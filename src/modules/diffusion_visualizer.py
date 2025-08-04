"""
Модуль интеграции OpenAI DALL-E для генерации визуальных представлений сцен
Использует OpenAI API для создания изображений высокого качества
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
from loguru import logger
import requests
import openai
from openai import OpenAI

from src.core.models import Scene, ScenarioInput, Choice
from src.modules.level_generator import GeneratedLevel


class VisualizationStyle(Enum):
    """Стили визуализации для DALL-E"""
    REALISTIC = "photorealistic, high quality, detailed"
    ARTISTIC = "artistic, stylized, creative"
    CONCEPT_ART = "concept art, digital painting, fantasy art"
    PIXEL_ART = "pixel art, 8-bit style, retro gaming"
    CYBERPUNK = "cyberpunk, neon lights, futuristic, dark atmosphere"
    FANTASY = "fantasy art, magical, mystical, ethereal"
    HORROR = "horror, dark, ominous, scary atmosphere"
    MINIMALIST = "minimalist, clean, simple, modern design"


class ImageQuality(Enum):
    """Качество изображений DALL-E"""
    STANDARD = "standard"
    HD = "hd"


@dataclass
class VisualizationConfig:
    """Конфигурация для генерации изображений через OpenAI DALL-E"""
    # Основные параметры DALL-E
    model: str = "dall-e-3"  # dall-e-2 или dall-e-3
    style: VisualizationStyle = VisualizationStyle.REALISTIC
    quality: ImageQuality = ImageQuality.STANDARD  # standard или hd
    size: str = "1024x1024"  # 1024x1024, 1792x1024, 1024x1792
    
    # Параметры промпта
    negative_prompt: str = "low quality, blurry, distorted, ugly, deformed, text, watermark"
    max_prompt_length: int = 4000  # Максимальная длина промпта для DALL-E
    
    # Настройки генерации
    n_images: int = 1  # Количество вариантов (максимум 10 для dall-e-2, 1 для dall-e-3)
    
    # OpenAI API настройки
    api_key: Optional[str] = None
    timeout: int = 120  # Таймаут запроса в секундах
    output_format: str = "PNG"
    
    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.getenv("OPENAI_API_KEY")
        
        # Ограничения для DALL-E 3
        if self.model == "dall-e-3":
            self.n_images = 1  # DALL-E 3 поддерживает только 1 изображение
        
        # Проверяем валидность размера
        valid_sizes_dalle3 = ["1024x1024", "1792x1024", "1024x1792"]
        valid_sizes_dalle2 = ["256x256", "512x512", "1024x1024"]
        
        if self.model == "dall-e-3" and self.size not in valid_sizes_dalle3:
            self.size = "1024x1024"
        elif self.model == "dall-e-2" and self.size not in valid_sizes_dalle2:
            self.size = "1024x1024"


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


# ControlNet код удален - используем только DALL-E генерацию


class DiffusionVisualizer:
    """Основной класс для генерации изображений с помощью OpenAI DALL-E"""
    
    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()
        self.prompt_engineer = PromptEngineer()
        
        # Инициализируем OpenAI клиент
        try:
            self.client = OpenAI(
                api_key=self.config.api_key,
                timeout=self.config.timeout
            )
        except Exception as e:
            logger.error(f"Ошибка инициализации OpenAI клиента: {e}")
            self.client = None
        
        logger.info(f"Инициализирована генерация изображений через OpenAI DALL-E (модель: {self.config.model})")
    
    async def generate_scene_visualization(
        self, 
        scene: Scene, 
        scenario: ScenarioInput,
        level_context: Optional[GeneratedLevel] = None,
        custom_config: Optional[VisualizationConfig] = None
    ) -> GeneratedVisualization:
        """Асинхронная генерация визуализации сцены через DALL-E"""
        
        config = custom_config or self.config
        
        logger.info(f"Генерируем визуализацию для сцены: {scene.scene_id}")
        
        # Создаем промпт
        prompt = self.prompt_engineer.create_scene_prompt(
            scene, scenario, config.style, level_context
        )
        
        # Генерируем в отдельном потоке для избежания блокировки
        loop = asyncio.get_event_loop()
        
        result = await loop.run_in_executor(
            None, 
            self._generate_dalle_image, 
            prompt, config
        )
        
        return result
    
    def _generate_dalle_image(
        self, 
        prompt: str, 
        config: VisualizationConfig
    ) -> GeneratedVisualization:
        """Базовая генерация изображения через DALL-E"""
        
        if not self.client:
            logger.error("OpenAI клиент не инициализирован")
            placeholder = self._create_placeholder_image()
            return GeneratedVisualization(
                image=placeholder,
                prompt=prompt,
                metadata={"error": "OpenAI клиент не доступен"}
            )
        
        try:
            # Обрезаем промпт если он слишком длинный
            if len(prompt) > config.max_prompt_length:
                prompt = prompt[:config.max_prompt_length-3] + "..."
            
            logger.info(f"Генерируем изображение через DALL-E: {prompt[:100]}...")
            
            # Генерируем изображение через OpenAI API
            response = self.client.images.generate(
                model=config.model,
                prompt=prompt,
                n=1,
                size=config.size,
                quality=config.quality.value,
                response_format="url"
            )
            
            # Скачиваем изображение
            image_url = response.data[0].url
            image_response = requests.get(image_url, timeout=30)
            image_response.raise_for_status()
            
            # Конвертируем в PIL Image
            image = Image.open(io.BytesIO(image_response.content))
            
            logger.info("Изображение успешно сгенерировано через DALL-E")
            
            return GeneratedVisualization(
                image=image,
                prompt=prompt,
                metadata={
                    "model": config.model,
                    "size": config.size,
                    "quality": config.quality.value
                }
            )
            
        except Exception as e:
            logger.error(f"Ошибка при генерации изображения через DALL-E: {e}")
            placeholder = self._create_placeholder_image()
            return GeneratedVisualization(
                image=placeholder,
                prompt=prompt,
                metadata={"error": str(e)}
            )
    
    def generate_scene_image(
        self, 
        scene_description: str, 
        style: str = "realistic", 
        aspect_ratio: str = "16:9"
    ) -> Image.Image:
        """Синхронная генерация изображения сцены через OpenAI DALL-E"""
        
        if not self.client:
            logger.error("OpenAI клиент не инициализирован")
            return self._create_placeholder_image()
        
        try:
            # Определяем размер изображения по соотношению сторон
            if aspect_ratio == "16:9":
                size = "1792x1024"
            elif aspect_ratio == "4:3":
                size = "1024x1024"  # Ближайший доступный размер
            elif aspect_ratio == "1:1":
                size = "1024x1024"
            else:
                size = "1024x1024"  # default
            
            # Определяем стиль
            style_mapping = {
                "realistic": VisualizationStyle.REALISTIC,
                "artistic": VisualizationStyle.ARTISTIC,
                "concept_art": VisualizationStyle.CONCEPT_ART,
                "pixel_art": VisualizationStyle.PIXEL_ART,
                "cyberpunk": VisualizationStyle.CYBERPUNK,
                "fantasy": VisualizationStyle.FANTASY,
                "horror": VisualizationStyle.HORROR,
                "minimalist": VisualizationStyle.MINIMALIST
            }
            
            selected_style = style_mapping.get(style, VisualizationStyle.REALISTIC)
            
            # Создаем промпт с учетом стиля
            styled_prompt = f"{scene_description}, {selected_style.value}"
            
            # Обрезаем промпт если он слишком длинный
            if len(styled_prompt) > self.config.max_prompt_length:
                styled_prompt = styled_prompt[:self.config.max_prompt_length-3] + "..."
            
            logger.info(f"Генерируем изображение через DALL-E: {styled_prompt[:100]}...")
            
            # Генерируем изображение через OpenAI API
            response = self.client.images.generate(
                model=self.config.model,
                prompt=styled_prompt,
                n=1,
                size=size,
                quality=self.config.quality.value,
                response_format="url"
            )
            
            # Скачиваем изображение
            image_url = response.data[0].url
            image_response = requests.get(image_url, timeout=30)
            image_response.raise_for_status()
            
            # Конвертируем в PIL Image
            image = Image.open(io.BytesIO(image_response.content))
            
            logger.info("Изображение успешно сгенерировано через DALL-E")
            return image
            
        except Exception as e:
            logger.error(f"Ошибка при генерации изображения через DALL-E: {e}")
            # Возвращаем заглушку
            return self._create_placeholder_image()
    
    def generate_with_controlnet(
        self, 
        prompt: str, 
        control_image: Image.Image, 
        control_type: str = "canny"
    ) -> Image.Image:
        """Fallback генерация (ControlNet не поддерживается в DALL-E, используем обычную генерацию)"""
        
        logger.warning("ControlNet не поддерживается в DALL-E, используем обычную генерацию")
        
        # Поскольку DALL-E не поддерживает ControlNet, просто генерируем обычное изображение
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
    
    def _create_placeholder_image(self, size: Tuple[int, int] = (1024, 1024)) -> Image.Image:
        """Создание изображения-заглушки при ошибке"""
        image = Image.new('RGB', size, color='lightgray')
        draw = ImageDraw.Draw(image)
        
        # Добавляем текст
        text = "DALL-E generation\nfailed"
        try:
            bbox = draw.textbbox((0, 0), text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (size[0] - text_width) // 2
            y = (size[1] - text_height) // 2
            
            draw.text((x, y), text, fill='black', anchor='mm')
        except:
            # Fallback если textbbox не поддерживается
            draw.text((size[0]//2, size[1]//2), text, fill='black', anchor='mm')
        
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