import os
import asyncio
from typing import List, Dict, Optional, Any
from loguru import logger
import openai
from openai import AsyncOpenAI
import anthropic
from anthropic import AsyncAnthropic
import json
import re

from src.core.models import Scene, Choice, ScenarioInput, GenerationConfig
from src.modules.story_planner import PlannedScene, StoryGraph
from src.modules.knowledge_base import KnowledgeBase, GenreKnowledgeManager


class PromptBuilder:
    """Построитель промптов для LLM"""
    
    @staticmethod
    def build_scene_prompt(
        planned_scene: PlannedScene,
        scenario: ScenarioInput,
        rag_context: str,
        genre_elements: Dict[str, Any],
        previous_scene_text: Optional[str] = None
    ) -> str:
        """Построение промпта для генерации сцены"""
        
        prompt = f"""Ты - мастер интерактивных историй. Создай детализированную сцену для квеста.

КОНТЕКСТ КВЕСТА:
- Жанр: {scenario.genre}
- Главный герой: {scenario.hero}
- Цель: {scenario.goal}

ТЕКУЩАЯ СЦЕНА:
- Этап: {planned_scene.stage_name}
- Описание этапа: {planned_scene.description}
- ID сцены: {planned_scene.scene_id}

ЖАНРОВЫЕ ЭЛЕМЕНТЫ:
- Типичные локации: {', '.join(genre_elements.get('locations', [])[:3])}
- Атмосферные слова: {', '.join(genre_elements.get('atmosphere_words', [])[:4])}
- Возможные предметы: {', '.join(genre_elements.get('items', [])[:3])}

ДОПОЛНИТЕЛЬНЫЙ КОНТЕКСТ:
{rag_context}

"""
        
        if previous_scene_text:
            prompt += f"""ПРЕДЫДУЩАЯ СЦЕНА:
{previous_scene_text[:500]}...

"""
        
        prompt += f"""ВАРИАНТЫ ДЕЙСТВИЙ:
Сцена должна предложить следующие варианты выбора:
"""
        
        for i, (choice_text, next_id) in enumerate(planned_scene.choices):
            prompt += f"{i+1}. {choice_text} (ведет к сцене {next_id})\n"
        
        prompt += """
ТРЕБОВАНИЯ:
1. Опиши сцену ярко и атмосферно, используя жанровые особенности
2. Включи описание окружения, ощущений героя, важные детали
3. Если уместно, добавь короткий диалог или внутренний монолог
4. Сделай варианты выбора интересными и значимыми
5. Текст сцены должен быть 150-300 слов
6. Варианты выбора должны быть краткими (5-15 слов каждый)

Ответь в формате JSON:
{
    "text": "Детальное описание сцены...",
    "choices": [
        {"text": "Текст первого выбора", "next_scene": "scene_id_1"},
        {"text": "Текст второго выбора", "next_scene": "scene_id_2"}
    ],
    "mood": "атмосфера сцены (напряженная/таинственная/action/etc)",
    "location": "конкретное место действия"
}"""
        
        return prompt
    
    @staticmethod
    def build_refinement_prompt(scene: Scene, issue: str) -> str:
        """Промпт для доработки сцены"""
        return f"""Необходимо доработать сцену квеста.

ТЕКУЩАЯ СЦЕНА:
{json.dumps(scene.dict(), ensure_ascii=False, indent=2)}

ПРОБЛЕМА:
{issue}

Исправь указанную проблему, сохранив общую структуру и стиль сцены.
Ответь в том же JSON формате."""


class LLMInterface:
    """Интерфейс для работы с языковыми моделями"""
    
    def __init__(self, config: GenerationConfig):
        self.config = config
        self.model = config.model
        
        # Инициализация клиентов
        if "gpt" in self.model.lower():
            self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.provider = "openai"
        elif "claude" in self.model.lower():
            self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.provider = "anthropic"
        else:
            raise ValueError(f"Неподдерживаемая модель: {self.model}")
    
    async def generate(self, prompt: str) -> Dict[str, Any]:
        """Генерация ответа от LLM"""
        try:
            if self.provider == "openai":
                return await self._generate_openai(prompt)
            elif self.provider == "anthropic":
                return await self._generate_anthropic(prompt)
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
            raise
    
    async def _generate_openai(self, prompt: str) -> Dict[str, Any]:
        """Генерация через OpenAI API"""
        # Подготавливаем параметры
        params = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Ты создаешь интерактивные квесты. Отвечай только валидным JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "top_p": self.config.top_p
        }
        
        # response_format поддерживается только некоторыми моделями
        if "gpt-4" in self.model and "mini" not in self.model:
            params["response_format"] = {"type": "json_object"}
        
        response = await self.client.chat.completions.create(**params)
        
        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        # Пытаемся распарсить JSON
        try:
            parsed_content = json.loads(content)
        except json.JSONDecodeError:
            # Пробуем извлечь JSON из текста
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    parsed_content = json.loads(json_match.group())
                except:
                    logger.error(f"Не удалось распарсить JSON из ответа: {content[:200]}...")
                    raise ValueError("Невалидный JSON в ответе")
            else:
                logger.error(f"JSON не найден в ответе: {content[:200]}...")
                raise ValueError("JSON не найден в ответе")
        
        return {
            "content": parsed_content,
            "tokens_used": tokens_used
        }
    
    async def _generate_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Генерация через Anthropic API"""
        response = await self.client.messages.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt + "\n\nОтветь только валидным JSON."}
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            top_p=self.config.top_p
        )
        
        content = response.content[0].text
        
        # Извлечение JSON из ответа
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        
        return {
            "content": json.loads(content),
            "tokens_used": response.usage.input_tokens + response.usage.output_tokens
        }


class SceneGenerator:
    """Генератор детализированных сцен квеста"""
    
    def __init__(self, knowledge_base: KnowledgeBase, config: GenerationConfig):
        self.kb = knowledge_base
        self.config = config
        self.llm = LLMInterface(config)
        self.genre_manager = GenreKnowledgeManager(knowledge_base)
        self.generated_scenes: Dict[str, Scene] = {}
        self.total_tokens = 0
    
    async def generate_all_scenes(
        self, 
        story_graph: StoryGraph, 
        scenario: ScenarioInput
    ) -> Dict[str, Scene]:
        """Генерация всех сцен квеста"""
        logger.info("Начинаем генерацию сцен")
        
        # Получаем жанровые элементы
        genre_elements = self.genre_manager.get_genre_elements(scenario.genre)
        
        # Определяем порядок генерации (по уровням глубины)
        scenes_by_depth = self._group_scenes_by_depth(story_graph)
        
        # Генерируем сцены последовательно по уровням
        for depth_level in sorted(scenes_by_depth.keys()):
            scenes_at_level = scenes_by_depth[depth_level]
            
            # Генерируем сцены параллельно на одном уровне
            tasks = []
            for planned_scene in scenes_at_level:
                task = self._generate_single_scene(
                    planned_scene, scenario, genre_elements, story_graph
                )
                tasks.append(task)
            
            generated = await asyncio.gather(*tasks)
            
            # Сохраняем сгенерированные сцены
            for scene in generated:
                if scene:
                    self.generated_scenes[scene.scene_id] = scene
        
        logger.info(f"Сгенерировано {len(self.generated_scenes)} сцен, "
                   f"использовано токенов: {self.total_tokens}")
        
        return self.generated_scenes
    
    def _group_scenes_by_depth(self, story_graph: StoryGraph) -> Dict[int, List[PlannedScene]]:
        """Группировка сцен по уровням глубины"""
        scenes_by_depth = {}
        
        for scene in story_graph.scenes.values():
            depth = scene.depth_level
            if depth not in scenes_by_depth:
                scenes_by_depth[depth] = []
            scenes_by_depth[depth].append(scene)
        
        return scenes_by_depth
    
    async def _generate_single_scene(
        self,
        planned_scene: PlannedScene,
        scenario: ScenarioInput,
        genre_elements: Dict[str, Any],
        story_graph: StoryGraph
    ) -> Optional[Scene]:
        """Генерация одной сцены"""
        try:
            # Получаем RAG контекст
            rag_context = ""
            if self.config.use_rag:
                contexts = self.kb.retrieve_genre_context(
                    scenario.genre,
                    f"{planned_scene.stage_name} {planned_scene.description}",
                    top_k=self.config.rag_top_k
                )
                rag_context = "\n".join([ctx['content'] for ctx in contexts[:3]])
            
            # Находим предыдущую сцену
            previous_scene_text = self._get_previous_scene_text(
                planned_scene.scene_id, story_graph
            )
            
            # Строим промпт
            prompt = PromptBuilder.build_scene_prompt(
                planned_scene,
                scenario,
                rag_context,
                genre_elements,
                previous_scene_text
            )
            
            # Генерируем
            result = await self.llm.generate(prompt)
            scene_data = result['content']
            self.total_tokens += result['tokens_used']
            
            # Преобразуем в модель Scene
            scene = self._parse_scene_response(scene_data, planned_scene)
            
            # Валидируем и при необходимости дорабатываем
            scene = await self._validate_and_refine_scene(scene, planned_scene)
            
            return scene
            
        except Exception as e:
            logger.error(f"Ошибка генерации сцены {planned_scene.scene_id}: {e}")
            # Возвращаем базовую сцену в случае ошибки
            return self._create_fallback_scene(planned_scene)
    
    def _get_previous_scene_text(
        self, 
        current_scene_id: str, 
        story_graph: StoryGraph
    ) -> Optional[str]:
        """Получение текста предыдущей сцены"""
        # Находим сцены, которые ведут к текущей
        for scene_id, edges in story_graph.edges.items():
            if current_scene_id in edges:
                if scene_id in self.generated_scenes:
                    return self.generated_scenes[scene_id].text
        return None
    
    def _parse_scene_response(
        self, 
        response_data: Dict[str, Any], 
        planned_scene: PlannedScene
    ) -> Scene:
        """Преобразование ответа LLM в модель Scene"""
        # Обрабатываем choices
        choices = []
        for i, (_, next_scene_id) in enumerate(planned_scene.choices):
            if i < len(response_data.get('choices', [])):
                choice_data = response_data['choices'][i]
                # Проверяем, является ли choice_data словарем
                if isinstance(choice_data, dict):
                    choice_text = choice_data.get('text', 'Продолжить')
                elif isinstance(choice_data, str):
                    choice_text = choice_data
                else:
                    choice_text = 'Продолжить'
                
                choices.append(Choice(
                    text=choice_text,
                    next_scene=next_scene_id  # Используем ID из плана
                ))
            else:
                # Fallback если LLM не сгенерировала достаточно выборов
                choices.append(Choice(
                    text=f"Вариант {i+1}",
                    next_scene=next_scene_id
                ))
        
        return Scene(
            scene_id=planned_scene.scene_id,
            text=response_data.get('text', ''),
            choices=choices,
            mood=response_data.get('mood'),
            location=response_data.get('location')
        )
    
    async def _validate_and_refine_scene(
        self, 
        scene: Scene, 
        planned_scene: PlannedScene
    ) -> Scene:
        """Валидация и доработка сцены при необходимости"""
        issues = []
        
        # Проверка длины текста
        if len(scene.text) < 100:
            issues.append("Текст сцены слишком короткий (менее 100 символов)")
        elif len(scene.text) > 2000:
            issues.append("Текст сцены слишком длинный (более 2000 символов)")
        
        # Проверка количества выборов
        if len(scene.choices) != len(planned_scene.choices):
            issues.append(
                f"Неверное количество выборов: {len(scene.choices)} вместо {len(planned_scene.choices)}"
            )
        
        # Если есть проблемы, пытаемся доработать
        if issues and self.config.model != "gpt-3.5-turbo":  # Не дорабатываем для базовых моделей
            issue_text = "; ".join(issues)
            prompt = PromptBuilder.build_refinement_prompt(scene, issue_text)
            
            try:
                result = await self.llm.generate(prompt)
                refined_data = result['content']
                self.total_tokens += result['tokens_used']
                
                return self._parse_scene_response(refined_data, planned_scene)
            except Exception as e:
                logger.warning(f"Не удалось доработать сцену: {e}")
        
        return scene
    
    def _create_fallback_scene(self, planned_scene: PlannedScene) -> Scene:
        """Создание запасной сцены в случае ошибки генерации"""
        choices = [
            Choice(text=choice_text, next_scene=next_id)
            for choice_text, next_id in planned_scene.choices
        ]
        
        return Scene(
            scene_id=planned_scene.scene_id,
            text=f"{planned_scene.description}. [Сцена сгенерирована в упрощенном режиме]",
            choices=choices if choices else [Choice(text="Продолжить", next_scene="end")]
        )