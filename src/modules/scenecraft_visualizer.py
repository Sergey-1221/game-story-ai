"""
SceneCraft Visualizer - генерация 3D-сцен по текстовому описанию и макету
Основано на подходе SceneCraft (Xiuyu Yang et al., 2024)
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np
from PIL import Image
import torch
from loguru import logger
import json
from pathlib import Path

from src.core.models import Scene, Quest
from src.modules.diffusion_visualizer import DiffusionVisualizer


@dataclass
class BoundingBox3D:
    """3D ограничивающий прямоугольник для объекта"""
    center: Tuple[float, float, float]  # x, y, z
    size: Tuple[float, float, float]    # width, height, depth
    rotation: float = 0.0               # поворот вокруг оси Y
    label: str = ""                     # метка объекта
    semantic_class: str = ""            # семантический класс


@dataclass
class RoomLayout:
    """Макет комнаты"""
    room_id: str
    room_type: str  # bedroom, hall, dungeon, etc.
    dimensions: Tuple[float, float, float]  # ширина, высота, глубина
    objects: List[BoundingBox3D] = field(default_factory=list)
    doors: List[BoundingBox3D] = field(default_factory=list)
    windows: List[BoundingBox3D] = field(default_factory=list)


@dataclass
class SceneLayout:
    """Полный макет сцены"""
    scene_id: str
    description: str
    rooms: List[RoomLayout] = field(default_factory=list)
    connections: List[Tuple[str, str]] = field(default_factory=list)  # связи между комнатами
    style: str = "realistic"
    lighting: str = "natural"


class LayoutGenerator:
    """Генератор макетов из текстовых описаний"""
    
    def __init__(self):
        self.object_sizes = self._load_default_sizes()
        self.room_templates = self._load_room_templates()
    
    def _load_default_sizes(self) -> Dict[str, Tuple[float, float, float]]:
        """Загрузка стандартных размеров объектов"""
        return {
            # Мебель
            "стол": (1.5, 0.8, 0.8),
            "стул": (0.5, 1.0, 0.5),
            "кровать": (2.0, 0.6, 1.5),
            "шкаф": (1.0, 2.0, 0.6),
            "сундук": (1.0, 0.6, 0.6),
            
            # Архитектура
            "дверь": (1.0, 2.0, 0.2),
            "окно": (1.2, 1.5, 0.2),
            "колонна": (0.5, 3.0, 0.5),
            
            # Персонажи
            "охранник": (0.5, 1.8, 0.5),
            "персонаж": (0.5, 1.8, 0.5),
            
            # Предметы
            "ключ": (0.1, 0.05, 0.05),
            "оружие": (0.3, 1.0, 0.1),
            "артефакт": (0.3, 0.3, 0.3),
        }
    
    def _load_room_templates(self) -> Dict[str, Dict[str, Any]]:
        """Загрузка шаблонов комнат"""
        return {
            "тронный_зал": {
                "min_size": (10, 5, 15),
                "typical_objects": ["трон", "колонна", "охранник"],
                "door_positions": ["front", "side"]
            },
            "темница": {
                "min_size": (3, 3, 3),
                "typical_objects": ["решетка", "цепи", "скамья"],
                "door_positions": ["front"]
            },
            "лаборатория": {
                "min_size": (6, 3, 8),
                "typical_objects": ["стол", "стеллаж", "оборудование"],
                "door_positions": ["front", "back"]
            },
            "коридор": {
                "min_size": (2, 3, 10),
                "typical_objects": ["факел", "картина"],
                "door_positions": ["front", "back"]
            }
        }
    
    def generate_layout_from_scene(self, scene: Scene, genre: str) -> SceneLayout:
        """Генерация макета из описания сцены"""
        logger.info(f"Генерируем макет для сцены {scene.scene_id}")
        
        # Анализируем текст сцены
        room_type = self._detect_room_type(scene.text, genre)
        objects = self._extract_objects_from_text(scene.text)
        
        # Создаем базовую комнату
        room = self._create_room(scene.scene_id, room_type, objects)
        
        # Создаем макет сцены
        layout = SceneLayout(
            scene_id=scene.scene_id,
            description=scene.text[:200],
            rooms=[room],
            style=self._determine_style(genre),
            lighting=self._determine_lighting(scene.mood)
        )
        
        return layout
    
    def _detect_room_type(self, text: str, genre: str) -> str:
        """Определение типа помещения из текста"""
        text_lower = text.lower()
        
        # Простой паттерн-матчинг
        if any(word in text_lower for word in ["тронный зал", "трон", "throne"]):
            return "тронный_зал"
        elif any(word in text_lower for word in ["темница", "тюрьма", "клетка", "dungeon"]):
            return "темница"
        elif any(word in text_lower for word in ["лаборатория", "лаб", "исследования"]):
            return "лаборатория"
        elif any(word in text_lower for word in ["коридор", "проход", "туннель"]):
            return "коридор"
        elif any(word in text_lower for word in ["улица", "снаружи", "двор"]):
            return "экстерьер"
        else:
            return "комната"
    
    def _extract_objects_from_text(self, text: str) -> List[str]:
        """Извлечение объектов из текста"""
        objects = []
        text_lower = text.lower()
        
        # Проверяем известные объекты
        for obj_name in self.object_sizes.keys():
            if obj_name in text_lower:
                objects.append(obj_name)
        
        return objects
    
    def _create_room(self, room_id: str, room_type: str, objects: List[str]) -> RoomLayout:
        """Создание комнаты с объектами"""
        # Получаем параметры комнаты
        template = self.room_templates.get(room_type, {
            "min_size": (5, 3, 5),
            "typical_objects": [],
            "door_positions": ["front"]
        })
        
        # Определяем размеры
        room_size = template["min_size"]
        if len(objects) > 5:
            # Увеличиваем размер для большого количества объектов
            room_size = tuple(s * 1.5 for s in room_size)
        
        room = RoomLayout(
            room_id=room_id,
            room_type=room_type,
            dimensions=room_size
        )
        
        # Расставляем объекты
        self._place_objects_in_room(room, objects)
        
        # Добавляем двери
        self._add_doors(room, template["door_positions"])
        
        return room
    
    def _place_objects_in_room(self, room: RoomLayout, object_names: List[str]):
        """Расстановка объектов в комнате"""
        width, height, depth = room.dimensions
        
        # Простой алгоритм расстановки по сетке
        grid_x = int(width / 2)
        grid_z = int(depth / 2)
        
        positions = []
        for i in range(grid_x):
            for j in range(grid_z):
                x = (i + 0.5) * 2 - width/2 + 1
                z = (j + 0.5) * 2 - depth/2 + 1
                positions.append((x, z))
        
        # Расставляем объекты
        for i, obj_name in enumerate(object_names[:len(positions)]):
            if obj_name in self.object_sizes:
                size = self.object_sizes[obj_name]
                x, z = positions[i]
                
                bbox = BoundingBox3D(
                    center=(x, size[1]/2, z),
                    size=size,
                    rotation=np.random.uniform(0, 360),
                    label=obj_name,
                    semantic_class=self._get_semantic_class(obj_name)
                )
                
                room.objects.append(bbox)
    
    def _add_doors(self, room: RoomLayout, door_positions: List[str]):
        """Добавление дверей в комнату"""
        width, _, depth = room.dimensions
        door_size = self.object_sizes["дверь"]
        
        for pos in door_positions:
            if pos == "front":
                center = (0, door_size[1]/2, -depth/2)
            elif pos == "back":
                center = (0, door_size[1]/2, depth/2)
            elif pos == "left":
                center = (-width/2, door_size[1]/2, 0)
            elif pos == "right":
                center = (width/2, door_size[1]/2, 0)
            else:
                continue
            
            door = BoundingBox3D(
                center=center,
                size=door_size,
                rotation=0 if pos in ["front", "back"] else 90,
                label="дверь",
                semantic_class="door"
            )
            
            room.doors.append(door)
    
    def _get_semantic_class(self, obj_name: str) -> str:
        """Получение семантического класса объекта"""
        obj_lower = obj_name.lower()
        
        if any(word in obj_lower for word in ["стол", "стул", "кровать", "шкаф"]):
            return "furniture"
        elif any(word in obj_lower for word in ["дверь", "окно", "стена"]):
            return "architecture"
        elif any(word in obj_lower for word in ["охранник", "враг", "персонаж"]):
            return "character"
        elif any(word in obj_lower for word in ["ключ", "оружие", "артефакт"]):
            return "item"
        else:
            return "object"
    
    def _determine_style(self, genre: str) -> str:
        """Определение визуального стиля по жанру"""
        style_map = {
            "киберпанк": "cyberpunk_neon",
            "фэнтези": "medieval_fantasy",
            "хоррор": "dark_gothic",
            "стимпанк": "steampunk_industrial",
            "детектив": "noir_realistic"
        }
        return style_map.get(genre.lower(), "realistic")
    
    def _determine_lighting(self, mood: Optional[str]) -> str:
        """Определение освещения по настроению"""
        if not mood:
            return "natural"
        
        mood_lower = mood.lower()
        if any(word in mood_lower for word in ["мрачный", "темный", "зловещий"]):
            return "dark_dramatic"
        elif any(word in mood_lower for word in ["яркий", "солнечный", "веселый"]):
            return "bright_cheerful"
        elif any(word in mood_lower for word in ["таинственный", "загадочный"]):
            return "mysterious_fog"
        else:
            return "natural"


class SceneCraftVisualizer:
    """Визуализатор сцен в стиле SceneCraft"""
    
    def __init__(self, diffusion_visualizer: Optional[DiffusionVisualizer] = None):
        self.layout_generator = LayoutGenerator()
        self.diffusion = diffusion_visualizer or DiffusionVisualizer()
        self.view_angles = [(0, 0), (45, 30), (90, 0), (135, -30)]  # азимут, элевация
    
    def visualize_scene(self, scene: Scene, genre: str, 
                       output_dir: str = "output/visualizations") -> Dict[str, Any]:
        """Полная визуализация сцены"""
        logger.info(f"Визуализируем сцену {scene.scene_id}")
        
        # Генерируем макет
        layout = self.layout_generator.generate_layout_from_scene(scene, genre)
        
        # Конвертируем в 2D проекции
        projections = self._create_2d_projections(layout)
        
        # Генерируем изображения с разных ракурсов
        images = self._generate_multiview_images(layout, scene, projections)
        
        # Опционально: создаем 3D представление (заглушка для NeRF)
        nerf_data = self._prepare_nerf_data(images, layout)
        
        # Сохраняем результаты
        results = self._save_visualization(scene.scene_id, layout, images, output_dir)
        
        return results
    
    def _create_2d_projections(self, layout: SceneLayout) -> Dict[str, np.ndarray]:
        """Создание 2D проекций макета"""
        projections = {}
        
        # План сверху (top-down view)
        projections["top"] = self._render_top_view(layout)
        
        # Вид спереди
        projections["front"] = self._render_front_view(layout)
        
        # Схема глубины
        projections["depth"] = self._render_depth_map(layout)
        
        return projections
    
    def _render_top_view(self, layout: SceneLayout) -> np.ndarray:
        """Рендеринг вида сверху"""
        # Определяем размер изображения
        max_size = 20  # максимальный размер в метрах
        resolution = 50  # пикселей на метр
        img_size = int(max_size * resolution)
        
        # Создаем пустое изображение
        img = np.ones((img_size, img_size, 3), dtype=np.uint8) * 255
        
        # Функция преобразования координат
        def world_to_pixel(x, z):
            px = int((x + max_size/2) * resolution)
            py = int((z + max_size/2) * resolution)
            return px, py
        
        # Рисуем комнаты
        for room in layout.rooms:
            width, _, depth = room.dimensions
            
            # Углы комнаты
            corners = [
                (-width/2, -depth/2),
                (width/2, -depth/2),
                (width/2, depth/2),
                (-width/2, depth/2)
            ]
            
            # Рисуем стены
            for i in range(4):
                p1 = world_to_pixel(*corners[i])
                p2 = world_to_pixel(*corners[(i+1)%4])
                self._draw_line(img, p1, p2, color=(0, 0, 0), thickness=3)
            
            # Рисуем объекты
            for obj in room.objects:
                x, _, z = obj.center
                px, py = world_to_pixel(x, z)
                
                # Цвет по семантическому классу
                color_map = {
                    "furniture": (139, 69, 19),  # коричневый
                    "character": (255, 0, 0),     # красный
                    "item": (0, 255, 0),          # зеленый
                    "door": (0, 0, 255)           # синий
                }
                color = color_map.get(obj.semantic_class, (128, 128, 128))
                
                # Рисуем прямоугольник объекта
                w, _, d = obj.size
                half_w = int(w * resolution / 2)
                half_d = int(d * resolution / 2)
                
                img[py-half_d:py+half_d, px-half_w:px+half_w] = color
        
        return img
    
    def _render_front_view(self, layout: SceneLayout) -> np.ndarray:
        """Рендеринг вида спереди"""
        # Упрощенная реализация - рисуем схематичный фронтальный вид
        img_width = 800
        img_height = 600
        img = np.ones((img_height, img_width, 3), dtype=np.uint8) * 240
        
        # Здесь можно добавить более сложную логику проекции
        
        return img
    
    def _render_depth_map(self, layout: SceneLayout) -> np.ndarray:
        """Рендеринг карты глубины"""
        # Создаем карту глубины для ControlNet
        img_size = 512
        depth_map = np.ones((img_size, img_size), dtype=np.float32)
        
        # Простая аппроксимация глубины на основе Y-координат объектов
        
        return (depth_map * 255).astype(np.uint8)
    
    def _generate_multiview_images(self, layout: SceneLayout, scene: Scene,
                                 projections: Dict[str, np.ndarray]) -> List[Image.Image]:
        """Генерация изображений с разных ракурсов"""
        images = []
        
        # Подготавливаем промпт
        style_prompt = f"{layout.style} style, {layout.lighting} lighting"
        scene_prompt = f"{scene.text[:200]}... {style_prompt}"
        
        # Генерируем изображения для каждого ракурса
        for i, (azimuth, elevation) in enumerate(self.view_angles):
            view_prompt = f"{scene_prompt}, view from azimuth {azimuth} elevation {elevation}"
            
            # Используем диффузионную модель с контролем по макету
            if hasattr(self.diffusion, 'generate_with_controlnet'):
                # Используем план сверху как условие
                control_image = Image.fromarray(projections["top"])
                image = self.diffusion.generate_with_controlnet(
                    prompt=view_prompt,
                    control_image=control_image,
                    control_type="canny"
                )
            else:
                # Fallback на обычную генерацию
                image = self.diffusion.generate_scene_image(
                    scene_description=view_prompt,
                    style="realistic",
                    aspect_ratio="16:9"
                )
            
            images.append(image)
        
        return images
    
    def _prepare_nerf_data(self, images: List[Image.Image], 
                         layout: SceneLayout) -> Dict[str, Any]:
        """Подготовка данных для NeRF (заглушка)"""
        # В реальной реализации здесь бы была подготовка данных для обучения NeRF
        nerf_data = {
            "images": len(images),
            "camera_poses": self.view_angles,
            "layout": layout.scene_id,
            "ready_for_training": False
        }
        
        return nerf_data
    
    def _save_visualization(self, scene_id: str, layout: SceneLayout,
                          images: List[Image.Image], output_dir: str) -> Dict[str, Any]:
        """Сохранение результатов визуализации"""
        output_path = Path(output_dir) / scene_id
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем макет
        layout_path = output_path / "layout.json"
        with open(layout_path, 'w', encoding='utf-8') as f:
            json.dump(self._layout_to_dict(layout), f, indent=2, ensure_ascii=False)
        
        # Сохраняем изображения
        image_paths = []
        for i, img in enumerate(images):
            img_path = output_path / f"view_{i}.png"
            img.save(img_path)
            image_paths.append(str(img_path))
        
        # Создаем композитное изображение
        composite = self._create_composite_view(images)
        composite_path = output_path / "composite.png"
        composite.save(composite_path)
        
        return {
            "scene_id": scene_id,
            "layout_path": str(layout_path),
            "image_paths": image_paths,
            "composite_path": str(composite_path),
            "visualization_dir": str(output_path)
        }
    
    def _create_composite_view(self, images: List[Image.Image]) -> Image.Image:
        """Создание композитного изображения из всех ракурсов"""
        if not images:
            return Image.new('RGB', (800, 600), color='white')
        
        # Размер одного изображения
        img_width = images[0].width
        img_height = images[0].height
        
        # Создаем сетку 2x2
        composite_width = img_width * 2
        composite_height = img_height * 2
        composite = Image.new('RGB', (composite_width, composite_height))
        
        # Вставляем изображения
        positions = [(0, 0), (img_width, 0), (0, img_height), (img_width, img_height)]
        
        for i, (img, pos) in enumerate(zip(images[:4], positions)):
            composite.paste(img, pos)
        
        return composite
    
    def _layout_to_dict(self, layout: SceneLayout) -> Dict[str, Any]:
        """Конвертация макета в словарь для сохранения"""
        return {
            "scene_id": layout.scene_id,
            "description": layout.description,
            "style": layout.style,
            "lighting": layout.lighting,
            "rooms": [
                {
                    "room_id": room.room_id,
                    "room_type": room.room_type,
                    "dimensions": room.dimensions,
                    "objects": [
                        {
                            "label": obj.label,
                            "center": obj.center,
                            "size": obj.size,
                            "rotation": obj.rotation,
                            "semantic_class": obj.semantic_class
                        }
                        for obj in room.objects
                    ],
                    "doors": [
                        {
                            "center": door.center,
                            "size": door.size,
                            "rotation": door.rotation
                        }
                        for door in room.doors
                    ]
                }
                for room in layout.rooms
            ],
            "connections": layout.connections
        }
    
    def _draw_line(self, img: np.ndarray, p1: Tuple[int, int], 
                  p2: Tuple[int, int], color: Tuple[int, int, int], thickness: int = 1):
        """Простая отрисовка линии (заглушка для OpenCV)"""
        # В реальной реализации использовался бы cv2.line
        x1, y1 = p1
        x2, y2 = p2
        
        # Простой алгоритм Брезенхема
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        while True:
            if 0 <= x1 < img.shape[1] and 0 <= y1 < img.shape[0]:
                img[y1, x1] = color
            
            if x1 == x2 and y1 == y2:
                break
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy
    
    def visualize_quest(self, quest: Quest, output_dir: str = "output/quest_viz") -> Dict[str, Any]:
        """Визуализация всего квеста"""
        logger.info(f"Визуализируем квест '{quest.title}'")
        
        results = {
            "quest_id": quest.title.replace(" ", "_").lower(),
            "scenes": []
        }
        
        # Визуализируем каждую сцену
        for scene in quest.scenes:
            try:
                scene_viz = self.visualize_scene(scene, quest.genre, output_dir)
                results["scenes"].append(scene_viz)
            except Exception as e:
                logger.error(f"Ошибка визуализации сцены {scene.scene_id}: {e}")
        
        # Создаем общую карту квеста (граф сцен)
        quest_map = self._create_quest_map(quest, output_dir)
        results["quest_map"] = quest_map
        
        return results
    
    def _create_quest_map(self, quest: Quest, output_dir: str) -> str:
        """Создание карты/графа квеста"""
        # Здесь можно использовать библиотеки типа networkx для создания графа
        # Пока возвращаем заглушку
        map_path = Path(output_dir) / "quest_map.json"
        
        quest_graph = {
            "nodes": [
                {"id": scene.scene_id, "label": scene.text[:50] + "..."}
                for scene in quest.scenes
            ],
            "edges": [
                {"from": scene.scene_id, "to": choice.next_scene, "label": choice.text[:30]}
                for scene in quest.scenes
                for choice in scene.choices
                if choice.next_scene
            ]
        }
        
        with open(map_path, 'w', encoding='utf-8') as f:
            json.dump(quest_graph, f, indent=2, ensure_ascii=False)
        
        return str(map_path)