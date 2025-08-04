"""
Модуль экспорта сгенерированного контента в игровые движки
Unreal Engine и Unity с поддержкой различных форматов и структур данных
"""

import os
import json
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import csv
import yaml
from loguru import logger
import zipfile
import shutil

from src.core.models import Quest, Scene, Choice
from src.modules.level_generator import GeneratedLevel, TileType
from src.modules.object_placement import GameObject, ObjectType


class GameEngine(Enum):
    """Поддерживаемые игровые движки"""
    UNREAL_ENGINE = "unreal"
    UNITY = "unity"
    GODOT = "godot"
    GAMEMAKER = "gamemaker"


class ExportFormat(Enum):
    """Форматы экспорта"""
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    YAML = "yaml"
    BLUEPRINT = "blueprint"
    PREFAB = "prefab"


@dataclass
class ExportConfig:
    """Конфигурация экспорта"""
    target_engine: GameEngine
    export_format: ExportFormat
    output_directory: str
    
    # Настройки экспорта
    include_visuals: bool = True
    include_audio_cues: bool = True
    include_localization: bool = False
    compress_output: bool = True
    
    # Специфичные настройки движка
    unreal_project_path: Optional[str] = None
    unity_project_path: Optional[str] = None
    
    # Настройки уровней
    export_levels: bool = True
    level_scale: float = 1.0
    tile_size: float = 100.0  # размер тайла в единицах движка
    
    # Настройки объектов
    export_objects: bool = True
    object_scale: float = 1.0
    
    # Дополнительные опции
    generate_collision: bool = True
    generate_navigation: bool = True
    optimize_for_mobile: bool = False


@dataclass
class UnrealExportData:
    """Данные для экспорта в Unreal Engine"""
    quest_data: Dict[str, Any]
    level_data: Dict[str, Any]
    blueprint_classes: List[Dict[str, Any]]
    material_definitions: List[Dict[str, Any]]
    audio_cues: List[Dict[str, Any]]


@dataclass
class UnityExportData:
    """Данные для экспорта в Unity"""
    quest_scriptable_objects: List[Dict[str, Any]]
    scene_prefabs: List[Dict[str, Any]]
    level_tilemaps: Dict[str, Any]
    component_scripts: List[Dict[str, Any]]
    asset_references: List[Dict[str, Any]]


class UnrealEngineExporter:
    """Экспортер для Unreal Engine"""
    
    def __init__(self, config: ExportConfig):
        self.config = config
        self.blueprint_counter = 0
    
    def export_quest(self, quest: Quest, level: Optional[GeneratedLevel] = None,
                    objects: Optional[List[GameObject]] = None) -> UnrealExportData:
        """Экспорт квеста в формат Unreal Engine"""
        
        logger.info(f"Экспортируем квест '{quest.title}' для Unreal Engine")
        
        # Подготавливаем данные квеста
        quest_data = self._prepare_quest_data(quest)
        
        # Подготавливаем данные уровня
        level_data = self._prepare_level_data(level) if level else {}
        
        # Генерируем Blueprint классы
        blueprint_classes = self._generate_blueprint_classes(quest, objects or [])
        
        # Генерируем определения материалов
        material_definitions = self._generate_material_definitions(level)
        
        # Генерируем аудио кьюи
        audio_cues = self._generate_audio_cues(quest) if self.config.include_audio_cues else []
        
        export_data = UnrealExportData(
            quest_data=quest_data,
            level_data=level_data,
            blueprint_classes=blueprint_classes,
            material_definitions=material_definitions,
            audio_cues=audio_cues
        )
        
        # Экспортируем файлы
        self._write_unreal_files(export_data)
        
        return export_data
    
    def _prepare_quest_data(self, quest: Quest) -> Dict[str, Any]:
        """Подготовка данных квеста для Unreal"""
        return {
            "QuestName": quest.title,
            "QuestID": f"Quest_{hash(quest.title) % 100000}",
            "Genre": quest.genre,
            "Hero": quest.hero,
            "Goal": quest.goal,
            "StartScene": quest.start_scene,
            "Scenes": [self._convert_scene_for_unreal(scene) for scene in quest.scenes],
            "Metadata": quest.metadata
        }
    
    def _convert_scene_for_unreal(self, scene: Scene) -> Dict[str, Any]:
        """Конвертация сцены для Unreal Engine"""
        return {
            "SceneID": scene.scene_id,
            "DisplayName": f"Scene {scene.scene_id}",
            "NarrativeText": scene.text,
            "Mood": scene.mood or "Neutral",
            "Location": scene.location or "Unknown",
            "ImagePrompt": scene.image_prompt,
            "PlayerChoices": [self._convert_choice_for_unreal(choice) for choice in scene.choices],
            "SceneType": "Narrative",
            "RequiredAssets": self._extract_required_assets(scene)
        }
    
    def _convert_choice_for_unreal(self, choice: Choice) -> Dict[str, Any]:
        """Конвертация выбора для Unreal Engine"""
        return {
            "ChoiceText": choice.text,
            "NextSceneID": choice.next_scene,
            "Condition": choice.condition or "",
            "Effect": choice.effect or "",
            "ChoiceType": self._classify_choice_type(choice.text),
            "RequiredFlags": self._extract_choice_flags(choice)
        }
    
    def _classify_choice_type(self, choice_text: str) -> str:
        """Классификация типа выбора"""
        text_lower = choice_text.lower()
        
        if any(word in text_lower for word in ['атаковать', 'сражаться', 'убить']):
            return "Combat"
        elif any(word in text_lower for word in ['говорить', 'спросить', 'сказать']):
            return "Dialogue"
        elif any(word in text_lower for word in ['исследовать', 'поискать', 'осмотреть']):
            return "Exploration"
        elif any(word in text_lower for word in ['взять', 'использовать', 'открыть']):
            return "Interaction"
        else:
            return "General"
    
    def _extract_required_assets(self, scene: Scene) -> List[str]:
        """Извлечение необходимых ассетов из сцены"""
        assets = []
        
        # Анализируем текст сцены на предмет упоминаний объектов
        text_lower = scene.text.lower()
        
        asset_keywords = {
            "Door": ["дверь", "дверца", "ворота"],
            "Key": ["ключ", "карта"],
            "Computer": ["компьютер", "терминал", "консоль"],
            "Weapon": ["оружие", "пистолет", "меч", "нож"],
            "Light": ["свет", "лампа", "фонарь", "факел"]
        }
        
        for asset_type, keywords in asset_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                assets.append(asset_type)
        
        return assets
    
    def _extract_choice_flags(self, choice: Choice) -> List[str]:
        """Извлечение флагов из выбора"""
        flags = []
        
        if choice.condition:
            # Простой парсинг условий
            if "имеет" in choice.condition.lower():
                flags.append("HasItem")
            if "уровень" in choice.condition.lower():
                flags.append("LevelRequirement")
        
        return flags
    
    def _prepare_level_data(self, level: GeneratedLevel) -> Dict[str, Any]:
        """Подготовка данных уровня для Unreal"""
        if not level:
            return {}
        
        return {
            "LevelName": f"GeneratedLevel_{level.metadata.get('seed', 'Unknown')}",
            "Width": level.width,
            "Height": level.height,
            "TileData": level.tiles.tolist(),
            "SpawnPoints": [{"X": pos[0] * self.config.tile_size, "Y": pos[1] * self.config.tile_size} 
                           for pos in level.spawn_points],
            "GoalPoints": [{"X": pos[0] * self.config.tile_size, "Y": pos[1] * self.config.tile_size} 
                          for pos in level.goal_points],
            "SpecialAreas": {
                area_type: [{"X": pos[0] * self.config.tile_size, "Y": pos[1] * self.config.tile_size} 
                           for pos in positions]
                for area_type, positions in level.special_areas.items()
            },
            "TileSize": self.config.tile_size,
            "GenerationMetadata": level.metadata
        }
    
    def _generate_blueprint_classes(self, quest: Quest, objects: List[GameObject]) -> List[Dict[str, Any]]:
        """Генерация Blueprint классов"""
        blueprints = []
        
        # Quest Manager Blueprint
        blueprints.append({
            "ClassName": "BP_QuestManager",
            "ParentClass": "Actor",
            "Components": [
                {
                    "Name": "QuestComponent",
                    "Type": "QuestComponent",
                    "Properties": {
                        "QuestData": f"Quest_{hash(quest.title) % 100000}"
                    }
                }
            ],
            "Functions": [
                {"Name": "StartQuest", "ReturnType": "void"},
                {"Name": "AdvanceToScene", "ReturnType": "void", "Parameters": ["FString SceneID"]},
                {"Name": "MakeChoice", "ReturnType": "void", "Parameters": ["int32 ChoiceIndex"]},
                {"Name": "GetCurrentScene", "ReturnType": "FQuestScene"}
            ]
        })
        
        # Scene Display Blueprint
        blueprints.append({
            "ClassName": "BP_SceneDisplay",
            "ParentClass": "UserWidget",
            "Components": [
                {"Name": "NarrativeText", "Type": "TextBlock"},
                {"Name": "ChoiceButtons", "Type": "VerticalBox"},
                {"Name": "SceneImage", "Type": "Image"}
            ],
            "Functions": [
                {"Name": "DisplayScene", "ReturnType": "void", "Parameters": ["FQuestScene Scene"]},
                {"Name": "CreateChoiceButtons", "ReturnType": "void"},
                {"Name": "OnChoiceSelected", "ReturnType": "void", "Parameters": ["int32 ChoiceIndex"]}
            ]
        })
        
        # Object Blueprints
        for obj in objects:
            blueprints.append(self._create_object_blueprint(obj))
        
        return blueprints
    
    def _create_object_blueprint(self, obj: GameObject) -> Dict[str, Any]:
        """Создание Blueprint для игрового объекта"""
        blueprint = {
            "ClassName": f"BP_{obj.object_type.value.title()}_{obj.object_id}",
            "ParentClass": "Actor",
            "Components": [
                {"Name": "RootComponent", "Type": "SceneComponent"},
                {"Name": "StaticMesh", "Type": "StaticMeshComponent"},
            ]
        }
        
        # Добавляем специфичные компоненты в зависимости от типа
        if obj.object_type == ObjectType.ENEMY:
            blueprint["Components"].extend([
                {"Name": "AIController", "Type": "AIController"},
                {"Name": "Health", "Type": "HealthComponent"},
                {"Name": "Combat", "Type": "CombatComponent"}
            ])
        elif obj.object_type == ObjectType.ITEM:
            blueprint["Components"].append(
                {"Name": "Interaction", "Type": "InteractionComponent"}
            )
        elif obj.object_type == ObjectType.TRAP:
            blueprint["Components"].extend([
                {"Name": "TriggerVolume", "Type": "BoxComponent"},
                {"Name": "Damage", "Type": "DamageComponent"}
            ])
        
        # Добавляем свойства из объекта
        blueprint["Properties"] = obj.properties
        
        return blueprint
    
    def _generate_material_definitions(self, level: Optional[GeneratedLevel]) -> List[Dict[str, Any]]:
        """Генерация определений материалов"""
        materials = []
        
        if not level:
            return materials
        
        # Материалы для тайлов
        tile_materials = {
            TileType.WALL: {
                "MaterialName": "M_Wall",
                "BaseColor": {"R": 0.5, "G": 0.5, "B": 0.5},
                "Roughness": 0.8,
                "Metallic": 0.1
            },
            TileType.FLOOR: {
                "MaterialName": "M_Floor",
                "BaseColor": {"R": 0.8, "G": 0.8, "B": 0.8},
                "Roughness": 0.6,
                "Metallic": 0.0
            },
            TileType.WATER: {
                "MaterialName": "M_Water",
                "BaseColor": {"R": 0.0, "G": 0.3, "B": 0.8},
                "Roughness": 0.1,
                "Metallic": 0.0,
                "Transparency": True
            }
        }
        
        # Получаем уникальные типы тайлов в уровне
        unique_tiles = set(level.tiles.flatten())
        
        for tile_value in unique_tiles:
            try:
                tile_type = TileType(tile_value)
                if tile_type in tile_materials:
                    materials.append(tile_materials[tile_type])
            except ValueError:
                continue
        
        return materials
    
    def _generate_audio_cues(self, quest: Quest) -> List[Dict[str, Any]]:
        """Генерация аудио кьюев"""
        audio_cues = []
        
        # Базовые аудио кьюи для квеста
        base_cues = [
            {
                "CueName": "Quest_Start",
                "SoundWave": f"SW_Quest_Start_{quest.genre}",
                "VolumeMultiplier": 0.8,
                "PitchMultiplier": 1.0
            },
            {
                "CueName": "Quest_Complete",
                "SoundWave": f"SW_Quest_Complete_{quest.genre}",
                "VolumeMultiplier": 1.0,
                "PitchMultiplier": 1.0
            },
            {
                "CueName": "Scene_Transition",
                "SoundWave": "SW_Scene_Transition",
                "VolumeMultiplier": 0.6,
                "PitchMultiplier": 1.0
            }
        ]
        
        audio_cues.extend(base_cues)
        
        # Аудио кьюи для разных настроений сцен
        moods = set(scene.mood for scene in quest.scenes if scene.mood)
        
        mood_audio_map = {
            "напряженная": "SW_Tension",
            "таинственная": "SW_Mystery",
            "action": "SW_Action",
            "спокойная": "SW_Calm"
        }
        
        for mood in moods:
            if mood in mood_audio_map:
                audio_cues.append({
                    "CueName": f"Mood_{mood}",
                    "SoundWave": mood_audio_map[mood],
                    "VolumeMultiplier": 0.7,
                    "PitchMultiplier": 1.0
                })
        
        return audio_cues
    
    def _write_unreal_files(self, export_data: UnrealExportData):
        """Запись файлов для Unreal Engine"""
        
        output_dir = Path(self.config.output_directory) / "Unreal"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Экспортируем данные квеста
        quest_file = output_dir / "QuestData.json"
        with open(quest_file, 'w', encoding='utf-8') as f:
            json.dump(export_data.quest_data, f, ensure_ascii=False, indent=2)
        
        # Экспортируем данные уровня
        if export_data.level_data:
            level_file = output_dir / "LevelData.json"
            with open(level_file, 'w', encoding='utf-8') as f:
                json.dump(export_data.level_data, f, ensure_ascii=False, indent=2)
        
        # Экспортируем Blueprint классы
        blueprint_dir = output_dir / "Blueprints"
        blueprint_dir.mkdir(exist_ok=True)
        
        for blueprint in export_data.blueprint_classes:
            blueprint_file = blueprint_dir / f"{blueprint['ClassName']}.json"
            with open(blueprint_file, 'w', encoding='utf-8') as f:
                json.dump(blueprint, f, ensure_ascii=False, indent=2)
        
        # Экспортируем материалы
        if export_data.material_definitions:
            materials_file = output_dir / "Materials.json"
            with open(materials_file, 'w', encoding='utf-8') as f:
                json.dump(export_data.material_definitions, f, ensure_ascii=False, indent=2)
        
        # Экспортируем аудио кьюи
        if export_data.audio_cues:
            audio_file = output_dir / "AudioCues.json"
            with open(audio_file, 'w', encoding='utf-8') as f:
                json.dump(export_data.audio_cues, f, ensure_ascii=False, indent=2)
        
        # Создаем README с инструкциями
        readme_content = self._generate_unreal_readme()
        readme_file = output_dir / "README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        logger.info(f"Файлы Unreal Engine экспортированы в: {output_dir}")
    
    def _generate_unreal_readme(self) -> str:
        """Генерация README для Unreal Engine"""
        return """# Unreal Engine Quest Import Instructions

## Файлы экспорта

- `QuestData.json` - Основные данные квеста
- `LevelData.json` - Данные сгенерированного уровня
- `Blueprints/` - Blueprint классы для импорта
- `Materials.json` - Определения материалов
- `AudioCues.json` - Аудио кьюи

## Инструкции по импорту

1. Создайте новый проект Unreal Engine или откройте существующий
2. Создайте папку `QuestSystem` в Content Browser
3. Импортируйте JSON файлы как Data Assets
4. Создайте Blueprint классы на основе файлов из папки Blueprints/
5. Настройте материалы согласно Materials.json
6. Импортируйте аудио файлы и создайте Sound Cues согласно AudioCues.json

## Использование

1. Добавьте BP_QuestManager на уровень
2. Настройте UI используя BP_SceneDisplay
3. Запустите квест через QuestManager

## Дополнительная настройка

- Настройте Input Mapping для взаимодействия с квестом
- Добавьте анимации и эффекты по необходимости
- Настройте освещение и постобработку для атмосферы
"""


class UnityExporter:
    """Экспортер для Unity"""
    
    def __init__(self, config: ExportConfig):
        self.config = config
    
    def export_quest(self, quest: Quest, level: Optional[GeneratedLevel] = None,
                    objects: Optional[List[GameObject]] = None) -> UnityExportData:
        """Экспорт квеста в формат Unity"""
        
        logger.info(f"Экспортируем квест '{quest.title}' для Unity")
        
        # Подготавливаем ScriptableObjects для квеста
        quest_scriptable_objects = self._prepare_scriptable_objects(quest)
        
        # Подготавливаем префабы сцен
        scene_prefabs = self._prepare_scene_prefabs(quest)
        
        # Подготавливаем Tilemap данные
        level_tilemaps = self._prepare_tilemap_data(level) if level else {}
        
        # Генерируем скрипты компонентов
        component_scripts = self._generate_component_scripts(quest, objects or [])
        
        # Подготавливаем ссылки на ассеты
        asset_references = self._prepare_asset_references(quest, level, objects or [])
        
        export_data = UnityExportData(
            quest_scriptable_objects=quest_scriptable_objects,
            scene_prefabs=scene_prefabs,
            level_tilemaps=level_tilemaps,
            component_scripts=component_scripts,
            asset_references=asset_references
        )
        
        # Экспортируем файлы
        self._write_unity_files(export_data)
        
        return export_data
    
    def _prepare_scriptable_objects(self, quest: Quest) -> List[Dict[str, Any]]:
        """Подготовка ScriptableObjects для Unity"""
        scriptable_objects = []
        
        # Главный ScriptableObject квеста
        quest_so = {
            "ClassName": "QuestData",
            "FileName": f"Quest_{quest.title.replace(' ', '_')}.asset",
            "Fields": {
                "questName": quest.title,
                "questID": f"quest_{hash(quest.title) % 100000}",
                "genre": quest.genre,
                "hero": quest.hero,
                "goal": quest.goal,
                "startSceneID": quest.start_scene,
                "scenes": [scene.scene_id for scene in quest.scenes]
            }
        }
        scriptable_objects.append(quest_so)
        
        # ScriptableObjects для сцен
        for scene in quest.scenes:
            scene_so = {
                "ClassName": "SceneData",
                "FileName": f"Scene_{scene.scene_id}.asset",
                "Fields": {
                    "sceneID": scene.scene_id,
                    "narrativeText": scene.text,
                    "mood": scene.mood or "Neutral",
                    "location": scene.location or "Unknown",
                    "imagePrompt": scene.image_prompt,
                    "choices": [self._convert_choice_for_unity(choice) for choice in scene.choices]
                }
            }
            scriptable_objects.append(scene_so)
        
        return scriptable_objects
    
    def _convert_choice_for_unity(self, choice: Choice) -> Dict[str, Any]:
        """Конвертация выбора для Unity"""
        return {
            "text": choice.text,
            "nextSceneID": choice.next_scene,
            "condition": choice.condition or "",
            "effect": choice.effect or "",
            "choiceType": self._classify_choice_type_unity(choice.text)
        }
    
    def _classify_choice_type_unity(self, choice_text: str) -> str:
        """Классификация типа выбора для Unity"""
        text_lower = choice_text.lower()
        
        if any(word in text_lower for word in ['атаковать', 'сражаться']):
            return "Combat"
        elif any(word in text_lower for word in ['говорить', 'спросить']):
            return "Dialogue"
        elif any(word in text_lower for word in ['исследовать', 'поискать']):
            return "Exploration"
        elif any(word in text_lower for word in ['взять', 'использовать']):
            return "Interaction"
        else:
            return "General"
    
    def _prepare_scene_prefabs(self, quest: Quest) -> List[Dict[str, Any]]:
        """Подготовка префабов сцен"""
        prefabs = []
        
        # Базовый префаб UI для отображения сцен
        ui_prefab = {
            "PrefabName": "QuestSceneUI",
            "Components": [
                {
                    "Type": "Canvas",
                    "RenderMode": "ScreenSpaceOverlay"
                },
                {
                    "Type": "CanvasScaler",
                    "UIScaleMode": "ScaleWithScreenSize",
                    "ReferenceResolution": {"x": 1920, "y": 1080}
                }
            ],
            "Children": [
                {
                    "Name": "Background",
                    "Components": [{"Type": "Image", "Color": {"r": 0, "g": 0, "b": 0, "a": 0.8}}]
                },
                {
                    "Name": "NarrativePanel",
                    "Components": [{"Type": "Image"}],
                    "Children": [
                        {
                            "Name": "NarrativeText",
                            "Components": [
                                {
                                    "Type": "Text",
                                    "FontSize": 18,
                                    "Color": {"r": 1, "g": 1, "b": 1, "a": 1},
                                    "Alignment": "MiddleLeft"
                                }
                            ]
                        }
                    ]
                },
                {
                    "Name": "ChoicesPanel",
                    "Components": [
                        {"Type": "VerticalLayoutGroup", "Spacing": 10},
                        {"Type": "ContentSizeFitter", "VerticalFit": "PreferredSize"}
                    ]
                }
            ]
        }
        prefabs.append(ui_prefab)
        
        # Префаб для кнопки выбора
        choice_button_prefab = {
            "PrefabName": "ChoiceButton",
            "Components": [
                {
                    "Type": "Button",
                    "Transition": "ColorTint",
                    "TargetGraphic": "Background"
                },
                {"Type": "Image", "Name": "Background"}
            ],
            "Children": [
                {
                    "Name": "Text",
                    "Components": [
                        {
                            "Type": "Text",
                            "FontSize": 16,
                            "Color": {"r": 0.2, "g": 0.2, "b": 0.2, "a": 1}
                        }
                    ]
                }
            ]
        }
        prefabs.append(choice_button_prefab)
        
        return prefabs
    
    def _prepare_tilemap_data(self, level: GeneratedLevel) -> Dict[str, Any]:
        """Подготовка данных Tilemap для Unity"""
        return {
            "TilemapName": f"GeneratedLevel_{level.metadata.get('seed', 'Unknown')}",
            "Width": level.width,
            "Height": level.height,
            "TileSize": {"x": self.config.tile_size / 100, "y": self.config.tile_size / 100},  # Unity units
            "Tiles": [
                {
                    "Position": {"x": x, "y": y},
                    "TileType": int(level.tiles[y, x]),
                    "SpriteName": self._get_tile_sprite_name(level.tiles[y, x])
                }
                for y in range(level.height)
                for x in range(level.width)
                if level.tiles[y, x] != TileType.EMPTY.value
            ],
            "SpawnPoints": [{"x": pos[0], "y": pos[1]} for pos in level.spawn_points],
            "GoalPoints": [{"x": pos[0], "y": pos[1]} for pos in level.goal_points],
            "SpecialAreas": {
                area_type: [{"x": pos[0], "y": pos[1]} for pos in positions]
                for area_type, positions in level.special_areas.items()
            }
        }
    
    def _get_tile_sprite_name(self, tile_value: int) -> str:
        """Получение имени спрайта для тайла"""
        sprite_map = {
            TileType.WALL.value: "wall_tile",
            TileType.FLOOR.value: "floor_tile",
            TileType.DOOR.value: "door_tile",
            TileType.WATER.value: "water_tile",
            TileType.OBSTACLE.value: "obstacle_tile",
            TileType.TRAP.value: "trap_tile"
        }
        
        try:
            tile_type = TileType(tile_value)
            return sprite_map.get(tile_type, "default_tile")
        except ValueError:
            return "default_tile"
    
    def _generate_component_scripts(self, quest: Quest, objects: List[GameObject]) -> List[Dict[str, Any]]:
        """Генерация скриптов компонентов"""
        scripts = []
        
        # QuestManager скрипт
        quest_manager_script = {
            "ClassName": "QuestManager",
            "FileName": "QuestManager.cs",
            "BaseClass": "MonoBehaviour",
            "Fields": [
                {"Name": "questData", "Type": "QuestData", "SerializeField": True},
                {"Name": "sceneUI", "Type": "QuestSceneUI", "SerializeField": True},
                {"Name": "currentScene", "Type": "SceneData", "Private": True}
            ],
            "Methods": [
                {"Name": "Start", "ReturnType": "void", "Access": "private"},
                {"Name": "StartQuest", "ReturnType": "void", "Access": "public"},
                {"Name": "AdvanceToScene", "ReturnType": "void", "Access": "public", "Parameters": ["string sceneID"]},
                {"Name": "MakeChoice", "ReturnType": "void", "Access": "public", "Parameters": ["int choiceIndex"]},
                {"Name": "GetCurrentScene", "ReturnType": "SceneData", "Access": "public"}
            ]
        }
        scripts.append(quest_manager_script)
        
        # QuestSceneUI скрипт
        scene_ui_script = {
            "ClassName": "QuestSceneUI",
            "FileName": "QuestSceneUI.cs",
            "BaseClass": "MonoBehaviour",
            "Fields": [
                {"Name": "narrativeText", "Type": "Text", "SerializeField": True},
                {"Name": "choicesPanel", "Type": "Transform", "SerializeField": True},
                {"Name": "choiceButtonPrefab", "Type": "GameObject", "SerializeField": True}
            ],
            "Methods": [
                {"Name": "DisplayScene", "ReturnType": "void", "Access": "public", "Parameters": ["SceneData scene"]},
                {"Name": "CreateChoiceButtons", "ReturnType": "void", "Access": "private", "Parameters": ["SceneData scene"]},
                {"Name": "OnChoiceClicked", "ReturnType": "void", "Access": "private", "Parameters": ["int choiceIndex"]}
            ]
        }
        scripts.append(scene_ui_script)
        
        # Скрипты для объектов
        for obj in objects:
            object_script = self._create_object_script(obj)
            scripts.append(object_script)
        
        return scripts
    
    def _create_object_script(self, obj: GameObject) -> Dict[str, Any]:
        """Создание скрипта для игрового объекта"""
        script = {
            "ClassName": f"{obj.object_type.value.title()}Object",
            "FileName": f"{obj.object_type.value.title()}Object.cs",
            "BaseClass": "MonoBehaviour",
            "Fields": [
                {"Name": "objectID", "Type": "string", "Value": obj.object_id},
                {"Name": "objectType", "Type": "ObjectType", "Value": obj.object_type.value}
            ],
            "Methods": [
                {"Name": "Start", "ReturnType": "void", "Access": "private"},
                {"Name": "OnTriggerEnter", "ReturnType": "void", "Access": "private", "Parameters": ["Collider other"]}
            ]
        }
        
        # Добавляем специфичные поля и методы
        if obj.object_type == ObjectType.ENEMY:
            script["Fields"].extend([
                {"Name": "health", "Type": "float", "Value": obj.properties.get("health", 100)},
                {"Name": "damage", "Type": "float", "Value": obj.properties.get("damage", 20)}
            ])
            script["Methods"].extend([
                {"Name": "TakeDamage", "ReturnType": "void", "Access": "public", "Parameters": ["float damage"]},
                {"Name": "Attack", "ReturnType": "void", "Access": "public", "Parameters": ["GameObject target"]}
            ])
        
        elif obj.object_type == ObjectType.ITEM:
            script["Fields"].extend([
                {"Name": "itemType", "Type": "string", "Value": obj.properties.get("item_type", "generic")},
                {"Name": "value", "Type": "int", "Value": obj.properties.get("value", 10)}
            ])
            script["Methods"].append(
                {"Name": "Collect", "ReturnType": "void", "Access": "public", "Parameters": ["GameObject collector"]}
            )
        
        return script
    
    def _prepare_asset_references(self, quest: Quest, level: Optional[GeneratedLevel], 
                                 objects: List[GameObject]) -> List[Dict[str, Any]]:
        """Подготовка ссылок на ассеты"""
        assets = []
        
        # Спрайты для UI
        assets.extend([
            {"Type": "Sprite", "Name": "background_panel", "Path": "UI/Sprites/background_panel"},
            {"Type": "Sprite", "Name": "button_normal", "Path": "UI/Sprites/button_normal"},
            {"Type": "Sprite", "Name": "button_highlighted", "Path": "UI/Sprites/button_highlighted"}
        ])
        
        # Спрайты для тайлов
        if level:
            unique_tiles = set(level.tiles.flatten())
            for tile_value in unique_tiles:
                sprite_name = self._get_tile_sprite_name(tile_value)
                assets.append({
                    "Type": "Sprite",
                    "Name": sprite_name,
                    "Path": f"Tiles/Sprites/{sprite_name}"
                })
        
        # Префабы для объектов
        for obj in objects:
            assets.append({
                "Type": "Prefab",
                "Name": f"{obj.object_type.value}_{obj.object_id}",
                "Path": f"Objects/Prefabs/{obj.object_type.value.title()}"
            })
        
        # Аудио файлы
        if self.config.include_audio_cues:
            audio_files = [
                f"quest_start_{quest.genre}",
                f"quest_complete_{quest.genre}",
                "scene_transition",
                "button_click"
            ]
            
            for audio_file in audio_files:
                assets.append({
                    "Type": "AudioClip",
                    "Name": audio_file,
                    "Path": f"Audio/{audio_file}"
                })
        
        return assets
    
    def _write_unity_files(self, export_data: UnityExportData):
        """Запись файлов для Unity"""
        
        output_dir = Path(self.config.output_directory) / "Unity"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Экспортируем ScriptableObjects
        scriptable_objects_dir = output_dir / "ScriptableObjects"
        scriptable_objects_dir.mkdir(exist_ok=True)
        
        for so in export_data.quest_scriptable_objects:
            so_file = scriptable_objects_dir / so["FileName"]
            with open(so_file.with_suffix('.json'), 'w', encoding='utf-8') as f:
                json.dump(so, f, ensure_ascii=False, indent=2)
        
        # Экспортируем префабы
        prefabs_dir = output_dir / "Prefabs"
        prefabs_dir.mkdir(exist_ok=True)
        
        for prefab in export_data.scene_prefabs:
            prefab_file = prefabs_dir / f"{prefab['PrefabName']}.json"
            with open(prefab_file, 'w', encoding='utf-8') as f:
                json.dump(prefab, f, ensure_ascii=False, indent=2)
        
        # Экспортируем Tilemap данные
        if export_data.level_tilemaps:
            tilemap_file = output_dir / "TilemapData.json"
            with open(tilemap_file, 'w', encoding='utf-8') as f:
                json.dump(export_data.level_tilemaps, f, ensure_ascii=False, indent=2)
        
        # Экспортируем скрипты
        scripts_dir = output_dir / "Scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        for script in export_data.component_scripts:
            script_file = scripts_dir / script["FileName"].replace('.cs', '.json')
            with open(script_file, 'w', encoding='utf-8') as f:
                json.dump(script, f, ensure_ascii=False, indent=2)
        
        # Экспортируем ссылки на ассеты
        assets_file = output_dir / "AssetReferences.json"
        with open(assets_file, 'w', encoding='utf-8') as f:
            json.dump(export_data.asset_references, f, ensure_ascii=False, indent=2)
        
        # Создаем README с инструкциями
        readme_content = self._generate_unity_readme()
        readme_file = output_dir / "README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        logger.info(f"Файлы Unity экспортированы в: {output_dir}")
    
    def _generate_unity_readme(self) -> str:
        """Генерация README для Unity"""
        return """# Unity Quest Import Instructions

## Файлы экспорта

- `ScriptableObjects/` - ScriptableObject определения для квеста и сцен
- `Prefabs/` - Префабы UI элементов
- `Scripts/` - C# скрипты компонентов (в формате JSON для конвертации)
- `TilemapData.json` - Данные сгенерированного уровня
- `AssetReferences.json` - Ссылки на необходимые ассеты

## Инструкции по импорту

1. Создайте новый проект Unity или откройте существующий
2. Создайте папки Assets/QuestSystem/
3. Создайте ScriptableObject классы на основе файлов из ScriptableObjects/
4. Импортируйте префабы из папки Prefabs/
5. Создайте C# скрипты на основе JSON файлов из Scripts/
6. Импортируйте необходимые ассеты согласно AssetReferences.json
7. Создайте Tilemap на основе TilemapData.json

## Структура проекта

```
Assets/
├── QuestSystem/
│   ├── Scripts/
│   ├── ScriptableObjects/
│   ├── Prefabs/
│   ├── Sprites/
│   └── Audio/
```

## Использование

1. Добавьте QuestManager на сцену
2. Настройте ссылки на UI элементы
3. Загрузите данные квеста
4. Запустите систему квестов

## Дополнительная настройка

- Настройте Input System для взаимодействия
- Добавьте анимации для UI
- Настройте аудио микшер
- Создайте спрайты для тайлов и объектов
"""


class GameEngineExportManager:
    """Менеджер экспорта в игровые движки"""
    
    def __init__(self):
        self.exporters = {
            GameEngine.UNREAL_ENGINE: UnrealEngineExporter,
            GameEngine.UNITY: UnityExporter
        }
    
    def export_quest(self, quest: Quest, config: ExportConfig,
                    level: Optional[GeneratedLevel] = None,
                    objects: Optional[List[GameObject]] = None) -> Union[UnrealExportData, UnityExportData]:
        """Экспорт квеста в выбранный игровой движок"""
        
        if config.target_engine not in self.exporters:
            raise ValueError(f"Неподдерживаемый движок: {config.target_engine}")
        
        exporter_class = self.exporters[config.target_engine]
        exporter = exporter_class(config)
        
        # Экспортируем
        export_data = exporter.export_quest(quest, level, objects)
        
        # Сжимаем результат если требуется
        if config.compress_output:
            self._compress_export(config.output_directory, config.target_engine)
        
        return export_data
    
    def _compress_export(self, output_directory: str, engine: GameEngine):
        """Сжатие экспортированных файлов"""
        
        engine_dir = Path(output_directory) / engine.value.title()
        
        if not engine_dir.exists():
            return
        
        # Создаем ZIP архив
        zip_path = Path(output_directory) / f"{engine.value}_export.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(engine_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(engine_dir)
                    zipf.write(file_path, arcname)
        
        logger.info(f"Экспорт сжат в архив: {zip_path}")
    
    def export_to_multiple_engines(self, quest: Quest, configs: List[ExportConfig],
                                  level: Optional[GeneratedLevel] = None,
                                  objects: Optional[List[GameObject]] = None) -> Dict[GameEngine, Any]:
        """Экспорт в несколько игровых движков"""
        
        results = {}
        
        for config in configs:
            try:
                logger.info(f"Экспортируем в {config.target_engine.value}")
                export_data = self.export_quest(quest, config, level, objects)
                results[config.target_engine] = export_data
            except Exception as e:
                logger.error(f"Ошибка экспорта в {config.target_engine.value}: {e}")
                results[config.target_engine] = {"error": str(e)}
        
        return results
    
    def validate_export_config(self, config: ExportConfig) -> List[str]:
        """Валидация конфигурации экспорта"""
        issues = []
        
        # Проверяем выходную директорию
        output_path = Path(config.output_directory)
        if not output_path.parent.exists():
            issues.append(f"Родительская директория не существует: {output_path.parent}")
        
        # Проверяем специфичные настройки движков
        if config.target_engine == GameEngine.UNREAL_ENGINE:
            if config.unreal_project_path and not Path(config.unreal_project_path).exists():
                issues.append(f"Проект Unreal Engine не найден: {config.unreal_project_path}")
        
        elif config.target_engine == GameEngine.UNITY:
            if config.unity_project_path and not Path(config.unity_project_path).exists():
                issues.append(f"Проект Unity не найден: {config.unity_project_path}")
        
        # Проверяем размер тайлов
        if config.tile_size <= 0:
            issues.append("Размер тайла должен быть больше 0")
        
        return issues