"""
Интегрированный генератор квестов с поддержкой Story2Game и SceneCraft
Объединяет структурированную генерацию сюжета и визуализацию сцен
"""

import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
from loguru import logger
import time

from src.core.models import (
    Quest, Scene, ScenarioInput, GenerationConfig,
    Choice
)
from src.quest_generator import QuestGenerator
from src.modules.story2game_engine import Story2GameEngine, WorldState
from src.modules.scenecraft_visualizer import SceneCraftVisualizer
from src.modules.knowledge_base import KnowledgeBase


class IntegratedQuestGenerator:
    """Расширенный генератор с поддержкой логики и визуализации"""
    
    def __init__(self, config: Optional[GenerationConfig] = None):
        # Базовый генератор
        self.base_generator = QuestGenerator(config)
        
        # Убедимся, что базовый генератор инициализирован
        self.base_generator._ensure_initialized()
        
        # Расширения
        self.story2game = Story2GameEngine(self.base_generator.knowledge_base)
        
        # SceneCraft может требовать тяжелые зависимости, делаем опциональным
        try:
            # Инициализируем SceneCraft без множественных видов для экономии API запросов
            self.scenecraft = SceneCraftVisualizer(enable_multiple_views=False)
            self.visualization_available = True
        except Exception as e:
            logger.warning(f"SceneCraft недоступен: {e}")
            self.scenecraft = None
            self.visualization_available = False
        
        # Конфигурация
        self.config = config or GenerationConfig()
        self.enable_logic_generation = True
        self.enable_visualization = self.visualization_available
        self.enable_dynamic_actions = False
    
    async def generate_enhanced_quest(
        self, 
        scenario: ScenarioInput,
        with_logic: bool = True,
        with_visuals: bool = False,
        export_code: bool = False
    ) -> Dict[str, Any]:
        """Генерация расширенного квеста с логикой и визуализацией"""
        start_time = time.time()
        logger.info("Начинаем расширенную генерацию квеста")
        
        # 1. Базовая генерация квеста
        quest = await self.base_generator.generate_async(scenario)
        
        result = {
            "quest": quest,
            "enhancements": {}
        }
        
        # 2. Добавляем структурированную логику (Story2Game)
        if with_logic:
            logic_data = await self._enhance_with_logic(quest, scenario)
            result["enhancements"]["logic"] = logic_data
            
            if export_code:
                code = self.story2game.export_to_code(
                    logic_data["story_actions"], 
                    language="python"
                )
                result["enhancements"]["generated_code"] = code
        
        # 3. Добавляем визуализацию (SceneCraft)
        if with_visuals:
            visualization = await self._enhance_with_visuals(quest)
            result["enhancements"]["visualization"] = visualization
        
        # 4. Интеграция логики и визуалов
        if with_logic and with_visuals:
            integrated = self._integrate_logic_and_visuals(
                logic_data, 
                visualization,
                quest
            )
            result["enhancements"]["integrated"] = integrated
        
        generation_time = time.time() - start_time
        result["metadata"] = {
            "generation_time": generation_time,
            "features_enabled": {
                "logic": with_logic,
                "visuals": with_visuals,
                "code_export": export_code
            }
        }
        
        logger.info(f"Расширенная генерация завершена за {generation_time:.2f} сек")
        return result
    
    async def _enhance_with_logic(self, quest: Quest, 
                                scenario: ScenarioInput) -> Dict[str, Any]:
        """Добавление логики Story2Game к квесту"""
        logger.info("Добавляем структурированную логику к квесту")
        
        logic_data = {
            "world_state": self._initialize_world_state(quest, scenario),
            "story_actions": [],
            "preconditions": {},
            "effects": {},
            "action_graph": {}
        }
        
        # Анализируем каждую сцену
        for scene in quest.scenes:
            scene_logic = self.story2game.analyze_scene_for_logic(scene, scenario)
            
            # Создаем действия для каждого выбора
            for i, (choice, action_data) in enumerate(
                zip(scene.choices, scene_logic["actions"])
            ):
                action_id = f"{scene.scene_id}_choice_{i}"
                
                # Преобразуем в структурированное действие
                story_action = self._create_story_action(
                    action_id,
                    choice,
                    action_data,
                    scene_logic["objects"]
                )
                
                logic_data["story_actions"].append(story_action)
                logic_data["preconditions"][action_id] = action_data["preconditions"]
                logic_data["effects"][action_id] = action_data["effects"]
                
                # Строим граф действий
                if scene.scene_id not in logic_data["action_graph"]:
                    logic_data["action_graph"][scene.scene_id] = []
                
                logic_data["action_graph"][scene.scene_id].append({
                    "action_id": action_id,
                    "next_scene": choice.next_scene,
                    "available": self._check_action_availability(
                        action_data["preconditions"],
                        logic_data["world_state"]
                    )
                })
        
        return logic_data
    
    async def _enhance_with_visuals(self, quest: Quest) -> Dict[str, Any]:
        """Добавление визуализации SceneCraft к квесту"""
        logger.info("Генерируем визуализацию для квеста")
        
        # Проверяем доступность визуализации
        if not self.visualization_available or self.scenecraft is None:
            logger.warning("Визуализация недоступна, возвращаем заглушку")
            return {
                "scenes": [],
                "enhanced_features": {
                    "multi_view_scenes": 0,
                    "scene_layouts": [],
                    "visual_consistency_score": 0.0
                },
                "message": "Визуализация недоступна из-за отсутствующих зависимостей"
            }
        
        # Визуализируем весь квест
        visualization = self.scenecraft.visualize_quest(quest)
        
        # Добавляем дополнительные визуальные элементы
        visualization["enhanced_features"] = {
            "multi_view_scenes": len(visualization["scenes"]),
            "scene_layouts": [],
            "visual_consistency_score": 0.0
        }
        
        # Анализируем визуальную согласованность
        if len(visualization["scenes"]) > 1:
            consistency = self._analyze_visual_consistency(visualization["scenes"])
            visualization["enhanced_features"]["visual_consistency_score"] = consistency
        
        return visualization
    
    def _integrate_logic_and_visuals(self, logic_data: Dict[str, Any],
                                   visualization: Dict[str, Any],
                                   quest: Quest) -> Dict[str, Any]:
        """Интеграция логики и визуализации"""
        logger.info("Интегрируем логику и визуализацию")
        
        integrated = {
            "interactive_scenes": [],
            "object_interactions": {},
            "visual_triggers": []
        }
        
        # Проверяем, есть ли визуализация
        if not visualization.get("scenes"):
            logger.warning("Нет визуализированных сцен для интеграции")
            return integrated
        
        # Для каждой визуализированной сцены добавляем интерактивность
        for scene_viz in visualization["scenes"]:
            scene_id = scene_viz["scene_id"]
            
            # Находим соответствующие действия
            actions = logic_data["action_graph"].get(scene_id, [])
            
            # Загружаем макет сцены
            layout = {}
            if "layout_path" in scene_viz:
                try:
                    with open(scene_viz["layout_path"], 'r', encoding='utf-8') as f:
                        layout = json.load(f)
                except Exception as e:
                    logger.warning(f"Не удалось загрузить макет: {e}")
                    layout = {"objects": []}
            
            # Создаем интерактивную сцену
            interactive_scene = {
                "scene_id": scene_id,
                "visual_data": scene_viz,
                "interactive_objects": [],
                "action_zones": []
            }
            
            # Помечаем интерактивные объекты
            for room in layout.get("rooms", []):
                for obj in room.get("objects", []):
                    # Проверяем, есть ли действия с этим объектом
                    obj_interactions = self._find_object_interactions(
                        obj["label"],
                        actions,
                        logic_data
                    )
                    
                    if obj_interactions:
                        interactive_scene["interactive_objects"].append({
                            "object": obj,
                            "interactions": obj_interactions,
                            "visual_highlight": True
                        })
            
            integrated["interactive_scenes"].append(interactive_scene)
        
        # Создаем визуальные триггеры на основе эффектов
        for action_id, effects in logic_data["effects"].items():
            for effect in effects:
                if effect.get("type") == "change_state":
                    integrated["visual_triggers"].append({
                        "trigger": action_id,
                        "visual_change": {
                            "object": effect.get("object"),
                            "from_state": "default",
                            "to_state": effect.get("new_state"),
                            "animation": self._get_state_change_animation(
                                effect.get("new_state")
                            )
                        }
                    })
        
        return integrated
    
    def _initialize_world_state(self, quest: Quest, 
                              scenario: ScenarioInput) -> Dict[str, Any]:
        """Инициализация начального состояния мира"""
        world_state = {
            "hero": {
                "location": quest.start_scene,
                "inventory": [],
                "attributes": {
                    "type": scenario.hero,
                    "goal": scenario.goal
                }
            },
            "locations": {},
            "objects": {},
            "flags": {}
        }
        
        # Добавляем локации из сцен
        for scene in quest.scenes:
            world_state["locations"][scene.scene_id] = {
                "visited": False,
                "accessible": scene.scene_id == quest.start_scene
            }
        
        return world_state
    
    def _create_story_action(self, action_id: str, choice: Choice,
                           action_data: Dict[str, Any],
                           objects: List[Dict]) -> Dict[str, Any]:
        """Создание структурированного действия"""
        return {
            "id": action_id,
            "description": choice.text,
            "next_scene": choice.next_scene,
            "preconditions": action_data.get("preconditions", []),
            "effects": action_data.get("effects", []),
            "required_objects": [
                obj["name"] for obj in objects 
                if obj["name"].lower() in choice.text.lower()
            ]
        }
    
    def _check_action_availability(self, preconditions: List[Dict],
                                 world_state: Dict[str, Any]) -> bool:
        """Проверка доступности действия в текущем состоянии"""
        if not preconditions:
            return True
        
        for precond in preconditions:
            if precond["type"] == "has_item":
                if precond["item"] not in world_state["hero"]["inventory"]:
                    return False
            elif precond["type"] == "at_location":
                if world_state["hero"]["location"] != precond["location"]:
                    return False
        
        return True
    
    def _analyze_visual_consistency(self, scenes: List[Dict]) -> float:
        """Анализ визуальной согласованности между сценами"""
        # Упрощенная метрика - проверяем, используется ли один стиль
        if not scenes:
            return 1.0
        
        # В реальной реализации здесь был бы анализ изображений
        # Пока возвращаем высокий балл
        return 0.85
    
    def _find_object_interactions(self, object_name: str,
                                actions: List[Dict],
                                logic_data: Dict) -> List[Dict]:
        """Поиск взаимодействий с объектом"""
        interactions = []
        
        for action in actions:
            action_id = action["action_id"]
            
            # Проверяем предусловия
            for precond in logic_data["preconditions"].get(action_id, []):
                if precond.get("item") == object_name:
                    interactions.append({
                        "type": "requires",
                        "action": action_id
                    })
            
            # Проверяем эффекты
            for effect in logic_data["effects"].get(action_id, []):
                if effect.get("object") == object_name:
                    interactions.append({
                        "type": "affects",
                        "action": action_id,
                        "effect": effect.get("type")
                    })
        
        return interactions
    
    def _get_state_change_animation(self, new_state: str) -> str:
        """Получение типа анимации для изменения состояния"""
        animations = {
            "unlocked": "unlock_rotation",
            "open": "swing_open",
            "destroyed": "crumble",
            "taken": "fade_out",
            "active": "power_on"
        }
        return animations.get(new_state, "fade_transition")
    
    async def generate_dynamic_response(self, current_scene: Scene,
                                      user_action: str,
                                      world_state: WorldState) -> Dict[str, Any]:
        """Генерация динамического ответа на неожиданное действие игрока"""
        if not self.enable_dynamic_actions:
            return {
                "success": False,
                "message": "Это действие не предусмотрено в данной сцене"
            }
        
        logger.info(f"Генерируем ответ на действие: {user_action}")
        
        # Используем Story2Game для генерации нового действия
        dynamic_action = self.story2game.generate_dynamic_action(
            user_action,
            current_scene,
            world_state
        )
        
        if dynamic_action:
            # Выполняем действие
            dynamic_action.execute(world_state)
            
            # Генерируем описание результата
            response = {
                "success": True,
                "action": dynamic_action.description,
                "world_changes": self._describe_world_changes(world_state),
                "new_options": self._generate_new_options(world_state, current_scene)
            }
            
            # Опционально генерируем визуализацию изменений
            if self.enable_visualization:
                response["visual_update"] = self._generate_visual_update(
                    current_scene,
                    dynamic_action
                )
            
            return response
        
        return {
            "success": False,
            "message": "Не удалось выполнить это действие",
            "hint": "Попробуйте другой подход"
        }
    
    def _describe_world_changes(self, world_state: WorldState) -> List[str]:
        """Описание изменений в мире после действия"""
        changes = []
        
        # Анализируем историю для последних изменений
        if world_state.history:
            last_action = world_state.history[-1]
            changes.append(f"Выполнено: {last_action}")
        
        return changes
    
    def _generate_new_options(self, world_state: WorldState,
                            current_scene: Scene) -> List[str]:
        """Генерация новых опций после динамического действия"""
        # В реальной реализации здесь был бы вызов LLM
        return [
            "Вернуться к основным действиям",
            "Исследовать последствия действия",
            "Попробовать что-то еще"
        ]
    
    def _generate_visual_update(self, scene: Scene, 
                              action: Any) -> Dict[str, Any]:
        """Генерация визуального обновления после действия"""
        return {
            "type": "partial_update",
            "affected_area": "center",
            "description": f"Визуальное изменение после: {action.description}"
        }
    
    def save_enhanced_quest(self, result: Dict[str, Any], 
                          output_path: str) -> Path:
        """Сохранение расширенного квеста со всеми улучшениями"""
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем базовый квест
        quest_path = output_path / "quest.json"
        self.base_generator.save_quest(result["quest"], str(quest_path))
        
        # Сохраняем логику
        if "logic" in result["enhancements"]:
            logic_path = output_path / "quest_logic.json"
            with open(logic_path, 'w', encoding='utf-8') as f:
                json.dump(result["enhancements"]["logic"], f, 
                         indent=2, ensure_ascii=False)
        
        # Сохраняем код
        if "generated_code" in result["enhancements"]:
            code_path = output_path / "quest_logic.py"
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(result["enhancements"]["generated_code"])
        
        # Сохраняем метаданные визуализации
        if "visualization" in result["enhancements"]:
            viz_meta_path = output_path / "visualization_meta.json"
            with open(viz_meta_path, 'w', encoding='utf-8') as f:
                json.dump(result["enhancements"]["visualization"], f,
                         indent=2, ensure_ascii=False)
        
        # Сохраняем интегрированные данные
        if "integrated" in result["enhancements"]:
            integrated_path = output_path / "integrated_quest.json"
            with open(integrated_path, 'w', encoding='utf-8') as f:
                json.dump(result["enhancements"]["integrated"], f,
                         indent=2, ensure_ascii=False)
        
        logger.info(f"Расширенный квест сохранен в {output_path}")
        return output_path