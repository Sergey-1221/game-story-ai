from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import uuid
from loguru import logger

from src.core.models import ScenarioInput, StoryPath
from src.modules.knowledge_base import KnowledgeBase


@dataclass
class PlannedScene:
    """Представление запланированной сцены"""
    scene_id: str
    stage_name: str
    description: str
    is_branching: bool = False
    choices: List[Tuple[str, str]] = None  # [(choice_text, next_scene_id)]
    depth_level: int = 0
    path_ids: Set[str] = None
    
    def __post_init__(self):
        if self.choices is None:
            self.choices = []
        if self.path_ids is None:
            self.path_ids = set()


class StoryGraph:
    """Граф сюжета для управления структурой квеста"""
    
    def __init__(self):
        self.scenes: Dict[str, PlannedScene] = {}
        self.edges: Dict[str, List[str]] = defaultdict(list)
        self.start_scene_id: Optional[str] = None
    
    def add_scene(self, scene: PlannedScene) -> str:
        """Добавление сцены в граф"""
        self.scenes[scene.scene_id] = scene
        if not self.start_scene_id:
            self.start_scene_id = scene.scene_id
        return scene.scene_id
    
    def add_edge(self, from_scene: str, to_scene: str, choice_text: str = "Продолжить"):
        """Добавление перехода между сценами"""
        self.edges[from_scene].append(to_scene)
        scene = self.scenes.get(from_scene)
        if scene:
            scene.choices.append((choice_text, to_scene))
    
    def get_all_paths(self) -> List[List[str]]:
        """Получение всех возможных путей через граф"""
        if not self.start_scene_id:
            return []
        
        paths = []
        
        def dfs(current: str, path: List[str]):
            if current not in self.edges or not self.edges[current]:
                paths.append(path[:])
                return
            
            for next_scene in self.edges[current]:
                if next_scene not in path:  # избегаем циклов
                    path.append(next_scene)
                    dfs(next_scene, path)
                    path.pop()
        
        dfs(self.start_scene_id, [self.start_scene_id])
        return paths
    
    def validate_branching_requirement(self, min_branch_depth: int = 3) -> bool:
        """Проверка требования о глубине ветвления"""
        all_paths = self.get_all_paths()
        
        if len(all_paths) < 2:
            return False
        
        main_path = max(all_paths, key=len)
        
        for path in all_paths:
            if path != main_path and len(path) >= min_branch_depth:
                return True
        
        return False


class StoryPlanner:
    """Планировщик структуры квеста"""
    
    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
        self.graph = StoryGraph()
    
    def plan_quest(self, scenario: ScenarioInput, 
                   min_scenes: int = 5, max_scenes: int = 10) -> StoryGraph:
        """Планирование структуры квеста"""
        logger.info(f"Планирование квеста: {scenario.genre} - {scenario.goal}")
        
        template = self.kb.find_quest_template(scenario.goal)
        
        if template:
            self._build_from_template(template, scenario)
        else:
            self._build_generic_structure(scenario)
        
        self._ensure_requirements(min_scenes, max_scenes)
        
        return self.graph
    
    def _build_from_template(self, template: Dict, scenario: ScenarioInput):
        """Построение структуры на основе шаблона"""
        stages = template.get('structure', [])
        prev_scene_id = None
        
        for i, stage in enumerate(stages):
            scene_id = f"scene_{i+1}"
            
            scene = PlannedScene(
                scene_id=scene_id,
                stage_name=stage['stage'],
                description=stage['description'],
                is_branching=stage.get('branching_point', False),
                depth_level=i
            )
            
            self.graph.add_scene(scene)
            
            if prev_scene_id:
                self.graph.add_edge(prev_scene_id, scene_id)
            
            if scene.is_branching and 'options' in stage:
                self._create_branches(scene_id, stage['options'], stages[i:])
            
            prev_scene_id = scene_id
    
    def _create_branches(self, branching_scene_id: str, 
                        options: List[str], remaining_stages: List[Dict]):
        """Создание развилок в сюжете"""
        branching_scene = self.graph.scenes[branching_scene_id]
        branching_scene.choices = []  # Очищаем стандартный выбор
        
        for j, option in enumerate(options[:2]):  # Максимум 2 основные ветки
            branch_id = f"{branching_scene_id}_branch_{j+1}"
            
            if j == 0:  # Основная ветка
                next_scene_id = self._continue_main_path(
                    branch_id, remaining_stages, branching_scene.depth_level
                )
            else:  # Альтернативная ветка
                next_scene_id = self._create_alternative_path(
                    branch_id, option, branching_scene.depth_level
                )
            
            self.graph.add_edge(branching_scene_id, next_scene_id, option)
    
    def _continue_main_path(self, start_id: str, stages: List[Dict], 
                           current_depth: int) -> str:
        """Продолжение основного пути"""
        if not stages or len(stages) < 2:
            return self._create_simple_scene(
                start_id, "Продолжение пути", current_depth + 1
            )
        
        first_scene_id = None
        prev_id = None
        
        for i, stage in enumerate(stages[1:3]):  # Берем следующие 2 стадии
            scene_id = f"{start_id}_cont_{i+1}"
            scene = PlannedScene(
                scene_id=scene_id,
                stage_name=stage.get('stage', 'continuation'),
                description=stage.get('description', 'Продолжение истории'),
                depth_level=current_depth + i + 1
            )
            
            self.graph.add_scene(scene)
            
            if i == 0:
                first_scene_id = scene_id
            
            if prev_id:
                self.graph.add_edge(prev_id, scene_id)
            
            prev_id = scene_id
        
        return first_scene_id
    
    def _create_alternative_path(self, start_id: str, option: str, 
                                current_depth: int) -> str:
        """Создание альтернативного пути (минимум 3 сцены)"""
        alt_stages = [
            ("последствие_выбора", f"Последствия выбора: {option}"),
            ("развитие_альтернативы", "Развитие альтернативного пути"),
            ("кульминация_альтернативы", "Кульминация альтернативной линии"),
            ("разрешение_альтернативы", "Разрешение альтернативного сюжета")
        ]
        
        first_scene_id = None
        prev_id = None
        
        for i, (stage_name, description) in enumerate(alt_stages):
            scene_id = f"{start_id}_alt_{i+1}"
            scene = PlannedScene(
                scene_id=scene_id,
                stage_name=stage_name,
                description=description,
                depth_level=current_depth + i + 1
            )
            
            self.graph.add_scene(scene)
            
            if i == 0:
                first_scene_id = scene_id
            
            if prev_id:
                self.graph.add_edge(prev_id, scene_id)
            
            prev_id = scene_id
        
        return first_scene_id
    
    def _build_generic_structure(self, scenario: ScenarioInput):
        """Построение универсальной структуры квеста"""
        stages = [
            ("завязка", "Введение в ситуацию и постановка задачи"),
            ("подготовка", "Подготовка к выполнению задачи"),
            ("первое_препятствие", "Первое серьезное препятствие"),
            ("развитие", "Развитие сюжета и усложнение"),
            ("кульминация", "Кульминационный момент"),
            ("развязка", "Разрешение конфликта"),
            ("финал", "Завершение истории")
        ]
        
        prev_scene_id = None
        
        for i, (stage_name, description) in enumerate(stages):
            scene_id = f"scene_{i+1}"
            
            is_branching = (i == 2)  # Развилка на третьей сцене
            
            scene = PlannedScene(
                scene_id=scene_id,
                stage_name=stage_name,
                description=description,
                is_branching=is_branching,
                depth_level=i
            )
            
            self.graph.add_scene(scene)
            
            if prev_scene_id:
                self.graph.add_edge(prev_scene_id, scene_id)
            
            if is_branching:
                self._create_branches(
                    scene_id,
                    ["Действовать осторожно", "Действовать решительно"],
                    stages[i+1:]
                )
                break  # Дальше пути расходятся
            
            prev_scene_id = scene_id
    
    def _create_simple_scene(self, scene_id: str, description: str, 
                           depth: int) -> str:
        """Создание простой сцены"""
        scene = PlannedScene(
            scene_id=scene_id,
            stage_name="development",
            description=description,
            depth_level=depth
        )
        self.graph.add_scene(scene)
        return scene_id
    
    def _ensure_requirements(self, min_scenes: int, max_scenes: int):
        """Обеспечение выполнения требований к структуре"""
        total_scenes = len(self.graph.scenes)
        
        if total_scenes < min_scenes:
            self._extend_paths(min_scenes - total_scenes)
        elif total_scenes > max_scenes:
            self._trim_paths(total_scenes - max_scenes)
        
        if not self.graph.validate_branching_requirement():
            self._ensure_branch_depth()
    
    def _extend_paths(self, scenes_to_add: int):
        """Расширение путей для достижения минимального количества сцен"""
        paths = self.graph.get_all_paths()
        shortest_path = min(paths, key=len) if paths else []
        
        if shortest_path and scenes_to_add > 0:
            last_scene = shortest_path[-1]
            for i in range(scenes_to_add):
                new_scene_id = f"{last_scene}_ext_{i+1}"
                new_scene = PlannedScene(
                    scene_id=new_scene_id,
                    stage_name="дополнение",
                    description="Дополнительное развитие сюжета",
                    depth_level=len(shortest_path) + i
                )
                self.graph.add_scene(new_scene)
                self.graph.add_edge(last_scene, new_scene_id)
                last_scene = new_scene_id
    
    def _trim_paths(self, scenes_to_remove: int):
        """Сокращение путей для соблюдения максимального количества сцен"""
        # Упрощенная реализация - в продакшене нужна более умная логика
        logger.warning(f"Необходимо удалить {scenes_to_remove} сцен")
    
    def _ensure_branch_depth(self):
        """Обеспечение требуемой глубины ветвления"""
        # Находим короткую альтернативную ветку и расширяем её
        paths = self.graph.get_all_paths()
        if len(paths) < 2:
            return
        
        main_path = max(paths, key=len)
        for path in paths:
            if path != main_path and len(path) < 3:
                # Расширяем эту ветку
                last_scene = path[-1]
                for i in range(3 - len(path) + 1):
                    new_scene_id = f"{last_scene}_deep_{i+1}"
                    new_scene = PlannedScene(
                        scene_id=new_scene_id,
                        stage_name="углубление",
                        description="Углубление альтернативной линии",
                        depth_level=len(path) + i
                    )
                    self.graph.add_scene(new_scene)
                    self.graph.add_edge(last_scene, new_scene_id)
                    last_scene = new_scene_id
                break