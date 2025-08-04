"""
Модуль интеграции диффузионных моделей для генерации визуальных представлений сцен
с поддержкой Stable Diffusion, ControlNet и других современных подходов
"""

import os
import asyncio
import base64
import io
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
from loguru import logger
import torch
from diffusers import (
    StableDiffusionPipeline, 
    StableDiffusionImg2ImgPipeline,
    StableDiffusionControlNetPipeline,
    ControlNetModel,
    DDIMScheduler,
    DPMSolverMultistepScheduler
)
from transformers import pipeline, BlipProcessor, BlipForConditionalGeneration
import requests
from controlnet_aux import (
    CannyDetector, 
    OpenposeDetector, 
    MidasDetector,
    LineartDetector
)

from src.core.models import Scene, ScenarioInput, Choice
from src.modules.level_generator import GeneratedLevel


class VisualizationStyle(Enum):
    """Стили визуализации"""
    REALISTIC = "realistic"
    ARTISTIC = "artistic"
    CONCEPT_ART = "concept_art"
    PIXEL_ART = "pixel_art"
    CYBERPUNK = "cyberpunk"
    FANTASY = "fantasy"
    HORROR = "horror"
    MINIMALIST = "minimalist"


class ControlNetType(Enum):
    """Типы ControlNet для управления генерацией"""
    CANNY = "canny"
    OPENPOSE = "openpose"
    DEPTH = "depth"
    LINEART = "lineart"
    SCRIBBLE = "scribble"
    SEMANTIC = "semantic"


@dataclass
class VisualizationConfig:
    """Конфигурация для визуализации"""
    model_id: str = "runwayml/stable-diffusion-v1-5"
    style: VisualizationStyle = VisualizationStyle.REALISTIC
    image_size: Tuple[int, int] = (768, 512)
    num_inference_steps: int = 20
    guidance_scale: float = 7.5
    negative_prompt: str = "blurry, low quality, distorted, text, watermark"
    
    # ControlNet настройки
    use_controlnet: bool = False
    controlnet_type: ControlNetType = ControlNetType.CANNY
    controlnet_conditioning_scale: float = 1.0
    
    # Постобработка
    enhance_quality: bool = True
    add_lighting_effects: bool = True
    composition_guidance: bool = True
    
    # Кеширование
    cache_models: bool = True
    output_format: str = "PNG"


@dataclass
class GeneratedVisualization:
    """Результат визуализации"""
    image: Image.Image
    prompt: str
    negative_prompt: str
    metadata: Dict[str, Any]
    control_image: Optional[Image.Image] = None
    seed: Optional[int] = None


class PromptEngineer:
    """Инженер промптов для диффузионных моделей"""
    
    def __init__(self):
        self.genre_styles = {
            "киберпанк": {
                "style_keywords": ["cyberpunk", "neon lights", "dystopian", "futuristic", "high-tech"],
                "atmosphere": ["dark", "moody", "atmospheric lighting", "rain", "fog"],
                "colors": ["neon blue", "electric pink", "dark purple", "metallic silver"],
                "elements": ["holographic displays", "cyber implants", "urban decay", "skyscrapers"]
            },
            "фэнтези": {
                "style_keywords": ["fantasy", "magical", "medieval", "mystical", "enchanted"],
                "atmosphere": ["ethereal", "golden hour", "mystical fog", "ancient"],
                "colors": ["emerald green", "royal blue", "golden", "deep purple"],
                "elements": ["magic particles", "ancient runes", "stone architecture", "forest"]
            },
            "хоррор": {
                "style_keywords": ["horror", "dark", "gothic", "sinister", "eerie"],
                "atmosphere": ["ominous", "shadowy", "dramatic lighting", "fog", "moonlight"],
                "colors": ["deep red", "black", "dark grey", "sickly green"],
                "elements": ["shadows", "decay", "abandoned", "twisted architecture"]
            },
            "постапокалипсис": {
                "style_keywords": ["post-apocalyptic", "wasteland", "destroyed", "abandoned"],
                "atmosphere": ["desolate", "dusty", "harsh sunlight", "storm clouds"],
                "colors": ["rust brown", "sandy yellow", "faded colors", "grey"],
                "elements": ["ruins", "debris", "overgrown vegetation", "makeshift structures"]
            }
        }
        
        self.quality_enhancers = [
            "highly detailed", "8k resolution", "professional photography",
            "cinematic lighting", "masterpiece", "award winning"
        ]
    
    def create_scene_prompt(
        self, 
        scene: Scene, 
        scenario: ScenarioInput, 
        style: VisualizationStyle,
        level_context: Optional[GeneratedLevel] = None
    ) -> str:
        """Создание промпта для визуализации сцены"""
        
        # Базовое описание сцены
        base_description = self._extract_visual_elements(scene.text)
        
        # Жанровые элементы
        genre_elements = self._get_genre_elements(scenario.genre)
        
        # Стилевые элементы
        style_elements = self._get_style_elements(style)
        
        # Композиционные элементы
        composition = self._determine_composition(scene, level_context)
        
        # Атмосферные элементы
        atmosphere = self._get_atmosphere_elements(scene.mood or "neutral", scenario.genre)
        
        # Составляем финальный промпт
        prompt_parts = []
        
        # Основное описание
        prompt_parts.append(base_description)
        
        # Композиция и перспектива
        prompt_parts.append(composition)
        
        # Жанровые элементы
        if genre_elements:
            prompt_parts.append(", ".join(genre_elements[:3]))
        
        # Стиль
        prompt_parts.append(style_elements)
        
        # Атмосфера
        prompt_parts.append(atmosphere)
        
        # Качественные модификаторы
        prompt_parts.extend(self.quality_enhancers[:2])
        
        final_prompt = ", ".join(filter(None, prompt_parts))
        
        # Ограничиваем длину промпта
        if len(final_prompt.split()) > 75:
            words = final_prompt.split()
            final_prompt = " ".join(words[:75])
        
        return final_prompt
    
    def _extract_visual_elements(self, scene_text: str) -> str:
        """Извлечение визуальных элементов из текста сцены"""
        # Упрощенная обработка - ищем описания локаций, объектов, действий
        visual_keywords = []
        
        # Ключевые слова для поиска визуальных элементов
        location_words = ["комната", "коридор", "улица", "лес", "здание", "дом", "лаборатория", "офис"]
        object_words = ["дверь", "стол", "компьютер", "окно", "лестница", "машина", "дерево"]
        lighting_words = ["свет", "тьма", "тень", "яркий", "тусклый", "неон", "лампа"]
        
        scene_lower = scene_text.lower()
        
        for word in location_words + object_words + lighting_words:
            if word in scene_lower:
                visual_keywords.append(word)
        
        # Если не нашли специфичных элементов, используем общее описание
        if not visual_keywords:
            # Берем первые несколько предложений
            sentences = scene_text.split('.')[:2]
            return '. '.join(sentences).strip()
        
        return "scene with " + ", ".join(visual_keywords[:5])
    
    def _get_genre_elements(self, genre: str) -> List[str]:
        """Получение элементов жанра"""
        genre_lower = genre.lower()
        if genre_lower in self.genre_styles:
            elements = self.genre_styles[genre_lower]
            return elements["style_keywords"] + elements["elements"][:2]
        return []
    
    def _get_style_elements(self, style: VisualizationStyle) -> str:
        """Получение стилевых элементов"""
        style_mappings = {
            VisualizationStyle.REALISTIC: "photorealistic, detailed textures, natural lighting",
            VisualizationStyle.ARTISTIC: "artistic rendering, painterly style, expressive",
            VisualizationStyle.CONCEPT_ART: "concept art, digital painting, cinematic",
            VisualizationStyle.PIXEL_ART: "pixel art style, retro gaming, 16-bit",
            VisualizationStyle.CYBERPUNK: "cyberpunk aesthetic, neon colors, futuristic",
            VisualizationStyle.FANTASY: "fantasy art, magical atmosphere, ethereal",
            VisualizationStyle.HORROR: "horror atmosphere, dark mood, ominous",
            VisualizationStyle.MINIMALIST: "minimalist design, clean lines, simple composition"
        }
        
        return style_mappings.get(style, "artistic rendering")
    
    def _determine_composition(self, scene: Scene, level_context: Optional[GeneratedLevel]) -> str:
        """Определение композиции изображения"""
        # Базовые композиционные элементы
        compositions = [
            "wide shot establishing scene",
            "medium shot character focus", 
            "close-up dramatic moment",
            "bird's eye view overview",
            "low angle dramatic perspective"
        ]
        
        # Выбираем композицию на основе контекста сцены
        if scene.location:
            if "комната" in scene.location.lower() or "офис" in scene.location.lower():
                return "interior scene, medium shot"
            elif "улица" in scene.location.lower() or "город" in scene.location.lower():
                return "urban environment, wide establishing shot"
        
        # Анализируем количество выборов для определения типа сцены
        if len(scene.choices) > 2:
            return "complex scene with multiple elements, wide shot"
        elif len(scene.choices) == 1:
            return "focused dramatic moment, medium close-up"
        
        return "balanced composition, medium shot"
    
    def _get_atmosphere_elements(self, mood: str, genre: str) -> str:
        """Получение атмосферных элементов"""
        mood_mappings = {
            "напряженная": "tense atmosphere, dramatic shadows, high contrast",
            "таинственная": "mysterious mood, fog, dim lighting",
            "action": "dynamic action scene, motion blur, intense lighting",
            "спокойная": "calm peaceful atmosphere, soft lighting",
            "угрожающая": "threatening atmosphere, ominous shadows, dark mood"
        }
        
        atmosphere = mood_mappings.get(mood, "atmospheric lighting, cinematic mood")
        
        # Добавляем жанровые атмосферные элементы
        if genre.lower() in self.genre_styles:
            genre_atmosphere = self.genre_styles[genre.lower()]["atmosphere"][:2]
            atmosphere += ", " + ", ".join(genre_atmosphere)
        
        return atmosphere
    
    def create_negative_prompt(self, base_negative: str, style: VisualizationStyle) -> str:
        """Создание негативного промпта"""
        base_elements = [
            "blurry", "low quality", "distorted", "deformed", "ugly",
            "text", "watermark", "signature", "logo", "bad anatomy"
        ]
        
        style_specific = {
            VisualizationStyle.REALISTIC: ["cartoon", "anime", "drawing", "painting"],
            VisualizationStyle.ARTISTIC: ["photograph", "realistic", "photographic"],
            VisualizationStyle.PIXEL_ART: ["smooth", "anti-aliased", "high resolution"],
            VisualizationStyle.CONCEPT_ART: ["amateur", "sketch", "unfinished"]
        }
        
        negative_elements = base_elements.copy()
        if style in style_specific:
            negative_elements.extend(style_specific[style])
        
        return ", ".join(negative_elements)


class ControlNetProcessor:
    """Процессор для подготовки управляющих изображений ControlNet"""
    
    def __init__(self):
        self.canny_detector = CannyDetector()
        self.openpose_detector = OpenposeDetector.from_pretrained("lllyasviel/Annotators")
        self.depth_detector = MidasDetector.from_pretrained("lllyasviel/Annotators")
        self.lineart_detector = LineartDetector.from_pretrained("lllyasviel/Annotators")
    
    def process_level_for_controlnet(
        self, 
        level: GeneratedLevel, 
        controlnet_type: ControlNetType,
        scene_position: Optional[Tuple[int, int]] = None
    ) -> Image.Image:
        """Обработка уровня для создания управляющего изображения"""
        
        # Создаем базовое изображение уровня
        level_image = self._create_level_visualization(level, scene_position)
        
        # Применяем соответствующий детектор
        if controlnet_type == ControlNetType.CANNY:
            return self.canny_detector(level_image)
        elif controlnet_type == ControlNetType.DEPTH:
            return self.depth_detector(level_image)
        elif controlnet_type == ControlNetType.LINEART:
            return self.lineart_detector(level_image)
        else:
            # Для других типов возвращаем базовое изображение
            return level_image
    
    def _create_level_visualization(
        self, 
        level: GeneratedLevel, 
        focus_position: Optional[Tuple[int, int]] = None
    ) -> Image.Image:
        """Создание визуализации уровня для ControlNet"""
        
        # Простая визуализация уровня
        height, width = level.tiles.shape
        image = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Цвета для тайлов (более контрастные для ControlNet)
        tile_colors = {
            0: (0, 0, 0),       # Пустота - черный
            1: (255, 255, 255), # Стена - белый
            2: (128, 128, 128), # Пол - серый
            3: (200, 200, 200), # Дверь - светло-серый
        }
        
        for y in range(height):
            for x in range(width):
                tile_value = level.tiles[y, x]
                if tile_value in tile_colors:
                    image[y, x] = tile_colors[tile_value]
        
        # Выделяем фокусную позицию если указана
        if focus_position:
            fx, fy = focus_position
            if 0 <= fx < width and 0 <= fy < height:
                cv2.circle(image, (fx, fy), 2, (255, 0, 0), -1)
        
        # Увеличиваем изображение
        scale_factor = 16
        large_image = cv2.resize(image, (width * scale_factor, height * scale_factor), 
                               interpolation=cv2.INTER_NEAREST)
        
        return Image.fromarray(large_image)


class DiffusionVisualizer:
    """Основной класс для генерации визуализаций с помощью диффузионных моделей"""
    
    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()
        self.prompt_engineer = PromptEngineer()
        self.controlnet_processor = ControlNetProcessor()
        
        # Кешированные модели
        self._cached_pipeline = None
        self._cached_controlnet_pipeline = None
        self._cached_img2img_pipeline = None
        
        # Проверяем доступность CUDA
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        
        logger.info(f"Инициализирована генерация изображений на устройстве: {self.device}")
    
    def _load_pipeline(self) -> StableDiffusionPipeline:
        """Загрузка основного пайплайна Stable Diffusion"""
        if self._cached_pipeline is None or not self.config.cache_models:
            logger.info(f"Загружаем модель: {self.config.model_id}")
            
            self._cached_pipeline = StableDiffusionPipeline.from_pretrained(
                self.config.model_id,
                torch_dtype=self.dtype,
                safety_checker=None,
                requires_safety_checker=False
            ).to(self.device)
            
            # Оптимизируем для производительности
            if self.device == "cuda":
                self._cached_pipeline.enable_model_cpu_offload()
                self._cached_pipeline.enable_xformers_memory_efficient_attention()
            
            # Улучшенный планировщик
            self._cached_pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                self._cached_pipeline.scheduler.config
            )
        
        return self._cached_pipeline
    
    def _load_controlnet_pipeline(self, controlnet_type: ControlNetType) -> StableDiffusionControlNetPipeline:
        """Загрузка пайплайна с ControlNet"""
        if self._cached_controlnet_pipeline is None or not self.config.cache_models:
            logger.info(f"Загружаем ControlNet: {controlnet_type.value}")
            
            # Выбираем подходящую модель ControlNet
            controlnet_models = {
                ControlNetType.CANNY: "lllyasviel/sd-controlnet-canny",
                ControlNetType.OPENPOSE: "lllyasviel/sd-controlnet-openpose",
                ControlNetType.DEPTH: "lllyasviel/sd-controlnet-depth",
                ControlNetType.LINEART: "lllyasviel/sd-controlnet-lineart"
            }
            
            controlnet_model_id = controlnet_models.get(
                controlnet_type, 
                "lllyasviel/sd-controlnet-canny"
            )
            
            controlnet = ControlNetModel.from_pretrained(
                controlnet_model_id,
                torch_dtype=self.dtype
            )
            
            self._cached_controlnet_pipeline = StableDiffusionControlNetPipeline.from_pretrained(
                self.config.model_id,
                controlnet=controlnet,
                torch_dtype=self.dtype,
                safety_checker=None,
                requires_safety_checker=False
            ).to(self.device)
            
            if self.device == "cuda":
                self._cached_controlnet_pipeline.enable_model_cpu_offload()
                self._cached_controlnet_pipeline.enable_xformers_memory_efficient_attention()
        
        return self._cached_controlnet_pipeline
    
    async def generate_scene_visualization(
        self, 
        scene: Scene, 
        scenario: ScenarioInput,
        level_context: Optional[GeneratedLevel] = None,
        custom_config: Optional[VisualizationConfig] = None
    ) -> GeneratedVisualization:
        """Асинхронная генерация визуализации сцены"""
        
        config = custom_config or self.config
        
        logger.info(f"Генерируем визуализацию для сцены: {scene.scene_id}")
        
        # Создаем промпт
        prompt = self.prompt_engineer.create_scene_prompt(
            scene, scenario, config.style, level_context
        )
        
        negative_prompt = self.prompt_engineer.create_negative_prompt(
            config.negative_prompt, config.style
        )
        
        # Генерируем в отдельном потоке для избежания блокировки
        loop = asyncio.get_event_loop()
        
        if config.use_controlnet and level_context:
            result = await loop.run_in_executor(
                None, 
                self._generate_with_controlnet, 
                prompt, negative_prompt, config, level_context, scene
            )
        else:
            result = await loop.run_in_executor(
                None, 
                self._generate_basic, 
                prompt, negative_prompt, config
            )
        
        return result
    
    def generate_scene_image(
        self, 
        scene_description: str, 
        style: str = "realistic", 
        aspect_ratio: str = "16:9"
    ) -> Image.Image:
        """Синхронная генерация изображения сцены для совместимости с SceneCraftVisualizer"""
        
        try:
            # Определяем размер изображения по соотношению сторон
            if aspect_ratio == "16:9":
                size = (1024, 576)
            elif aspect_ratio == "4:3":
                size = (1024, 768)
            elif aspect_ratio == "1:1":
                size = (1024, 1024)
            else:
                size = (1024, 576)  # default
            
            # Создаем конфигурацию для генерации
            config = VisualizationConfig(
                image_size=size,
                style=VisualizationStyle(style) if style in [s.value for s in VisualizationStyle] else VisualizationStyle.REALISTIC,
                num_inference_steps=20,  # Быстрая генерация
                guidance_scale=7.5
            )
            
            # Обновляем промпт в зависимости от стиля
            styled_prompt = f"{scene_description}, {style} style, high quality, detailed"
            
            # Запускаем базовую генерацию
            pipeline = self._load_pipeline()
            
            generator = torch.Generator(device=self.device)
            seed = torch.randint(0, 2**32, (1,)).item()
            generator.manual_seed(seed)
            
            with torch.autocast(self.device):
                result = pipeline(
                    prompt=styled_prompt,
                    negative_prompt="low quality, blurry, distorted, ugly, deformed",
                    height=config.image_size[1],
                    width=config.image_size[0],
                    num_inference_steps=config.num_inference_steps,
                    guidance_scale=config.guidance_scale,
                    generator=generator
                )
            
            return result.images[0]
            
        except Exception as e:
            logger.error(f"Ошибка при генерации изображения сцены: {e}")
            # Возвращаем заглушку
            return self._create_placeholder_image(size)
    
    def generate_with_controlnet(
        self, 
        prompt: str, 
        control_image: Image.Image, 
        control_type: str = "canny"
    ) -> Image.Image:
        """Синхронная генерация с ControlNet для совместимости с SceneCraftVisualizer"""
        
        try:
            # Преобразуем строковый тип в enum
            controlnet_type_map = {
                "canny": ControlNetType.CANNY,
                "openpose": ControlNetType.OPENPOSE,
                "depth": ControlNetType.DEPTH,
                "lineart": ControlNetType.LINEART
            }
            
            controlnet_type = controlnet_type_map.get(control_type, ControlNetType.CANNY)
            
            # Загружаем пайплайн с ControlNet
            pipeline = self._load_controlnet_pipeline(controlnet_type)
            
            # Обрабатываем control image в зависимости от типа
            processed_control = self.controlnet_processor.process_control_image(
                control_image, controlnet_type
            )
            
            generator = torch.Generator(device=self.device)
            seed = torch.randint(0, 2**32, (1,)).item()
            generator.manual_seed(seed)
            
            with torch.autocast(self.device):
                result = pipeline(
                    prompt=prompt,
                    image=processed_control,
                    negative_prompt="low quality, blurry, distorted, ugly, deformed",
                    height=1024,
                    width=1024,
                    num_inference_steps=20,
                    guidance_scale=7.5,
                    controlnet_conditioning_scale=1.0,
                    generator=generator
                )
            
            return result.images[0]
            
        except Exception as e:
            logger.error(f"Ошибка при генерации с ControlNet: {e}")
            # Fallback на обычную генерацию
            return self.generate_scene_image(prompt, "realistic", "1:1")
    
    def _generate_basic(
        self, 
        prompt: str, 
        negative_prompt: str, 
        config: VisualizationConfig
    ) -> GeneratedVisualization:
        """Базовая генерация без ControlNet"""
        
        pipeline = self._load_pipeline()
        
        # Устанавливаем сид для воспроизводимости
        generator = torch.Generator(device=self.device)
        seed = torch.randint(0, 2**32, (1,)).item()
        generator.manual_seed(seed)
        
        try:
            # Генерируем изображение
            with torch.autocast(self.device):
                result = pipeline(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    height=config.image_size[1],
                    width=config.image_size[0],
                    num_inference_steps=config.num_inference_steps,
                    guidance_scale=config.guidance_scale,
                    generator=generator
                )
            
            image = result.images[0]
            
            # Постобработка
            if config.enhance_quality:
                image = self._enhance_image_quality(image)
            
            return GeneratedVisualization(
                image=image,
                prompt=prompt,
                negative_prompt=negative_prompt,
                seed=seed,
                metadata={
                    "model": config.model_id,
                    "style": config.style.value,
                    "steps": config.num_inference_steps,
                    "guidance": config.guidance_scale,
                    "size": config.image_size
                }
            )
            
        except Exception as e:
            logger.error(f"Ошибка при генерации изображения: {e}")
            # Возвращаем заглушку
            placeholder = self._create_placeholder_image(config.image_size)
            return GeneratedVisualization(
                image=placeholder,
                prompt=prompt,
                negative_prompt=negative_prompt,
                metadata={"error": str(e)}
            )
    
    def _generate_with_controlnet(
        self, 
        prompt: str, 
        negative_prompt: str, 
        config: VisualizationConfig,
        level_context: GeneratedLevel,
        scene: Scene
    ) -> GeneratedVisualization:
        """Генерация с использованием ControlNet"""
        
        pipeline = self._load_controlnet_pipeline(config.controlnet_type)
        
        # Создаем управляющее изображение
        control_image = self.controlnet_processor.process_level_for_controlnet(
            level_context, config.controlnet_type
        )
        
        # Изменяем размер управляющего изображения
        control_image = control_image.resize(config.image_size, Image.LANCZOS)
        
        generator = torch.Generator(device=self.device)
        seed = torch.randint(0, 2**32, (1,)).item()
        generator.manual_seed(seed)
        
        try:
            with torch.autocast(self.device):
                result = pipeline(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    image=control_image,
                    height=config.image_size[1],
                    width=config.image_size[0],
                    num_inference_steps=config.num_inference_steps,
                    guidance_scale=config.guidance_scale,
                    controlnet_conditioning_scale=config.controlnet_conditioning_scale,
                    generator=generator
                )
            
            image = result.images[0]
            
            if config.enhance_quality:
                image = self._enhance_image_quality(image)
            
            return GeneratedVisualization(
                image=image,
                prompt=prompt,
                negative_prompt=negative_prompt,
                control_image=control_image,
                seed=seed,
                metadata={
                    "model": config.model_id,
                    "controlnet_type": config.controlnet_type.value,
                    "style": config.style.value,
                    "conditioning_scale": config.controlnet_conditioning_scale
                }
            )
            
        except Exception as e:
            logger.error(f"Ошибка при генерации с ControlNet: {e}")
            placeholder = self._create_placeholder_image(config.image_size)
            return GeneratedVisualization(
                image=placeholder,
                prompt=prompt,
                negative_prompt=negative_prompt,
                metadata={"error": str(e)}
            )
    
    def _enhance_image_quality(self, image: Image.Image) -> Image.Image:
        """Улучшение качества изображения"""
        # Простое улучшение контраста и резкости
        from PIL import ImageEnhance
        
        # Увеличиваем контраст
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.1)
        
        # Увеличиваем резкость
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.1)
        
        return image
    
    def _create_placeholder_image(self, size: Tuple[int, int]) -> Image.Image:
        """Создание изображения-заглушки при ошибке"""
        image = Image.new('RGB', size, color='lightgray')
        draw = ImageDraw.Draw(image)
        
        # Добавляем текст
        text = "Image generation\nfailed"
        bbox = draw.textbbox((0, 0), text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2
        
        draw.text((x, y), text, fill='black', anchor='mm')
        
        return image
    
    def generate_batch_visualizations(
        self, 
        scenes: List[Scene], 
        scenario: ScenarioInput,
        level_context: Optional[GeneratedLevel] = None
    ) -> List[GeneratedVisualization]:
        """Батчевая генерация визуализаций"""
        
        logger.info(f"Генерируем визуализации для {len(scenes)} сцен")
        results = []
        
        for i, scene in enumerate(scenes):
            logger.info(f"Обрабатываем сцену {i+1}/{len(scenes)}: {scene.scene_id}")
            
            # Запускаем синхронную генерацию
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    self.generate_scene_visualization(scene, scenario, level_context)
                )
                results.append(result)
            finally:
                loop.close()
        
        return results
    
    def save_visualization(
        self, 
        visualization: GeneratedVisualization, 
        output_path: str,
        include_metadata: bool = True
    ):
        """Сохранение визуализации"""
        
        # Сохраняем основное изображение
        visualization.image.save(output_path, format=self.config.output_format)
        
        if include_metadata:
            # Сохраняем метаданные
            metadata_path = Path(output_path).with_suffix('.json')
            metadata = {
                "prompt": visualization.prompt,
                "negative_prompt": visualization.negative_prompt,
                "seed": visualization.seed,
                **visualization.metadata
            }
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # Сохраняем управляющее изображение если есть
            if visualization.control_image:
                control_path = Path(output_path).with_name(
                    f"{Path(output_path).stem}_control{Path(output_path).suffix}"
                )
                visualization.control_image.save(control_path)
        
        logger.info(f"Визуализация сохранена: {output_path}")
    
    def cleanup_models(self):
        """Очистка кешированных моделей для освобождения памяти"""
        if self._cached_pipeline:
            del self._cached_pipeline
            self._cached_pipeline = None
        
        if self._cached_controlnet_pipeline:
            del self._cached_controlnet_pipeline
            self._cached_controlnet_pipeline = None
        
        if self._cached_img2img_pipeline:
            del self._cached_img2img_pipeline
            self._cached_img2img_pipeline = None
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("Кеш моделей очищен")