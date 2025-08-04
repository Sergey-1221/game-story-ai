"""
Модуль генерации уровней с использованием процедурных алгоритмов
и современных AI-подходов для создания игровых локаций
"""

import numpy as np
import random
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from loguru import logger
import noise
from scipy.spatial.distance import euclidean
from sklearn.cluster import KMeans
import cv2

from src.core.models import ScenarioInput


class TileType(Enum):
    """Типы тайлов для генерации уровней"""
    EMPTY = 0
    WALL = 1
    FLOOR = 2
    DOOR = 3
    WATER = 4
    OBSTACLE = 5
    SPAWN = 6
    GOAL = 7
    SECRET = 8
    TRAP = 9


@dataclass
class LevelConfig:
    """Конфигурация для генерации уровня"""
    width: int = 32
    height: int = 32
    algorithm: str = "wfc"  # wfc, cellular, perlin, maze, hybrid
    seed: Optional[int] = None
    
    # WFC параметры
    wfc_patterns_size: int = 3
    wfc_overlapping: bool = True
    
    # Cellular automata параметры
    wall_probability: float = 0.45
    iterations: int = 5
    
    # Perlin noise параметры
    noise_scale: float = 0.1
    octaves: int = 4
    persistence: float = 0.5
    lacunarity: float = 2.0
    
    # Гибридные параметры
    room_count: int = 5
    corridor_width: int = 2
    
    # Жанровые модификаторы
    genre_modifiers: Dict[str, Any] = None


@dataclass
class GeneratedLevel:
    """Результат генерации уровня"""
    tiles: np.ndarray
    width: int
    height: int
    spawn_points: List[Tuple[int, int]]
    goal_points: List[Tuple[int, int]]
    special_areas: Dict[str, List[Tuple[int, int]]]
    metadata: Dict[str, Any]


class WaveFunctionCollapseGenerator:
    """Генератор уровней на основе Wave Function Collapse"""
    
    def __init__(self, patterns: Optional[List[np.ndarray]] = None):
        self.patterns = patterns or self._create_default_patterns()
        self.pattern_weights = [1.0] * len(self.patterns)
    
    def _create_default_patterns(self) -> List[np.ndarray]:
        """Создание базовых паттернов для WFC"""
        patterns = []
        
        # Простые паттерны 3x3
        # Пустое пространство
        patterns.append(np.array([
            [TileType.FLOOR.value, TileType.FLOOR.value, TileType.FLOOR.value],
            [TileType.FLOOR.value, TileType.FLOOR.value, TileType.FLOOR.value],
            [TileType.FLOOR.value, TileType.FLOOR.value, TileType.FLOOR.value]
        ]))
        
        # Угол стены
        patterns.append(np.array([
            [TileType.WALL.value, TileType.WALL.value, TileType.FLOOR.value],
            [TileType.WALL.value, TileType.WALL.value, TileType.FLOOR.value],
            [TileType.FLOOR.value, TileType.FLOOR.value, TileType.FLOOR.value]
        ]))
        
        # Прямая стена
        patterns.append(np.array([
            [TileType.WALL.value, TileType.WALL.value, TileType.WALL.value],
            [TileType.FLOOR.value, TileType.FLOOR.value, TileType.FLOOR.value],
            [TileType.FLOOR.value, TileType.FLOOR.value, TileType.FLOOR.value]
        ]))
        
        # Дверь
        patterns.append(np.array([
            [TileType.WALL.value, TileType.DOOR.value, TileType.WALL.value],
            [TileType.FLOOR.value, TileType.FLOOR.value, TileType.FLOOR.value],
            [TileType.FLOOR.value, TileType.FLOOR.value, TileType.FLOOR.value]
        ]))
        
        return patterns
    
    def generate(self, config: LevelConfig) -> np.ndarray:
        """Генерация уровня методом WFC"""
        if config.seed:
            np.random.seed(config.seed)
            random.seed(config.seed)
        
        width, height = config.width, config.height
        
        # Инициализация волновых функций (возможные состояния каждой клетки)
        wave_functions = np.full((height, width), set(range(len(self.patterns))), dtype=object)
        
        # Простая реализация WFC
        level = np.zeros((height, width), dtype=int)
        
        for y in range(height):
            for x in range(width):
                # Выбираем случайный паттерн из доступных
                available_patterns = list(wave_functions[y, x]) if isinstance(wave_functions[y, x], set) else [0]
                if available_patterns:
                    pattern_idx = random.choice(available_patterns)
                    pattern = self.patterns[pattern_idx]
                    
                    # Применяем центральное значение паттерна
                    center_y, center_x = pattern.shape[0] // 2, pattern.shape[1] // 2
                    level[y, x] = pattern[center_y, center_x]
        
        return level


class CellularAutomataGenerator:
    """Генератор уровней на основе клеточных автоматов"""
    
    def generate(self, config: LevelConfig) -> np.ndarray:
        """Генерация уровня методом клеточных автоматов"""
        if config.seed:
            np.random.seed(config.seed)
            random.seed(config.seed)
        
        width, height = config.width, config.height
        
        # Начальная случайная генерация
        level = np.random.choice(
            [TileType.WALL.value, TileType.FLOOR.value],
            size=(height, width),
            p=[config.wall_probability, 1 - config.wall_probability]
        )
        
        # Итерации клеточного автомата
        for _ in range(config.iterations):
            new_level = level.copy()
            
            for y in range(1, height - 1):
                for x in range(1, width - 1):
                    # Подсчитываем соседей-стен
                    wall_count = np.sum(level[y-1:y+2, x-1:x+2] == TileType.WALL.value)
                    
                    # Правила клеточного автомата
                    if wall_count >= 5:
                        new_level[y, x] = TileType.WALL.value
                    elif wall_count <= 3:
                        new_level[y, x] = TileType.FLOOR.value
            
            level = new_level
        
        # Граничные стены
        level[0, :] = TileType.WALL.value
        level[-1, :] = TileType.WALL.value
        level[:, 0] = TileType.WALL.value
        level[:, -1] = TileType.WALL.value
        
        return level


class PerlinNoiseGenerator:
    """Генератор уровней на основе шума Перлина"""
    
    def generate(self, config: LevelConfig) -> np.ndarray:
        """Генерация уровня с помощью шума Перлина"""
        if config.seed:
            np.random.seed(config.seed)
            random.seed(config.seed)
        
        width, height = config.width, config.height
        level = np.zeros((height, width), dtype=int)
        
        for y in range(height):
            for x in range(width):
                # Генерация шума Перлина
                noise_value = noise.pnoise2(
                    x * config.noise_scale,
                    y * config.noise_scale,
                    octaves=config.octaves,
                    persistence=config.persistence,
                    lacunarity=config.lacunarity,
                    base=config.seed or 0
                )
                
                # Преобразование в тип тайла
                if noise_value < -0.3:
                    level[y, x] = TileType.WATER.value
                elif noise_value < 0:
                    level[y, x] = TileType.FLOOR.value
                elif noise_value < 0.3:
                    level[y, x] = TileType.OBSTACLE.value
                else:
                    level[y, x] = TileType.WALL.value
        
        return level


class MazeGenerator:
    """Генератор лабиринтов"""
    
    def generate(self, config: LevelConfig) -> np.ndarray:
        """Генерация лабиринта"""
        if config.seed:
            np.random.seed(config.seed)
            random.seed(config.seed)
        
        width, height = config.width, config.height
        
        # Убеждаемся, что размеры нечетные
        if width % 2 == 0:
            width -= 1
        if height % 2 == 0:
            height -= 1
        
        # Инициализация лабиринта стенами
        maze = np.full((height, width), TileType.WALL.value, dtype=int)
        
        # Рекурсивный backtracking
        def carve_passages(x, y):
            maze[y, x] = TileType.FLOOR.value
            
            # Случайный порядок направлений
            directions = [(0, 2), (2, 0), (0, -2), (-2, 0)]
            random.shuffle(directions)
            
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                
                if (0 < nx < width - 1 and 0 < ny < height - 1 and 
                    maze[ny, nx] == TileType.WALL.value):
                    
                    # Прорубаем стену между текущей и следующей клеткой
                    maze[y + dy // 2, x + dx // 2] = TileType.FLOOR.value
                    carve_passages(nx, ny)
        
        # Начинаем с случайной нечетной позиции
        start_x = random.randrange(1, width, 2)
        start_y = random.randrange(1, height, 2)
        carve_passages(start_x, start_y)
        
        return maze


class LevelGenerator:
    """Основной класс для генерации уровней"""
    
    def __init__(self):
        self.wfc_generator = WaveFunctionCollapseGenerator()
        self.cellular_generator = CellularAutomataGenerator()
        self.perlin_generator = PerlinNoiseGenerator()
        self.maze_generator = MazeGenerator()
        
        # Жанровые модификаторы
        self.genre_configs = {
            "киберпанк": {
                "wall_probability": 0.3,
                "obstacle_density": 0.15,
                "special_tiles": [TileType.TRAP, TileType.SECRET]
            },
            "фэнтези": {
                "wall_probability": 0.4,
                "water_probability": 0.1,
                "special_tiles": [TileType.SECRET]
            },
            "хоррор": {
                "wall_probability": 0.6,
                "corridor_width": 1,
                "special_tiles": [TileType.TRAP]
            },
            "постапокалипсис": {
                "obstacle_density": 0.25,
                "wall_probability": 0.35,
                "special_tiles": [TileType.OBSTACLE, TileType.TRAP]
            }
        }
    
    def generate_level(
        self, 
        scenario: ScenarioInput, 
        config: Optional[LevelConfig] = None
    ) -> GeneratedLevel:
        """Генерация уровня для сценария"""
        
        if not config:
            config = LevelConfig()
        
        # Применяем жанровые модификаторы
        self._apply_genre_modifiers(config, scenario.genre)
        
        logger.info(f"Генерируем уровень {config.width}x{config.height} алгоритмом {config.algorithm}")
        
        # Выбираем алгоритм генерации
        if config.algorithm == "wfc":
            base_level = self.wfc_generator.generate(config)
        elif config.algorithm == "cellular":
            base_level = self.cellular_generator.generate(config)
        elif config.algorithm == "perlin":
            base_level = self.perlin_generator.generate(config)
        elif config.algorithm == "maze":
            base_level = self.maze_generator.generate(config)
        elif config.algorithm == "hybrid":
            base_level = self._generate_hybrid_level(config)
        else:
            raise ValueError(f"Неизвестный алгоритм: {config.algorithm}")
        
        # Пост-обработка уровня
        processed_level = self._post_process_level(base_level, config, scenario)
        
        # Поиск ключевых точек
        spawn_points = self._find_spawn_points(processed_level)
        goal_points = self._find_goal_points(processed_level)
        special_areas = self._find_special_areas(processed_level)
        
        # Метаданные
        metadata = {
            "algorithm": config.algorithm,
            "genre": scenario.genre,
            "seed": config.seed,
            "generation_params": config.__dict__
        }
        
        return GeneratedLevel(
            tiles=processed_level,
            width=config.width,
            height=config.height,
            spawn_points=spawn_points,
            goal_points=goal_points,
            special_areas=special_areas,
            metadata=metadata
        )
    
    def _apply_genre_modifiers(self, config: LevelConfig, genre: str):
        """Применение жанровых модификаторов к конфигурации"""
        if genre.lower() in self.genre_configs:
            genre_config = self.genre_configs[genre.lower()]
            
            for key, value in genre_config.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    def _generate_hybrid_level(self, config: LevelConfig) -> np.ndarray:
        """Гибридная генерация, сочетающая несколько алгоритмов"""
        width, height = config.width, config.height
        
        # Начинаем с клеточного автомата для общей структуры
        base_level = self.cellular_generator.generate(config)
        
        # Добавляем комнаты с помощью простого алгоритма
        rooms = self._generate_rooms(width, height, config.room_count)
        
        for room in rooms:
            x, y, w, h = room
            base_level[y:y+h, x:x+w] = TileType.FLOOR.value
        
        # Соединяем комнаты коридорами
        for i in range(len(rooms) - 1):
            self._connect_rooms(base_level, rooms[i], rooms[i+1], config.corridor_width)
        
        # Добавляем шум Перлина для деталей
        noise_config = LevelConfig(
            width=width, height=height,
            noise_scale=0.2, octaves=2
        )
        noise_layer = self.perlin_generator.generate(noise_config)
        
        # Смешиваем слои
        mask = (noise_layer == TileType.OBSTACLE.value) & (base_level == TileType.FLOOR.value)
        base_level[mask] = TileType.OBSTACLE.value
        
        return base_level
    
    def _generate_rooms(self, width: int, height: int, room_count: int) -> List[Tuple[int, int, int, int]]:
        """Генерация прямоугольных комнат"""
        rooms = []
        
        for _ in range(room_count):
            # Случайные размеры комнаты
            room_width = random.randint(4, width // 4)
            room_height = random.randint(4, height // 4)
            
            # Случайная позиция
            x = random.randint(1, width - room_width - 1)
            y = random.randint(1, height - room_height - 1)
            
            rooms.append((x, y, room_width, room_height))
        
        return rooms
    
    def _connect_rooms(self, level: np.ndarray, room1: Tuple, room2: Tuple, corridor_width: int):
        """Соединение двух комнат коридором"""
        x1, y1, w1, h1 = room1
        x2, y2, w2, h2 = room2
        
        # Центры комнат
        center1 = (x1 + w1 // 2, y1 + h1 // 2)
        center2 = (x2 + w2 // 2, y2 + h2 // 2)
        
        # Простой L-образный коридор
        if random.choice([True, False]):
            # Сначала горизонтально, потом вертикально
            self._carve_horizontal_corridor(level, center1[0], center2[0], center1[1], corridor_width)
            self._carve_vertical_corridor(level, center2[0], center1[1], center2[1], corridor_width)
        else:
            # Сначала вертикально, потом горизонтально
            self._carve_vertical_corridor(level, center1[0], center1[1], center2[1], corridor_width)
            self._carve_horizontal_corridor(level, center1[0], center2[0], center2[1], corridor_width)
    
    def _carve_horizontal_corridor(self, level: np.ndarray, x1: int, x2: int, y: int, width: int):
        """Прорубка горизонтального коридора"""
        start_x, end_x = min(x1, x2), max(x1, x2)
        for x in range(start_x, end_x + 1):
            for dy in range(-width//2, width//2 + 1):
                if 0 <= y + dy < level.shape[0] and 0 <= x < level.shape[1]:
                    level[y + dy, x] = TileType.FLOOR.value
    
    def _carve_vertical_corridor(self, level: np.ndarray, x: int, y1: int, y2: int, width: int):
        """Прорубка вертикального коридора"""
        start_y, end_y = min(y1, y2), max(y1, y2)
        for y in range(start_y, end_y + 1):
            for dx in range(-width//2, width//2 + 1):
                if 0 <= y < level.shape[0] and 0 <= x + dx < level.shape[1]:
                    level[y, x + dx] = TileType.FLOOR.value
    
    def _post_process_level(self, level: np.ndarray, config: LevelConfig, scenario: ScenarioInput) -> np.ndarray:
        """Пост-обработка сгенерированного уровня"""
        processed_level = level.copy()
        
        # Размещение специальных элементов в зависимости от жанра
        if scenario.genre.lower() in self.genre_configs:
            special_tiles = self.genre_configs[scenario.genre.lower()].get("special_tiles", [])
            
            # Размещаем специальные тайлы
            floor_positions = np.where(processed_level == TileType.FLOOR.value)
            floor_coords = list(zip(floor_positions[0], floor_positions[1]))
            
            if floor_coords and special_tiles:
                special_count = min(len(floor_coords) // 10, 5)  # Не более 5 специальных тайлов
                special_positions = random.sample(floor_coords, special_count)
                
                for i, (y, x) in enumerate(special_positions):
                    tile_type = special_tiles[i % len(special_tiles)]
                    processed_level[y, x] = tile_type.value
        
        return processed_level
    
    def _find_spawn_points(self, level: np.ndarray) -> List[Tuple[int, int]]:
        """Поиск точек появления игрока"""
        floor_positions = np.where(level == TileType.FLOOR.value)
        if len(floor_positions[0]) == 0:
            return [(1, 1)]  # Fallback
        
        # Ищем позиции в углах или у краев
        spawn_candidates = []
        height, width = level.shape
        
        for y, x in zip(floor_positions[0], floor_positions[1]):
            # Предпочитаем позиции ближе к углам
            distance_to_corner = min(
                euclidean((y, x), (0, 0)),
                euclidean((y, x), (0, width-1)),
                euclidean((y, x), (height-1, 0)),
                euclidean((y, x), (height-1, width-1))
            )
            spawn_candidates.append((distance_to_corner, (x, y)))
        
        # Сортируем по расстоянию до угла и берем лучшие
        spawn_candidates.sort(key=lambda x: x[0])
        return [pos for _, pos in spawn_candidates[:3]]
    
    def _find_goal_points(self, level: np.ndarray) -> List[Tuple[int, int]]:
        """Поиск целевых точек"""
        # Ищем существующие целевые тайлы
        goal_positions = np.where(level == TileType.GOAL.value)
        if len(goal_positions[0]) > 0:
            return [(x, y) for y, x in zip(goal_positions[0], goal_positions[1])]
        
        # Если нет специальных целевых тайлов, выбираем удаленные позиции пола
        floor_positions = np.where(level == TileType.FLOOR.value)
        if len(floor_positions[0]) == 0:
            return [(level.shape[1]-2, level.shape[0]-2)]  # Fallback
        
        # Ищем позиции, наиболее удаленные от углов
        goal_candidates = []
        height, width = level.shape
        
        for y, x in zip(floor_positions[0], floor_positions[1]):
            min_distance_to_corner = min(
                euclidean((y, x), (0, 0)),
                euclidean((y, x), (0, width-1)),
                euclidean((y, x), (height-1, 0)),
                euclidean((y, x), (height-1, width-1))
            )
            goal_candidates.append((min_distance_to_corner, (x, y)))
        
        # Сортируем по убыванию расстояния до ближайшего угла
        goal_candidates.sort(key=lambda x: x[0], reverse=True)
        return [pos for _, pos in goal_candidates[:2]]
    
    def _find_special_areas(self, level: np.ndarray) -> Dict[str, List[Tuple[int, int]]]:
        """Поиск специальных областей"""
        special_areas = {}
        
        # Ищем различные типы специальных тайлов
        for tile_type in [TileType.SECRET, TileType.TRAP, TileType.WATER]:
            positions = np.where(level == tile_type.value)
            if len(positions[0]) > 0:
                coords = [(x, y) for y, x in zip(positions[0], positions[1])]
                special_areas[tile_type.name.lower()] = coords
        
        return special_areas
    
    def export_to_image(self, level: GeneratedLevel, output_path: str):
        """Экспорт уровня в изображение для визуализации"""
        # Цветовая карта для тайлов
        color_map = {
            TileType.EMPTY.value: (0, 0, 0),        # Черный
            TileType.WALL.value: (128, 128, 128),   # Серый
            TileType.FLOOR.value: (255, 255, 255),  # Белый
            TileType.DOOR.value: (139, 69, 19),     # Коричневый
            TileType.WATER.value: (0, 0, 255),      # Синий
            TileType.OBSTACLE.value: (165, 42, 42), # Красно-коричневый
            TileType.SPAWN.value: (0, 255, 0),      # Зеленый
            TileType.GOAL.value: (255, 0, 0),       # Красный
            TileType.SECRET.value: (255, 0, 255),   # Фиолетовый
            TileType.TRAP.value: (255, 165, 0)      # Оранжевый
        }
        
        height, width = level.tiles.shape
        image = np.zeros((height, width, 3), dtype=np.uint8)
        
        for y in range(height):
            for x in range(width):
                tile_value = level.tiles[y, x]
                if tile_value in color_map:
                    image[y, x] = color_map[tile_value]
        
        # Увеличиваем изображение для лучшей видимости
        scale_factor = 10
        large_image = cv2.resize(image, (width * scale_factor, height * scale_factor), 
                               interpolation=cv2.INTER_NEAREST)
        
        cv2.imwrite(output_path, cv2.cvtColor(large_image, cv2.COLOR_RGB2BGR))
        logger.info(f"Уровень экспортирован в изображение: {output_path}")