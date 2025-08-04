"""
Story2Game Engine - структурированная генерация сюжета с предусловиями и эффектами
Основано на подходе Story2Game (Eric Zhou et al., 2025)
"""

from typing import List, Dict, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import json

from src.core.models import Scene, Choice, ScenarioInput
from src.modules.knowledge_base import KnowledgeBase


class ObjectState(Enum):
    """Возможные состояния игровых объектов"""
    EXISTS = "exists"
    DESTROYED = "destroyed"
    OPEN = "open"
    CLOSED = "closed"
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    ACTIVE = "active"
    INACTIVE = "inactive"
    TAKEN = "taken"
    DROPPED = "dropped"


class RelationType(Enum):
    """Типы отношений между объектами"""
    AT = "at"  # объект находится в локации
    HAS = "has"  # персонаж имеет предмет
    KNOWS = "knows"  # персонаж знает информацию
    BLOCKS = "blocks"  # объект блокирует путь
    REQUIRES = "requires"  # действие требует объект
    UNLOCKS = "unlocks"  # объект открывает другой


@dataclass
class GameObject:
    """Игровой объект с состоянием"""
    id: str
    name: str
    type: str  # item, character, location, information
    state: ObjectState = ObjectState.EXISTS
    attributes: Dict[str, Any] = field(default_factory=dict)
    relations: List[Tuple[RelationType, str]] = field(default_factory=list)


@dataclass
class Precondition:
    """Предусловие для действия"""
    object_id: str
    condition_type: str  # state, relation, attribute
    expected_value: Any
    
    def check(self, world_state: 'WorldState') -> bool:
        """Проверка выполнения предусловия"""
        obj = world_state.get_object(self.object_id)
        if not obj:
            return False
        
        if self.condition_type == "state":
            return obj.state == self.expected_value
        elif self.condition_type == "relation":
            rel_type, target = self.expected_value
            return any(r == (rel_type, target) for r in obj.relations)
        elif self.condition_type == "attribute":
            attr_name, attr_value = self.expected_value
            return obj.attributes.get(attr_name) == attr_value
        
        return False


@dataclass
class Effect:
    """Эффект действия на мир"""
    object_id: str
    effect_type: str  # change_state, add_relation, remove_relation, set_attribute
    new_value: Any
    
    def apply(self, world_state: 'WorldState'):
        """Применение эффекта к состоянию мира"""
        obj = world_state.get_object(self.object_id)
        if not obj:
            return
        
        if self.effect_type == "change_state":
            obj.state = self.new_value
        elif self.effect_type == "add_relation":
            if self.new_value not in obj.relations:
                obj.relations.append(self.new_value)
        elif self.effect_type == "remove_relation":
            if self.new_value in obj.relations:
                obj.relations.remove(self.new_value)
        elif self.effect_type == "set_attribute":
            attr_name, attr_value = self.new_value
            obj.attributes[attr_name] = attr_value


@dataclass
class StoryAction:
    """Действие в истории с логикой"""
    id: str
    description: str
    preconditions: List[Precondition] = field(default_factory=list)
    effects: List[Effect] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)
    
    def is_available(self, world_state: 'WorldState') -> bool:
        """Проверка доступности действия"""
        return all(p.check(world_state) for p in self.preconditions)
    
    def execute(self, world_state: 'WorldState'):
        """Выполнение действия"""
        for effect in self.effects:
            effect.apply(world_state)


class WorldState:
    """Состояние игрового мира"""
    
    def __init__(self):
        self.objects: Dict[str, GameObject] = {}
        self.current_location: Optional[str] = None
        self.history: List[str] = []
    
    def add_object(self, obj: GameObject):
        """Добавление объекта в мир"""
        self.objects[obj.id] = obj
    
    def get_object(self, obj_id: str) -> Optional[GameObject]:
        """Получение объекта по ID"""
        return self.objects.get(obj_id)
    
    def get_objects_by_type(self, obj_type: str) -> List[GameObject]:
        """Получение объектов по типу"""
        return [obj for obj in self.objects.values() if obj.type == obj_type]
    
    def clone(self) -> 'WorldState':
        """Создание копии состояния мира"""
        import copy
        return copy.deepcopy(self)


class Story2GameEngine:
    """Движок генерации структурированных историй с логикой"""
    
    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
        self.world_state = WorldState()
        self.story_actions: Dict[str, StoryAction] = {}
        self.action_templates = self._load_action_templates()
    
    def _load_action_templates(self) -> Dict[str, Dict[str, Any]]:
        """Загрузка шаблонов действий для разных жанров"""
        return {
            "take_item": {
                "preconditions": [
                    {"type": "state", "object": "{item}", "value": ObjectState.EXISTS},
                    {"type": "relation", "object": "{item}", "value": (RelationType.AT, "{location}")}
                ],
                "effects": [
                    {"type": "change_state", "object": "{item}", "value": ObjectState.TAKEN},
                    {"type": "add_relation", "object": "hero", "value": (RelationType.HAS, "{item}")}
                ]
            },
            "unlock_door": {
                "preconditions": [
                    {"type": "state", "object": "{door}", "value": ObjectState.LOCKED},
                    {"type": "relation", "object": "hero", "value": (RelationType.HAS, "{key}")}
                ],
                "effects": [
                    {"type": "change_state", "object": "{door}", "value": ObjectState.UNLOCKED}
                ]
            },
            "defeat_enemy": {
                "preconditions": [
                    {"type": "state", "object": "{enemy}", "value": ObjectState.ACTIVE},
                    {"type": "relation", "object": "hero", "value": (RelationType.HAS, "{weapon}")}
                ],
                "effects": [
                    {"type": "change_state", "object": "{enemy}", "value": ObjectState.DESTROYED},
                    {"type": "remove_relation", "object": "{enemy}", "value": (RelationType.BLOCKS, "{path}")}
                ]
            }
        }
    
    def analyze_scene_for_logic(self, scene: Scene, scenario: ScenarioInput) -> Dict[str, Any]:
        """Анализ сцены для извлечения логических элементов"""
        logger.info(f"Анализируем сцену {scene.scene_id} для логики")
        
        # Извлекаем объекты и действия из текста
        objects = self._extract_objects(scene.text, scenario.genre)
        actions = self._extract_actions(scene.choices, objects)
        
        # Определяем предусловия и эффекты
        logic_data = {
            "objects": objects,
            "actions": []
        }
        
        for choice in scene.choices:
            action_logic = self._infer_action_logic(choice.text, objects, scenario.genre)
            logic_data["actions"].append({
                "choice_text": choice.text,
                "next_scene": choice.next_scene,
                "preconditions": action_logic["preconditions"],
                "effects": action_logic["effects"]
            })
        
        return logic_data
    
    def _extract_objects(self, text: str, genre: str) -> List[Dict[str, Any]]:
        """Извлечение игровых объектов из текста"""
        # Упрощенная реализация - в реальности нужен NER или LLM
        objects = []
        
        # Ищем типичные объекты для жанра
        genre_objects = self.kb.get_story_elements("objects", genre, count=10)
        
        for obj_name in genre_objects:
            if obj_name.lower() in text.lower():
                objects.append({
                    "name": obj_name,
                    "type": self._classify_object(obj_name),
                    "state": ObjectState.EXISTS
                })
        
        return objects
    
    def _extract_actions(self, choices: List[Choice], objects: List[Dict]) -> List[str]:
        """Извлечение действий из вариантов выбора"""
        actions = []
        
        for choice in choices:
            # Простой паттерн-матчинг для определения типа действия
            text_lower = choice.text.lower()
            
            if any(word in text_lower for word in ["взять", "забрать", "подобрать", "take"]):
                actions.append("take_item")
            elif any(word in text_lower for word in ["открыть", "взломать", "unlock", "open"]):
                actions.append("unlock_door")
            elif any(word in text_lower for word in ["атаковать", "победить", "сразиться", "attack"]):
                actions.append("defeat_enemy")
            else:
                actions.append("custom_action")
        
        return actions
    
    def _infer_action_logic(self, action_text: str, objects: List[Dict], genre: str) -> Dict[str, Any]:
        """Определение логики действия"""
        # В реальной реализации здесь был бы вызов LLM для анализа
        # Пока используем простые правила
        
        preconditions = []
        effects = []
        
        text_lower = action_text.lower()
        
        # Анализ предусловий
        if "ключ" in text_lower or "key" in text_lower:
            preconditions.append({
                "type": "has_item",
                "item": "key"
            })
        
        if "оружие" in text_lower or "weapon" in text_lower:
            preconditions.append({
                "type": "has_item",
                "item": "weapon"
            })
        
        # Анализ эффектов
        if "открыть" in text_lower or "unlock" in text_lower:
            effects.append({
                "type": "change_state",
                "object": "door",
                "new_state": "unlocked"
            })
        
        if "взять" in text_lower or "take" in text_lower:
            for obj in objects:
                if obj["name"].lower() in text_lower:
                    effects.append({
                        "type": "add_to_inventory",
                        "item": obj["name"]
                    })
        
        return {
            "preconditions": preconditions,
            "effects": effects
        }
    
    def generate_dynamic_action(self, user_action: str, current_scene: Scene, 
                              world_state: WorldState) -> Optional[StoryAction]:
        """Генерация нового действия для неожиданного ввода игрока"""
        logger.info(f"Генерируем динамическое действие для: {user_action}")
        
        # Анализируем намерение игрока
        intent = self._analyze_user_intent(user_action)
        
        # Проверяем, возможно ли действие в текущем состоянии
        available_objects = self._get_available_objects(world_state, current_scene)
        
        # Генерируем новое действие если возможно
        if self._can_generate_action(intent, available_objects):
            return self._create_dynamic_action(intent, available_objects, world_state)
        
        return None
    
    def _analyze_user_intent(self, user_action: str) -> Dict[str, Any]:
        """Анализ намерения пользователя"""
        # Упрощенный анализ - в реальности нужен NLU
        intent = {
            "action_type": "unknown",
            "target": None,
            "method": None
        }
        
        action_lower = user_action.lower()
        
        if any(word in action_lower for word in ["осмотреть", "изучить", "examine"]):
            intent["action_type"] = "examine"
        elif any(word in action_lower for word in ["использовать", "применить", "use"]):
            intent["action_type"] = "use"
        elif any(word in action_lower for word in ["поговорить", "спросить", "talk"]):
            intent["action_type"] = "talk"
        
        return intent
    
    def _get_available_objects(self, world_state: WorldState, scene: Scene) -> List[GameObject]:
        """Получение доступных объектов в текущей сцене"""
        location_id = world_state.current_location
        available = []
        
        for obj in world_state.objects.values():
            # Объект доступен если он в текущей локации или у героя
            if any(rel == (RelationType.AT, location_id) for rel in obj.relations):
                available.append(obj)
            elif any(rel[0] == RelationType.HAS and rel[1] == obj.id 
                    for rel in world_state.get_object("hero").relations):
                available.append(obj)
        
        return available
    
    def _can_generate_action(self, intent: Dict, objects: List[GameObject]) -> bool:
        """Проверка возможности генерации действия"""
        # Проверяем, есть ли подходящие объекты для действия
        if intent["action_type"] == "examine":
            return len(objects) > 0
        elif intent["action_type"] == "use":
            return any(obj.type == "item" for obj in objects)
        elif intent["action_type"] == "talk":
            return any(obj.type == "character" for obj in objects)
        
        return False
    
    def _create_dynamic_action(self, intent: Dict, objects: List[GameObject], 
                             world_state: WorldState) -> StoryAction:
        """Создание динамического действия"""
        action_id = f"dynamic_{len(self.story_actions)}"
        
        # Базовое описание действия
        if intent["action_type"] == "examine":
            target = objects[0] if objects else "окружение"
            description = f"Вы внимательно осматриваете {target.name if hasattr(target, 'name') else target}"
        else:
            description = "Вы пытаетесь выполнить необычное действие"
        
        # Создаем действие без жестких предусловий
        action = StoryAction(
            id=action_id,
            description=description,
            preconditions=[],
            effects=[]
        )
        
        # Добавляем эффект записи в историю
        action.effects.append(
            Effect(
                object_id="hero",
                effect_type="set_attribute",
                new_value=("last_action", intent["action_type"])
            )
        )
        
        return action
    
    def _classify_object(self, obj_name: str) -> str:
        """Классификация типа объекта"""
        obj_lower = obj_name.lower()
        
        if any(word in obj_lower for word in ["ключ", "меч", "чип", "артефакт", "key", "sword"]):
            return "item"
        elif any(word in obj_lower for word in ["дверь", "ворота", "замок", "door", "gate"]):
            return "obstacle"
        elif any(word in obj_lower for word in ["охранник", "враг", "страж", "guard", "enemy"]):
            return "character"
        elif any(word in obj_lower for word in ["комната", "зал", "коридор", "room", "hall"]):
            return "location"
        else:
            return "object"
    
    def export_to_code(self, story_actions: List[StoryAction], language: str = "python") -> str:
        """Экспорт логики истории в исполняемый код"""
        if language == "python":
            return self._export_to_python(story_actions)
        elif language == "javascript":
            return self._export_to_javascript(story_actions)
        else:
            return json.dumps([action.__dict__ for action in story_actions], indent=2)
    
    def _export_to_python(self, actions: List[StoryAction]) -> str:
        """Экспорт в Python код"""
        code = """# Автоматически сгенерированная логика квеста

class QuestLogic:
    def __init__(self):
        self.world_state = {}
        self.inventory = []
        self.current_scene = 'start'
    
    def check_preconditions(self, action_id):
        \"\"\"Проверка предусловий действия\"\"\"
"""
        
        for action in actions:
            code += f"""
        if action_id == '{action.id}':
            # {action.description}
            conditions = []
"""
            for precond in action.preconditions:
                code += f"            conditions.append(self._check_{precond.condition_type}('{precond.object_id}', {repr(precond.expected_value)}))\n"
            
            code += "            return all(conditions)\n"
        
        code += """
        return False
    
    def execute_action(self, action_id):
        \"\"\"Выполнение действия\"\"\"
"""
        
        for action in actions:
            code += f"""
        if action_id == '{action.id}':
            # Применяем эффекты
"""
            for effect in action.effects:
                code += f"            self._apply_{effect.effect_type}('{effect.object_id}', {repr(effect.new_value)})\n"
        
        return code
    
    def _export_to_javascript(self, actions: List[StoryAction]) -> str:
        """Экспорт в JavaScript код"""
        # Аналогичная реализация для JS
        pass