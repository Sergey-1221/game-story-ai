from typing import Dict, List, Set, Optional, Tuple
from collections import deque
from loguru import logger

from src.core.models import Scene, Quest, StoryPath, Choice
from src.modules.story_planner import StoryGraph


class BranchManager:
    """Модуль управления ветвлениями и проверки целостности квеста"""
    
    def __init__(self):
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []
    
    def consolidate_quest(
        self,
        scenes: Dict[str, Scene],
        story_graph: StoryGraph,
        scenario_data: Dict[str, str],
        quest_title: str = None
    ) -> Quest:
        """Консолидация всех компонентов в единый квест"""
        logger.info("Начинаем консолидацию квеста")
        
        # Очищаем предыдущие ошибки
        self.validation_errors = []
        self.validation_warnings = []
        
        # Валидация структуры
        if not self._validate_structure(scenes, story_graph):
            raise ValueError(f"Ошибки валидации: {'; '.join(self.validation_errors)}")
        
        # Анализ путей
        all_paths = self._analyze_paths(scenes, story_graph)
        
        # Определение главного пути
        main_path = self._identify_main_path(all_paths)
        
        # Создание объекта квеста
        quest = Quest(
            title=quest_title or f"Квест: {scenario_data['goal'][:50]}",
            genre=scenario_data['genre'],
            hero=scenario_data['hero'],
            goal=scenario_data['goal'],
            scenes=list(scenes.values()),
            start_scene=story_graph.start_scene_id,
            paths=all_paths,
            metadata={
                'warnings': self.validation_warnings,
                'total_branches': self._count_branches(scenes),
                'max_depth': max(path.length for path in all_paths) if all_paths else 0
            }
        )
        
        # Финальная проверка
        self._final_validation(quest)
        
        logger.info(f"Квест успешно консолидирован: {len(quest.scenes)} сцен, "
                   f"{len(all_paths)} путей")
        
        return quest
    
    def _validate_structure(
        self, 
        scenes: Dict[str, Scene], 
        story_graph: StoryGraph
    ) -> bool:
        """Проверка структурной целостности квеста"""
        is_valid = True
        
        # Проверка наличия начальной сцены
        if not story_graph.start_scene_id:
            self.validation_errors.append("Отсутствует начальная сцена")
            is_valid = False
        elif story_graph.start_scene_id not in scenes:
            self.validation_errors.append(
                f"Начальная сцена {story_graph.start_scene_id} не найдена"
            )
            is_valid = False
        
        # Проверка всех переходов
        for scene_id, scene in scenes.items():
            for choice in scene.choices:
                if choice.next_scene and choice.next_scene not in scenes:
                    # Проверяем, не является ли это специальным концом
                    if choice.next_scene not in ['end', 'game_over', 'victory']:
                        self.validation_errors.append(
                            f"Битая ссылка: сцена {scene_id} ссылается на "
                            f"несуществующую сцену {choice.next_scene}"
                        )
                        is_valid = False
        
        # Проверка достижимости всех сцен
        reachable = self._find_reachable_scenes(scenes, story_graph.start_scene_id)
        unreachable = set(scenes.keys()) - reachable
        
        if unreachable:
            self.validation_warnings.append(
                f"Недостижимые сцены: {', '.join(unreachable)}"
            )
        
        # Проверка наличия развилок (предупреждение, но не критическая ошибка)
        has_branching = any(len(scene.choices) > 1 for scene in scenes.values())
        if not has_branching:
            logger.warning("Квест не содержит развилок - это линейная история")
        
        # Проверка глубины альтернативных путей (только если есть развилки)
        if has_branching and not self._validate_branching_depth(scenes, story_graph, min_depth=2):
            logger.warning("Альтернативные ветки могли быть длиннее")
        
        return is_valid
    
    def _find_reachable_scenes(
        self, 
        scenes: Dict[str, Scene], 
        start_scene_id: str
    ) -> Set[str]:
        """Поиск всех достижимых сцен от начальной"""
        reachable = set()
        queue = deque([start_scene_id])
        
        while queue:
            current_id = queue.popleft()
            if current_id in reachable or current_id not in scenes:
                continue
            
            reachable.add(current_id)
            current_scene = scenes[current_id]
            
            for choice in current_scene.choices:
                if choice.next_scene and choice.next_scene in scenes:
                    queue.append(choice.next_scene)
        
        return reachable
    
    def _validate_branching_depth(
        self,
        scenes: Dict[str, Scene],
        story_graph: StoryGraph,
        min_depth: int = 3
    ) -> bool:
        """Проверка глубины альтернативных веток"""
        all_paths = self._trace_all_paths(scenes, story_graph.start_scene_id)
        
        if len(all_paths) < 2:
            return False
        
        # Находим основной путь (самый длинный)
        main_path = max(all_paths, key=len)
        
        # Проверяем альтернативные пути
        for path in all_paths:
            if path != main_path and len(path) >= min_depth:
                return True
        
        return False
    
    def _trace_all_paths(
        self, 
        scenes: Dict[str, Scene], 
        start_id: str
    ) -> List[List[str]]:
        """Трассировка всех возможных путей через квест"""
        paths = []
        
        def dfs(current_id: str, path: List[str], visited: Set[str]):
            if current_id not in scenes:
                # Достигли конца
                paths.append(path[:])
                return
            
            if current_id in visited:
                # Обнаружен цикл
                self.validation_warnings.append(
                    f"Обнаружен цикл в пути: {' -> '.join(path[-3:])}"
                )
                paths.append(path[:])
                return
            
            visited.add(current_id)
            scene = scenes[current_id]
            
            if not scene.choices:
                # Конечная сцена
                paths.append(path[:])
            else:
                for choice in scene.choices:
                    if choice.next_scene:
                        path.append(choice.next_scene)
                        dfs(choice.next_scene, path, visited.copy())
                        path.pop()
        
        dfs(start_id, [start_id], set())
        return paths
    
    def _analyze_paths(
        self, 
        scenes: Dict[str, Scene], 
        story_graph: StoryGraph
    ) -> List[StoryPath]:
        """Анализ всех путей и создание объектов StoryPath"""
        all_paths = self._trace_all_paths(scenes, story_graph.start_scene_id)
        story_paths = []
        
        for i, path in enumerate(all_paths):
            # Определяем тип пути
            is_main = self._is_main_path(path, all_paths)
            
            # Определяем исход
            outcome = self._determine_outcome(path, scenes)
            
            story_path = StoryPath(
                path_id=f"path_{i+1}",
                scenes=path,
                length=len(path),
                is_main=is_main,
                outcome=outcome
            )
            
            story_paths.append(story_path)
        
        return story_paths
    
    def _is_main_path(self, path: List[str], all_paths: List[List[str]]) -> bool:
        """Определение, является ли путь основным"""
        # Основной путь - обычно самый длинный или наиболее прямой
        if not all_paths:
            return True
        
        max_length = max(len(p) for p in all_paths)
        return len(path) == max_length
    
    def _determine_outcome(
        self, 
        path: List[str], 
        scenes: Dict[str, Scene]
    ) -> str:
        """Определение исхода пути на основе последней сцены"""
        if not path:
            return "unknown"
        
        last_scene_id = path[-1]
        if last_scene_id not in scenes:
            # Специальные концовки
            if last_scene_id == "victory":
                return "победа"
            elif last_scene_id == "game_over":
                return "поражение"
            elif last_scene_id == "end":
                return "завершение"
            return "unknown"
        
        last_scene = scenes[last_scene_id]
        
        # Анализируем текст последней сцены
        text_lower = last_scene.text.lower()
        
        if any(word in text_lower for word in ['победа', 'успех', 'выполнил', 'достиг']):
            return "успех"
        elif any(word in text_lower for word in ['провал', 'поражение', 'погиб', 'схватили']):
            return "провал"
        else:
            return "нейтральный"
    
    def _identify_main_path(self, paths: List[StoryPath]) -> Optional[StoryPath]:
        """Идентификация главного пути"""
        main_paths = [p for p in paths if p.is_main]
        
        if main_paths:
            # Выбираем путь с наилучшим исходом
            for outcome in ['успех', 'победа', 'завершение', 'нейтральный']:
                for path in main_paths:
                    if path.outcome == outcome:
                        return path
            return main_paths[0]
        
        # Если нет явного главного пути, выбираем самый длинный
        return max(paths, key=lambda p: p.length) if paths else None
    
    def _count_branches(self, scenes: Dict[str, Scene]) -> int:
        """Подсчет количества развилок в квесте"""
        return sum(1 for scene in scenes.values() if len(scene.choices) > 1)
    
    def _final_validation(self, quest: Quest):
        """Финальная проверка собранного квеста"""
        # Проверка общего количества сцен
        scene_count = len(quest.scenes)
        if scene_count < 5:
            self.validation_errors.append(
                f"Недостаточно сцен: {scene_count} (минимум 5)"
            )
        elif scene_count > 10:
            self.validation_warnings.append(
                f"Слишком много сцен: {scene_count} (рекомендуется до 10)"
            )
        
        # Проверка наличия циклов
        if any("цикл" in warning for warning in self.validation_warnings):
            logger.warning("В квесте обнаружены циклические пути")
        
        # Логирование результатов валидации
        if self.validation_errors:
            logger.error(f"Ошибки валидации: {self.validation_errors}")
        if self.validation_warnings:
            logger.warning(f"Предупреждения: {self.validation_warnings}")
    
    def check_narrative_consistency(self, quest: Quest) -> List[str]:
        """Проверка нарративной согласованности (опциональная)"""
        issues = []
        
        # Проверка упоминания цели в сценах
        goal_mentioned = any(
            quest.goal.lower() in scene.text.lower() 
            for scene in quest.scenes
        )
        
        if not goal_mentioned:
            issues.append("Цель квеста не упоминается ни в одной сцене")
        
        # Проверка упоминания героя
        hero_words = quest.hero.lower().split()
        hero_mentioned = any(
            any(word in scene.text.lower() for word in hero_words)
            for scene in quest.scenes
        )
        
        if not hero_mentioned:
            issues.append("Герой не упоминается в тексте сцен")
        
        return issues