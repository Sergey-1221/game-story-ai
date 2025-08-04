import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from loguru import logger

from src.core.models import Quest, Scene, Choice


class OutputFormatter:
    """Модуль форматирования и вывода квеста в JSON"""
    
    def __init__(self, pretty_print: bool = True, validate_json: bool = True):
        self.pretty_print = pretty_print
        self.validate_json = validate_json
    
    def format_quest(self, quest: Quest, 
                    include_metadata: bool = False,
                    include_paths: bool = False) -> Dict[str, Any]:
        """Форматирование квеста в словарь для JSON"""
        
        # Базовая структура
        quest_data = {
            "quest": {
                "title": quest.title,
                "genre": quest.genre,
                "hero": quest.hero,
                "goal": quest.goal,
                "start_scene": quest.start_scene,
                "scenes": self._format_scenes(quest.scenes)
            }
        }
        
        # Опционально добавляем метаданные
        if include_metadata:
            quest_data["quest"]["metadata"] = {
                "generated_at": datetime.now().isoformat(),
                "total_scenes": len(quest.scenes),
                "total_branches": quest.metadata.get('total_branches', 0),
                "max_depth": quest.metadata.get('max_depth', 0),
                "warnings": quest.metadata.get('warnings', [])
            }
        
        # Опционально добавляем информацию о путях
        if include_paths and quest.paths:
            quest_data["quest"]["paths"] = [
                {
                    "path_id": path.path_id,
                    "length": path.length,
                    "is_main": path.is_main,
                    "outcome": path.outcome,
                    "scenes": path.scenes
                }
                for path in quest.paths
            ]
        
        return quest_data
    
    def _format_scenes(self, scenes: List[Scene]) -> List[Dict[str, Any]]:
        """Форматирование списка сцен"""
        formatted_scenes = []
        
        for scene in scenes:
            scene_data = {
                "scene_id": scene.scene_id,
                "text": scene.text,
                "choices": self._format_choices(scene.choices)
            }
            
            # Добавляем опциональные поля, если они есть
            if scene.mood:
                scene_data["mood"] = scene.mood
            if scene.location:
                scene_data["location"] = scene.location
            if scene.image_prompt:
                scene_data["image_prompt"] = scene.image_prompt
            
            formatted_scenes.append(scene_data)
        
        return formatted_scenes
    
    def _format_choices(self, choices: List[Choice]) -> List[Dict[str, Any]]:
        """Форматирование вариантов выбора"""
        formatted_choices = []
        
        for choice in choices:
            choice_data = {
                "text": choice.text,
                "next_scene": choice.next_scene
            }
            
            # Добавляем опциональные поля
            if choice.condition:
                choice_data["condition"] = choice.condition
            if choice.effect:
                choice_data["effect"] = choice.effect
            
            formatted_choices.append(choice_data)
        
        return formatted_choices
    
    def save_to_file(self, quest: Quest, file_path: str, 
                    include_metadata: bool = False,
                    include_paths: bool = False) -> Path:
        """Сохранение квеста в JSON файл"""
        file_path = Path(file_path)
        
        # Создаем директорию, если не существует
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Форматируем данные
        quest_data = self.format_quest(quest, include_metadata, include_paths)
        
        # Валидация JSON перед сохранением
        if self.validate_json:
            self._validate_json_structure(quest_data)
        
        # Сохраняем
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if self.pretty_print:
                    json.dump(quest_data, f, ensure_ascii=False, indent=2)
                else:
                    json.dump(quest_data, f, ensure_ascii=False)
            
            logger.info(f"Квест успешно сохранен в {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Ошибка сохранения файла: {e}")
            raise
    
    def save_minimal_format(self, quest: Quest, file_path: str) -> Path:
        """Сохранение в минимальном формате (только требуемые поля)"""
        file_path = Path(file_path)
        
        # Минимальный формат - только сцены
        scenes_data = []
        
        for scene in quest.scenes:
            scene_data = {
                "scene_id": scene.scene_id,
                "text": scene.text,
                "choices": [
                    {
                        "text": choice.text,
                        "next_scene": choice.next_scene
                    }
                    for choice in scene.choices
                ]
            }
            scenes_data.append(scene_data)
        
        # Сохраняем массив сцен
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(scenes_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Квест сохранен в минимальном формате: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
            raise
    
    def _validate_json_structure(self, data: Dict[str, Any]):
        """Валидация структуры JSON перед сохранением"""
        try:
            # Проверяем, что данные сериализуемы
            json.dumps(data)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Данные не могут быть сериализованы в JSON: {e}")
        
        # Проверка обязательных полей
        if "quest" not in data:
            raise ValueError("Отсутствует корневой элемент 'quest'")
        
        quest_data = data["quest"]
        required_fields = ["scenes"]
        
        for field in required_fields:
            if field not in quest_data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
        
        # Проверка сцен
        scenes = quest_data["scenes"]
        if not isinstance(scenes, list):
            raise ValueError("Поле 'scenes' должно быть массивом")
        
        if not scenes:
            raise ValueError("Массив сцен пуст")
        
        for i, scene in enumerate(scenes):
            if "scene_id" not in scene:
                raise ValueError(f"Сцена {i} не имеет scene_id")
            if "text" not in scene:
                raise ValueError(f"Сцена {scene.get('scene_id', i)} не имеет текста")
            if "choices" not in scene:
                raise ValueError(f"Сцена {scene.get('scene_id', i)} не имеет choices")
    
    def export_for_visualization(self, quest: Quest) -> Dict[str, Any]:
        """Экспорт данных для визуализации (например, для графа)"""
        nodes = []
        edges = []
        
        # Создаем узлы
        for scene in quest.scenes:
            node = {
                "id": scene.scene_id,
                "label": f"{scene.scene_id}\n{scene.text[:30]}...",
                "type": "scene",
                "mood": scene.mood or "neutral"
            }
            nodes.append(node)
        
        # Создаем рёбра
        for scene in quest.scenes:
            for i, choice in enumerate(scene.choices):
                if choice.next_scene:
                    edge = {
                        "from": scene.scene_id,
                        "to": choice.next_scene,
                        "label": choice.text[:20] + "...",
                        "choice_index": i
                    }
                    edges.append(edge)
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "title": quest.title,
                "genre": quest.genre,
                "total_scenes": len(quest.scenes),
                "start_scene": quest.start_scene
            }
        }
    
    def export_for_game_engine(self, quest: Quest, engine: str = "unity") -> Dict[str, Any]:
        """Экспорт для игровых движков"""
        if engine.lower() == "unity":
            return self._export_unity_format(quest)
        elif engine.lower() == "godot":
            return self._export_godot_format(quest)
        else:
            # Универсальный формат
            return self.format_quest(quest, include_metadata=True)
    
    def _export_unity_format(self, quest: Quest) -> Dict[str, Any]:
        """Формат для Unity"""
        return {
            "questData": {
                "id": quest.title.replace(" ", "_").lower(),
                "displayName": quest.title,
                "description": quest.goal,
                "startNode": quest.start_scene,
                "nodes": [
                    {
                        "nodeId": scene.scene_id,
                        "nodeType": "dialogue",
                        "content": scene.text,
                        "responses": [
                            {
                                "text": choice.text,
                                "nextNode": choice.next_scene,
                                "condition": choice.condition
                            }
                            for choice in scene.choices
                        ]
                    }
                    for scene in quest.scenes
                ]
            }
        }
    
    def _export_godot_format(self, quest: Quest) -> Dict[str, Any]:
        """Формат для Godot"""
        return {
            "resource_type": "DialogueResource",
            "title": quest.title,
            "start_id": quest.start_scene,
            "dialogues": {
                scene.scene_id: {
                    "text": scene.text,
                    "options": [
                        {
                            "label": choice.text,
                            "next": choice.next_scene
                        }
                        for choice in scene.choices
                    ]
                }
                for scene in quest.scenes
            }
        }