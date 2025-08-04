"""
Модуль интеллектуального размещения объектов в игровых уровнях
с использованием машинного обучения и эвристических алгоритмов
"""

import numpy as np
import random
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from loguru import logger
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import euclidean_distances
from scipy.spatial import distance
from scipy.optimize import minimize
import cv2

from src.core.models import ScenarioInput
from src.modules.level_generator import GeneratedLevel, TileType


class ObjectType(Enum):
    """Типы объектов для размещения"""
    ENEMY = "enemy"
    ITEM = "item"
    TREASURE = "treasure"
    TRAP = "trap"
    DECORATION = "decoration"
    INTERACTIVE = "interactive"
    QUEST_OBJECT = "quest_object"
    CHECKPOINT = "checkpoint"
    LIGHT_SOURCE = "light_source"
    COVER = "cover"


@dataclass
class GameObject:
    """Игровой объект"""
    object_id: str
    object_type: ObjectType
    position: Tuple[int, int]
    properties: Dict[str, Any]
    influence_radius: float = 3.0
    placement_rules: Dict[str, Any] = None


@dataclass
class PlacementRule:
    """Правило размещения объектов"""
    object_type: ObjectType
    min_distance_from_walls: float = 1.0
    min_distance_from_same_type: float = 3.0
    max_distance_from_same_type: float = 10.0
    preferred_tiles: List[TileType] = None
    forbidden_tiles: List[TileType] = None
    density_per_area: float = 0.1  # объектов на квадратную единицу
    clustering_preference: float = 0.5  # 0 = избегать кластеров, 1 = предпочитать кластеры
    strategic_importance: float = 1.0  # важность для игрового процесса


@dataclass
class PlacementContext:
    """Контекст для размещения объектов"""
    level: GeneratedLevel
    scenario: ScenarioInput
    player_path: Optional[List[Tuple[int, int]]] = None
    difficulty_zones: Optional[np.ndarray] = None
    visibility_map: Optional[np.ndarray] = None


class PathAnalyzer:
    """Анализатор путей игрока для оптимального размещения объектов"""
    
    def __init__(self):
        self.path_cache = {}
    
    def find_player_paths(self, level: GeneratedLevel) -> List[List[Tuple[int, int]]]:
        """Поиск возможных путей игрока от spawn до goal точек"""
        paths = []
        
        for spawn in level.spawn_points:
            for goal in level.goal_points:
                path = self._find_path_astar(level, spawn, goal)
                if path:
                    paths.append(path)
        
        return paths
    
    def _find_path_astar(self, level: GeneratedLevel, start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """A* поиск пути"""
        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])
        
        def is_walkable(pos):
            x, y = pos
            if x < 0 or x >= level.width or y < 0 or y >= level.height:
                return False
            tile = level.tiles[y, x]
            return tile in [TileType.FLOOR.value, TileType.DOOR.value, TileType.GOAL.value, TileType.SPAWN.value]
        
        open_set = [start]
        came_from = {}
        g_score = {start: 0}
        f_score = {start: heuristic(start, goal)}
        
        while open_set:
            current = min(open_set, key=lambda x: f_score.get(x, float('inf')))
            
            if current == goal:
                # Восстанавливаем путь
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]
            
            open_set.remove(current)
            
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]:
                neighbor = (current[0] + dx, current[1] + dy)
                
                if not is_walkable(neighbor):
                    continue
                
                tentative_g_score = g_score[current] + (1.414 if abs(dx) + abs(dy) == 2 else 1)
                
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = g_score[neighbor] + heuristic(neighbor, goal)
                    
                    if neighbor not in open_set:
                        open_set.append(neighbor)
        
        return None


class DifficultyZoneAnalyzer:
    """Анализатор зон сложности для адаптивного размещения объектов"""
    
    def analyze_difficulty_zones(self, level: GeneratedLevel, paths: List[List[Tuple[int, int]]]) -> np.ndarray:
        """Создание карты зон сложности"""
        difficulty_map = np.zeros((level.height, level.width), dtype=float)
        
        # Базовая сложность на основе расстояния от spawn точек
        for spawn in level.spawn_points:
            for y in range(level.height):
                for x in range(level.width):
                    if level.tiles[y, x] in [TileType.FLOOR.value, TileType.DOOR.value]:
                        dist = distance.euclidean((x, y), spawn)
                        difficulty_map[y, x] += min(dist / 10.0, 1.0)  # Нормализуем
        
        # Увеличиваем сложность в узких проходах
        difficulty_map += self._analyze_choke_points(level)
        
        # Увеличиваем сложность рядом с целевыми точками
        for goal in level.goal_points:
            for y in range(max(0, goal[1] - 5), min(level.height, goal[1] + 6)):
                for x in range(max(0, goal[0] - 5), min(level.width, goal[0] + 6)):
                    dist = distance.euclidean((x, y), goal)
                    if dist <= 5:
                        difficulty_map[y, x] += (5 - dist) / 5.0
        
        # Нормализация
        max_difficulty = np.max(difficulty_map)
        if max_difficulty > 0:
            difficulty_map /= max_difficulty
        
        return difficulty_map
    
    def _analyze_choke_points(self, level: GeneratedLevel) -> np.ndarray:
        """Анализ узких проходов (choke points)"""
        choke_map = np.zeros((level.height, level.width), dtype=float)
        
        for y in range(1, level.height - 1):
            for x in range(1, level.width - 1):
                if level.tiles[y, x] == TileType.FLOOR.value:
                    # Считаем количество свободных соседей
                    neighbors = [
                        level.tiles[y-1, x-1], level.tiles[y-1, x], level.tiles[y-1, x+1],
                        level.tiles[y, x-1],                           level.tiles[y, x+1],
                        level.tiles[y+1, x-1], level.tiles[y+1, x], level.tiles[y+1, x+1]
                    ]
                    
                    free_neighbors = sum(1 for tile in neighbors if tile == TileType.FLOOR.value)
                    
                    # Чем меньше свободных соседей, тем выше значение choke point
                    if free_neighbors <= 3:
                        choke_map[y, x] = (4 - free_neighbors) / 4.0
        
        return choke_map


class VisibilityAnalyzer:
    """Анализатор видимости для размещения объектов с учетом зоны видимости игрока"""
    
    def compute_visibility_map(self, level: GeneratedLevel, paths: List[List[Tuple[int, int]]]) -> np.ndarray:
        """Вычисление карты видимости"""
        visibility_map = np.zeros((level.height, level.width), dtype=float)
        
        # Для каждой точки на основных путях вычисляем видимость
        for path in paths[:3]:  # Берем только первые 3 пути для производительности
            for pos in path[::2]:  # Каждая вторая точка
                visible_points = self._calculate_fov(level, pos, radius=7)
                for vx, vy in visible_points:
                    visibility_map[vy, vx] += 1.0
        
        # Нормализация
        max_visibility = np.max(visibility_map)
        if max_visibility > 0:
            visibility_map /= max_visibility
        
        return visibility_map
    
    def _calculate_fov(self, level: GeneratedLevel, center: Tuple[int, int], radius: int) -> List[Tuple[int, int]]:
        """Вычисление поля зрения методом ray casting"""
        visible_points = []
        cx, cy = center
        
        # Проверяем лучи в разных направлениях
        for angle in range(0, 360, 5):  # Каждые 5 градусов
            rad = np.radians(angle)
            dx = np.cos(rad)
            dy = np.sin(rad)
            
            for step in range(1, radius + 1):
                x = int(cx + dx * step)
                y = int(cy + dy * step)
                
                if x < 0 or x >= level.width or y < 0 or y >= level.height:
                    break
                
                if level.tiles[y, x] == TileType.WALL.value:
                    break
                
                visible_points.append((x, y))
        
        return visible_points


class MLPlacementOptimizer:
    """Оптимизатор размещения объектов с использованием ML"""
    
    def __init__(self):
        self.feature_weights = {
            'distance_to_path': 0.3,
            'difficulty_zone': 0.25,
            'visibility': 0.2,
            'clustering': 0.15,
            'strategic_position': 0.1
        }
    
    def optimize_placement(
        self, 
        context: PlacementContext, 
        objects_to_place: List[ObjectType],
        placement_rules: Dict[ObjectType, PlacementRule]
    ) -> List[GameObject]:
        """Оптимизация размещения объектов"""
        
        logger.info(f"Оптимизируем размещение {len(objects_to_place)} объектов")
        
        # Анализируем контекст
        path_analyzer = PathAnalyzer()
        difficulty_analyzer = DifficultyZoneAnalyzer()
        visibility_analyzer = VisibilityAnalyzer()
        
        paths = path_analyzer.find_player_paths(context.level)
        difficulty_zones = difficulty_analyzer.analyze_difficulty_zones(context.level, paths)
        visibility_map = visibility_analyzer.compute_visibility_map(context.level, paths)
        
        # Обновляем контекст
        context.player_path = paths[0] if paths else None
        context.difficulty_zones = difficulty_zones
        context.visibility_map = visibility_map
        
        placed_objects = []
        
        # Размещаем объекты по типам
        for object_type in set(objects_to_place):
            count = objects_to_place.count(object_type)
            rule = placement_rules.get(object_type, PlacementRule(object_type))
            
            positions = self._find_optimal_positions(context, object_type, rule, count, placed_objects)
            
            for i, pos in enumerate(positions):
                obj = GameObject(
                    object_id=f"{object_type.value}_{i+1}",
                    object_type=object_type,
                    position=pos,
                    properties=self._generate_object_properties(object_type, context.scenario),
                    placement_rules=rule.__dict__
                )
                placed_objects.append(obj)
        
        logger.info(f"Размещено {len(placed_objects)} объектов")
        return placed_objects
    
    def _find_optimal_positions(
        self, 
        context: PlacementContext, 
        object_type: ObjectType, 
        rule: PlacementRule,
        count: int,
        existing_objects: List[GameObject]
    ) -> List[Tuple[int, int]]:
        """Поиск оптимальных позиций для объектов данного типа"""
        
        # Получаем все возможные позиции
        candidate_positions = self._get_candidate_positions(context.level, rule)
        
        if not candidate_positions:
            return []
        
        # Вычисляем оценки для каждой позиции
        position_scores = []
        
        for pos in candidate_positions:
            score = self._evaluate_position(pos, context, object_type, rule, existing_objects)
            position_scores.append((score, pos))
        
        # Сортируем по оценке
        position_scores.sort(key=lambda x: x[0], reverse=True)
        
        # Выбираем лучшие позиции с учетом правил расстояния
        selected_positions = []
        
        for score, pos in position_scores:
            if len(selected_positions) >= count:
                break
            
            # Проверяем минимальное расстояние от уже выбранных позиций того же типа
            too_close = False
            for selected_pos in selected_positions:
                dist = distance.euclidean(pos, selected_pos)
                if dist < rule.min_distance_from_same_type:
                    too_close = True
                    break
            
            if not too_close:
                selected_positions.append(pos)
        
        return selected_positions
    
    def _get_candidate_positions(self, level: GeneratedLevel, rule: PlacementRule) -> List[Tuple[int, int]]:
        """Получение кандидатов позиций с учетом правил"""
        candidates = []
        
        preferred_tiles = rule.preferred_tiles or [TileType.FLOOR]
        forbidden_tiles = rule.forbidden_tiles or [TileType.WALL, TileType.WATER]
        
        for y in range(level.height):
            for x in range(level.width):
                tile_type = TileType(level.tiles[y, x])
                
                # Проверяем тип тайла
                if tile_type in forbidden_tiles:
                    continue
                
                if preferred_tiles and tile_type not in preferred_tiles:
                    continue
                
                # Проверяем расстояние от стен
                if self._distance_to_wall(level, (x, y)) < rule.min_distance_from_walls:
                    continue
                
                candidates.append((x, y))
        
        return candidates
    
    def _distance_to_wall(self, level: GeneratedLevel, pos: Tuple[int, int]) -> float:
        """Вычисление расстояния до ближайшей стены"""
        x, y = pos
        min_dist = float('inf')
        
        for dy in range(-5, 6):
            for dx in range(-5, 6):
                nx, ny = x + dx, y + dy
                
                if (0 <= nx < level.width and 0 <= ny < level.height and 
                    level.tiles[ny, nx] == TileType.WALL.value):
                    
                    dist = distance.euclidean((x, y), (nx, ny))
                    min_dist = min(min_dist, dist)
        
        return min_dist if min_dist != float('inf') else 5.0
    
    def _evaluate_position(
        self, 
        pos: Tuple[int, int], 
        context: PlacementContext, 
        object_type: ObjectType,
        rule: PlacementRule,
        existing_objects: List[GameObject]
    ) -> float:
        """Оценка качества позиции для размещения объекта"""
        x, y = pos
        score = 0.0
        
        # Расстояние до пути игрока
        if context.player_path:
            min_path_dist = min(distance.euclidean(pos, path_pos) for path_pos in context.player_path)
            path_score = self._sigmoid_score(min_path_dist, optimal=3.0, width=2.0)
            score += self.feature_weights['distance_to_path'] * path_score
        
        # Зона сложности
        if context.difficulty_zones is not None:
            difficulty_score = context.difficulty_zones[y, x]
            # Для врагов предпочитаем высокую сложность, для предметов - низкую
            if object_type == ObjectType.ENEMY:
                score += self.feature_weights['difficulty_zone'] * difficulty_score
            else:
                score += self.feature_weights['difficulty_zone'] * (1.0 - difficulty_score)
        
        # Видимость
        if context.visibility_map is not None:
            visibility_score = context.visibility_map[y, x]
            # Для ловушек предпочитаем низкую видимость
            if object_type == ObjectType.TRAP:
                score += self.feature_weights['visibility'] * (1.0 - visibility_score)
            else:
                score += self.feature_weights['visibility'] * visibility_score
        
        # Кластеризация
        clustering_score = self._evaluate_clustering(pos, existing_objects, rule.clustering_preference)
        score += self.feature_weights['clustering'] * clustering_score
        
        # Стратегическая позиция
        strategic_score = self._evaluate_strategic_position(pos, context, object_type)
        score += self.feature_weights['strategic_position'] * strategic_score * rule.strategic_importance
        
        return score
    
    def _sigmoid_score(self, value: float, optimal: float, width: float) -> float:
        """Сигмоидальная функция оценки с оптимальным значением"""
        return 1.0 / (1.0 + np.exp(abs(value - optimal) / width))
    
    def _evaluate_clustering(self, pos: Tuple[int, int], existing_objects: List[GameObject], preference: float) -> float:
        """Оценка кластеризации объектов"""
        if not existing_objects:
            return 0.5
        
        distances = [distance.euclidean(pos, obj.position) for obj in existing_objects]
        avg_distance = np.mean(distances)
        
        # preference = 0: избегать кластеров (высокие расстояния лучше)
        # preference = 1: предпочитать кластеры (низкие расстояния лучше)
        normalized_dist = min(avg_distance / 10.0, 1.0)
        
        return preference * (1.0 - normalized_dist) + (1.0 - preference) * normalized_dist
    
    def _evaluate_strategic_position(self, pos: Tuple[int, int], context: PlacementContext, object_type: ObjectType) -> float:
        """Оценка стратегической важности позиции"""
        x, y = pos
        score = 0.0
        
        # Близость к целевым точкам
        if context.level.goal_points:
            min_goal_dist = min(distance.euclidean(pos, goal) for goal in context.level.goal_points)
            if object_type in [ObjectType.ENEMY, ObjectType.TRAP]:
                # Враги и ловушки лучше размещать ближе к цели
                score += (10.0 - min(min_goal_dist, 10.0)) / 10.0
        
        # Близость к точкам появления
        if context.level.spawn_points:
            min_spawn_dist = min(distance.euclidean(pos, spawn) for spawn in context.level.spawn_points)
            if object_type in [ObjectType.ITEM, ObjectType.CHECKPOINT]:
                # Предметы и чекпоинты лучше размещать не слишком близко к спавну
                score += min(min_spawn_dist / 5.0, 1.0)
        
        return score
    
    def _generate_object_properties(self, object_type: ObjectType, scenario: ScenarioInput) -> Dict[str, Any]:
        """Генерация свойств объекта в зависимости от типа и сценария"""
        properties = {"genre": scenario.genre}
        
        if object_type == ObjectType.ENEMY:
            properties.update({
                "health": random.randint(50, 150),
                "damage": random.randint(10, 30),
                "ai_type": random.choice(["patrol", "guard", "aggressive"]),
                "detection_radius": random.uniform(3.0, 7.0)
            })
        
        elif object_type == ObjectType.ITEM:
            properties.update({
                "item_type": random.choice(["weapon", "armor", "consumable", "key"]),
                "value": random.randint(10, 100),
                "stackable": random.choice([True, False])
            })
        
        elif object_type == ObjectType.TRAP:
            properties.update({
                "trap_type": random.choice(["spike", "poison", "explosive", "alarm"]),
                "damage": random.randint(20, 50),
                "detection_difficulty": random.uniform(0.3, 0.8)
            })
        
        elif object_type == ObjectType.TREASURE:
            properties.update({
                "treasure_type": random.choice(["gold", "gems", "artifact"]),
                "value": random.randint(100, 500),
                "hidden": random.choice([True, False])
            })
        
        return properties


class ObjectPlacementEngine:
    """Основной движок размещения объектов"""
    
    def __init__(self):
        self.optimizer = MLPlacementOptimizer()
        self.default_rules = self._create_default_rules()
    
    def _create_default_rules(self) -> Dict[ObjectType, PlacementRule]:
        """Создание правил размещения по умолчанию"""
        rules = {}
        
        rules[ObjectType.ENEMY] = PlacementRule(
            object_type=ObjectType.ENEMY,
            min_distance_from_walls=1.5,
            min_distance_from_same_type=4.0,
            density_per_area=0.05,
            clustering_preference=0.3,
            strategic_importance=1.0
        )
        
        rules[ObjectType.ITEM] = PlacementRule(
            object_type=ObjectType.ITEM,
            min_distance_from_walls=1.0,
            min_distance_from_same_type=3.0,
            density_per_area=0.08,
            clustering_preference=0.1,
            strategic_importance=0.7
        )
        
        rules[ObjectType.TRAP] = PlacementRule(
            object_type=ObjectType.TRAP,
            min_distance_from_walls=0.5,
            min_distance_from_same_type=5.0,
            density_per_area=0.03,
            clustering_preference=0.0,
            strategic_importance=0.9
        )
        
        rules[ObjectType.TREASURE] = PlacementRule(
            object_type=ObjectType.TREASURE,
            min_distance_from_walls=1.0,
            min_distance_from_same_type=8.0,
            density_per_area=0.02,
            clustering_preference=0.0,
            strategic_importance=1.0
        )
        
        return rules
    
    def place_objects(
        self, 
        level: GeneratedLevel, 
        scenario: ScenarioInput,
        object_config: Optional[Dict[ObjectType, int]] = None
    ) -> List[GameObject]:
        """Размещение объектов на уровне"""
        
        # Определяем количество объектов каждого типа
        if not object_config:
            object_config = self._calculate_object_counts(level, scenario)
        
        # Создаем список объектов для размещения
        objects_to_place = []
        for obj_type, count in object_config.items():
            objects_to_place.extend([obj_type] * count)
        
        # Создаем контекст размещения
        context = PlacementContext(level=level, scenario=scenario)
        
        # Оптимизируем размещение
        placed_objects = self.optimizer.optimize_placement(
            context, objects_to_place, self.default_rules
        )
        
        return placed_objects
    
    def _calculate_object_counts(self, level: GeneratedLevel, scenario: ScenarioInput) -> Dict[ObjectType, int]:
        """Вычисление количества объектов каждого типа"""
        # Площадь проходимых тайлов
        walkable_area = np.sum(np.isin(level.tiles, [
            TileType.FLOOR.value, TileType.DOOR.value, TileType.SPAWN.value, TileType.GOAL.value
        ]))
        
        base_counts = {
            ObjectType.ENEMY: max(1, int(walkable_area * 0.05)),
            ObjectType.ITEM: max(2, int(walkable_area * 0.08)),
            ObjectType.TRAP: max(1, int(walkable_area * 0.03)),
            ObjectType.TREASURE: max(1, int(walkable_area * 0.02)),
            ObjectType.DECORATION: max(3, int(walkable_area * 0.1))
        }
        
        # Модификаторы в зависимости от жанра
        genre_modifiers = {
            "киберпанк": {
                ObjectType.ENEMY: 1.2,
                ObjectType.TRAP: 1.5,
                ObjectType.ITEM: 1.1
            },
            "хоррор": {
                ObjectType.ENEMY: 0.8,
                ObjectType.TRAP: 2.0,
                ObjectType.ITEM: 0.7
            },
            "фэнтези": {
                ObjectType.TREASURE: 1.5,
                ObjectType.ENEMY: 1.0,
                ObjectType.ITEM: 1.2
            }
        }
        
        if scenario.genre.lower() in genre_modifiers:
            modifiers = genre_modifiers[scenario.genre.lower()]
            for obj_type, modifier in modifiers.items():
                if obj_type in base_counts:
                    base_counts[obj_type] = max(1, int(base_counts[obj_type] * modifier))
        
        return base_counts
    
    def export_placement_data(self, objects: List[GameObject], output_path: str):
        """Экспорт данных о размещении объектов"""
        placement_data = {
            "objects": [
                {
                    "id": obj.object_id,
                    "type": obj.object_type.value,
                    "position": obj.position,
                    "properties": obj.properties,
                    "influence_radius": obj.influence_radius
                }
                for obj in objects
            ],
            "metadata": {
                "total_objects": len(objects),
                "object_types": list(set(obj.object_type.value for obj in objects))
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(placement_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Данные о размещении объектов экспортированы в: {output_path}")
    
    def visualize_placement(self, level: GeneratedLevel, objects: List[GameObject], output_path: str):
        """Визуализация размещения объектов на уровне"""
        # Базовое изображение уровня
        height, width = level.tiles.shape
        image = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Цвета для тайлов
        tile_colors = {
            TileType.WALL.value: (64, 64, 64),
            TileType.FLOOR.value: (200, 200, 200),
            TileType.DOOR.value: (139, 69, 19),
            TileType.WATER.value: (0, 100, 200)
        }
        
        for y in range(height):
            for x in range(width):
                tile_value = level.tiles[y, x]
                if tile_value in tile_colors:
                    image[y, x] = tile_colors[tile_value]
        
        # Цвета для объектов
        object_colors = {
            ObjectType.ENEMY: (255, 0, 0),      # Красный
            ObjectType.ITEM: (0, 255, 0),       # Зеленый
            ObjectType.TRAP: (255, 165, 0),     # Оранжевый
            ObjectType.TREASURE: (255, 215, 0), # Золотой
            ObjectType.DECORATION: (128, 0, 128) # Фиолетовый
        }
        
        # Размещаем объекты на изображении
        for obj in objects:
            x, y = obj.position
            if 0 <= x < width and 0 <= y < height:
                color = object_colors.get(obj.object_type, (255, 255, 255))
                image[y, x] = color
        
        # Увеличиваем изображение для лучшей видимости
        scale_factor = 8
        large_image = cv2.resize(image, (width * scale_factor, height * scale_factor), 
                               interpolation=cv2.INTER_NEAREST)
        
        cv2.imwrite(output_path, cv2.cvtColor(large_image, cv2.COLOR_RGB2BGR))
        logger.info(f"Визуализация размещения объектов сохранена в: {output_path}")