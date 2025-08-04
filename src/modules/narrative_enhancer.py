"""
Модуль улучшения нарративной генерации на основе подходов GENEVA
(GENerative Evaluation Via Adversarial networks) и других современных методов
для создания более качественных и связных игровых повествований
"""

import asyncio
import random
import re
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import numpy as np
from loguru import logger
import openai
from openai import AsyncOpenAI
import anthropic
from anthropic import AsyncAnthropic
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import spacy

from src.core.models import Scene, Choice, Quest, ScenarioInput, GenerationConfig
from src.modules.knowledge_base import KnowledgeBase


class NarrativeQualityMetric(Enum):
    """Метрики качества нарратива"""
    COHERENCE = "coherence"           # Связность
    ENGAGEMENT = "engagement"         # Вовлеченность
    ORIGINALITY = "originality"       # Оригинальность
    EMOTIONAL_IMPACT = "emotional_impact"  # Эмоциональное воздействие
    CHARACTER_CONSISTENCY = "character_consistency"  # Последовательность персонажей
    PACING = "pacing"                # Темп повествования
    TENSION = "tension"              # Напряжение
    IMMERSION = "immersion"          # Погружение


@dataclass
class NarrativeAnalysis:
    """Результат анализа нарратива"""
    coherence_score: float
    engagement_score: float
    originality_score: float
    emotional_impact_score: float
    character_consistency_score: float
    pacing_score: float
    tension_curve: List[float]
    overall_quality: float
    suggestions: List[str]
    problematic_scenes: List[str]


@dataclass
class EnhancementConfig:
    """Конфигурация для улучшения нарратива"""
    target_quality_threshold: float = 0.75
    max_iterations: int = 3
    focus_metrics: List[NarrativeQualityMetric] = None
    enhance_character_development: bool = True
    enhance_emotional_arcs: bool = True
    enhance_plot_structure: bool = True
    use_adversarial_feedback: bool = True
    creative_temperature: float = 0.8


class NarrativeAnalyzer:
    """Анализатор качества нарратива"""
    
    def __init__(self):
        # Загружаем модели для анализа
        self.sentence_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        # Модель для анализа эмоций
        try:
            self.emotion_analyzer = pipeline(
                "text-classification",
                model="j-hartmann/emotion-english-distilroberta-base",
                device=0 if torch.cuda.is_available() else -1
            )
        except:
            self.emotion_analyzer = None
            logger.warning("Не удалось загрузить модель анализа эмоций")
        
        # Загружаем spaCy для лингвистического анализа
        try:
            self.nlp = spacy.load("ru_core_news_sm")
        except:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except:
                self.nlp = None
                logger.warning("Не удалось загрузить spaCy модель")
        
        # Кеш для вычислений
        self.embeddings_cache = {}
    
    def analyze_quest_narrative(self, quest: Quest) -> NarrativeAnalysis:
        """Комплексный анализ нарратива квеста"""
        logger.info(f"Анализируем нарратив квеста: {quest.title}")
        
        # Извлекаем тексты сцен
        scene_texts = [scene.text for scene in quest.scenes]
        
        # Вычисляем метрики
        coherence_score = self._analyze_coherence(scene_texts, quest.scenes)
        engagement_score = self._analyze_engagement(scene_texts, quest.scenes)
        originality_score = self._analyze_originality(scene_texts)
        emotional_impact_score = self._analyze_emotional_impact(scene_texts)
        character_consistency_score = self._analyze_character_consistency(scene_texts)
        pacing_score = self._analyze_pacing(quest.scenes)
        tension_curve = self._analyze_tension_curve(scene_texts)
        
        # Общая оценка качества
        overall_quality = np.mean([
            coherence_score, engagement_score, originality_score,
            emotional_impact_score, character_consistency_score, pacing_score
        ])
        
        # Генерируем предложения по улучшению
        suggestions = self._generate_improvement_suggestions(
            coherence_score, engagement_score, originality_score,
            emotional_impact_score, character_consistency_score, pacing_score
        )
        
        # Находим проблемные сцены
        problematic_scenes = self._identify_problematic_scenes(quest.scenes, tension_curve)
        
        return NarrativeAnalysis(
            coherence_score=coherence_score,
            engagement_score=engagement_score,
            originality_score=originality_score,
            emotional_impact_score=emotional_impact_score,
            character_consistency_score=character_consistency_score,
            pacing_score=pacing_score,
            tension_curve=tension_curve,
            overall_quality=overall_quality,
            suggestions=suggestions,
            problematic_scenes=problematic_scenes
        )
    
    def _analyze_coherence(self, scene_texts: List[str], scenes: List[Scene]) -> float:
        """Анализ связности нарратива"""
        if len(scene_texts) < 2:
            return 1.0
        
        # Вычисляем семантическую близость соседних сцен
        embeddings = self._get_text_embeddings(scene_texts)
        coherence_scores = []
        
        for i in range(len(embeddings) - 1):
            similarity = cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0]
            coherence_scores.append(similarity)
        
        # Проверяем логические связи через выборы
        choice_coherence = self._analyze_choice_coherence(scenes)
        
        # Комбинируем семантическую и структурную связность
        semantic_coherence = np.mean(coherence_scores)
        overall_coherence = (semantic_coherence + choice_coherence) / 2
        
        return max(0.0, min(1.0, overall_coherence))
    
    def _analyze_choice_coherence(self, scenes: List[Scene]) -> float:
        """Анализ связности через выборы игрока"""
        scene_dict = {scene.scene_id: scene for scene in scenes}
        coherent_transitions = 0
        total_transitions = 0
        
        for scene in scenes:
            for choice in scene.choices:
                if choice.next_scene in scene_dict:
                    total_transitions += 1
                    # Простая проверка: есть ли семантическая связь между выбором и следующей сценой
                    next_scene = scene_dict[choice.next_scene]
                    if self._choice_scene_coherent(choice.text, next_scene.text):
                        coherent_transitions += 1
        
        return coherent_transitions / max(total_transitions, 1)
    
    def _choice_scene_coherent(self, choice_text: str, scene_text: str) -> bool:
        """Проверка связности между выбором и сценой"""
        # Упрощенная проверка на основе ключевых слов
        choice_words = set(choice_text.lower().split())
        scene_words = set(scene_text.lower().split()[:50])  # Первые 50 слов сцены
        
        # Если есть общие ключевые слова (исключая служебные)
        stop_words = {'и', 'в', 'на', 'с', 'по', 'для', 'от', 'к', 'из', 'о', 'при', 'до'}
        meaningful_overlap = (choice_words - stop_words) & (scene_words - stop_words)
        
        return len(meaningful_overlap) > 0
    
    def _analyze_engagement(self, scene_texts: List[str], scenes: List[Scene]) -> float:
        """Анализ вовлеченности"""
        engagement_factors = []
        
        # Анализируем разнообразие выборов
        choice_diversity = self._analyze_choice_diversity(scenes)
        engagement_factors.append(choice_diversity)
        
        # Анализируем длину и сложность текстов
        text_complexity = self._analyze_text_complexity(scene_texts)
        engagement_factors.append(text_complexity)
        
        # Анализируем использование диалогов и действий
        interaction_score = self._analyze_interaction_elements(scene_texts)
        engagement_factors.append(interaction_score)
        
        return np.mean(engagement_factors)
    
    def _analyze_choice_diversity(self, scenes: List[Scene]) -> float:
        """Анализ разнообразия выборов"""
        if not scenes:
            return 0.0
        
        # Считаем среднее количество выборов и их разнообразие
        choice_counts = [len(scene.choices) for scene in scenes]
        avg_choices = np.mean(choice_counts)
        choice_variance = np.var(choice_counts)
        
        # Анализируем семантическое разнообразие выборов
        all_choices = []
        for scene in scenes:
            all_choices.extend([choice.text for choice in scene.choices])
        
        if len(all_choices) < 2:
            return 0.5
        
        choice_embeddings = self._get_text_embeddings(all_choices)
        similarity_matrix = cosine_similarity(choice_embeddings)
        
        # Считаем среднюю непохожесть выборов
        diversity_score = 1.0 - np.mean(similarity_matrix[np.triu_indices_from(similarity_matrix, k=1)])
        
        # Комбинируем факторы
        quantity_score = min(avg_choices / 3.0, 1.0)  # Оптимально 3 выбора
        variance_score = min(choice_variance / 2.0, 1.0)
        
        return np.mean([quantity_score, variance_score, diversity_score])
    
    def _analyze_text_complexity(self, scene_texts: List[str]) -> float:
        """Анализ сложности и качества текстов"""
        if not scene_texts:
            return 0.0
        
        complexity_scores = []
        
        for text in scene_texts:
            # Длина текста (оптимально 100-300 слов)
            word_count = len(text.split())
            length_score = self._sigmoid_score(word_count, optimal=200, width=100)
            
            # Разнообразие словаря
            unique_words = len(set(text.lower().split()))
            vocabulary_score = min(unique_words / max(word_count, 1), 1.0)
            
            # Сложность предложений
            sentence_count = len(text.split('.'))
            avg_sentence_length = word_count / max(sentence_count, 1)
            sentence_score = self._sigmoid_score(avg_sentence_length, optimal=15, width=10)
            
            complexity_scores.append(np.mean([length_score, vocabulary_score, sentence_score]))
        
        return np.mean(complexity_scores)
    
    def _analyze_interaction_elements(self, scene_texts: List[str]) -> float:
        """Анализ интерактивных элементов"""
        interaction_score = 0.0
        total_texts = len(scene_texts)
        
        if total_texts == 0:
            return 0.0
        
        for text in scene_texts:
            text_lower = text.lower()
            score = 0.0
            
            # Диалоги
            if '"' in text or '«' in text or '—' in text:
                score += 0.3
            
            # Действия героя
            action_words = ['ты', 'вы', 'идешь', 'смотришь', 'берешь', 'говоришь']
            if any(word in text_lower for word in action_words):
                score += 0.3
            
            # Сенсорные описания
            sensory_words = ['видишь', 'слышишь', 'чувствуешь', 'запах', 'звук', 'свет']
            if any(word in text_lower for word in sensory_words):
                score += 0.2
            
            # Эмоциональные слова
            emotion_words = ['страх', 'радость', 'гнев', 'удивление', 'напряжение']
            if any(word in text_lower for word in emotion_words):
                score += 0.2
            
            interaction_score += min(score, 1.0)
        
        return interaction_score / total_texts
    
    def _analyze_originality(self, scene_texts: List[str]) -> float:
        """Анализ оригинальности содержания"""
        if not scene_texts:
            return 0.5
        
        # Анализ на основе разнообразия использованных концепций
        all_text = ' '.join(scene_texts)
        
        # Подсчет уникальных понятий и образов
        originality_factors = []
        
        # Разнообразие прилагательных и описаний
        if self.nlp:
            doc = self.nlp(all_text[:10000])  # Ограничиваем для производительности
            adjectives = [token.lemma_ for token in doc if token.pos_ == 'ADJ']
            adj_diversity = len(set(adjectives)) / max(len(adjectives), 1)
            originality_factors.append(adj_diversity)
            
            # Разнообразие существительных
            nouns = [token.lemma_ for token in doc if token.pos_ == 'NOUN']
            noun_diversity = len(set(nouns)) / max(len(nouns), 1)
            originality_factors.append(noun_diversity)
        
        # Простая проверка на клише
        cliches = [
            'темная ночь', 'яркий свет', 'тяжелая дверь', 'длинный коридор',
            'загадочный незнакомец', 'древний артефакт'
        ]
        
        cliche_count = sum(1 for cliche in cliches if cliche in all_text.lower())
        cliche_penalty = min(cliche_count * 0.1, 0.3)
        
        base_originality = np.mean(originality_factors) if originality_factors else 0.5
        return max(0.0, base_originality - cliche_penalty)
    
    def _analyze_emotional_impact(self, scene_texts: List[str]) -> float:
        """Анализ эмоционального воздействия"""
        if not scene_texts or not self.emotion_analyzer:
            return 0.5
        
        emotion_scores = []
        
        for text in scene_texts:
            try:
                # Анализируем эмоции в тексте
                emotions = self.emotion_analyzer(text[:512])  # Ограничиваем длину
                
                # Ищем сильные эмоции
                strong_emotions = ['anger', 'fear', 'joy', 'surprise']
                max_emotion_score = max(
                    [emotion['score'] for emotion in emotions 
                     if emotion['label'].lower() in strong_emotions],
                    default=0.0
                )
                
                emotion_scores.append(max_emotion_score)
                
            except Exception as e:
                logger.warning(f"Ошибка анализа эмоций: {e}")
                emotion_scores.append(0.3)  # Нейтральная оценка
        
        return np.mean(emotion_scores)
    
    def _analyze_character_consistency(self, scene_texts: List[str]) -> float:
        """Анализ последовательности персонажей"""
        # Упрощенный анализ на основе упоминаний персонажей
        all_text = ' '.join(scene_texts).lower()
        
        # Ищем упоминания персонажей
        character_patterns = [
            r'\b(герой|героиня|протагонист|ты|вы)\b',
            r'\b(враг|противник|антагонист)\b',
            r'\b(союзник|друг|помощник)\b'
        ]
        
        character_mentions = {}
        for i, pattern in enumerate(character_patterns):
            matches = re.findall(pattern, all_text)
            character_mentions[f'character_{i}'] = len(matches)
        
        # Если персонажи упоминаются равномерно по тексту - это хорошо
        total_mentions = sum(character_mentions.values())
        if total_mentions == 0:
            return 0.5
        
        # Проверяем распределение упоминаний по сценам
        consistency_scores = []
        for text in scene_texts:
            text_lower = text.lower()
            scene_mentions = sum(len(re.findall(pattern, text_lower)) 
                               for pattern in character_patterns)
            scene_ratio = scene_mentions / len(text.split()) if text.split() else 0
            consistency_scores.append(scene_ratio)
        
        # Хорошая последовательность = равномерное распределение
        if len(consistency_scores) > 1:
            consistency = 1.0 - np.std(consistency_scores) / (np.mean(consistency_scores) + 1e-6)
        else:
            consistency = 0.5
        
        return max(0.0, min(1.0, consistency))
    
    def _analyze_pacing(self, scenes: List[Scene]) -> float:
        """Анализ темпа повествования"""
        if len(scenes) < 2:
            return 0.5
        
        pacing_factors = []
        
        # Анализируем длину сцен
        scene_lengths = [len(scene.text.split()) for scene in scenes]
        length_variance = np.var(scene_lengths) / (np.mean(scene_lengths) + 1e-6)
        length_diversity = min(length_variance / 100, 1.0)  # Нормализуем
        pacing_factors.append(length_diversity)
        
        # Анализируем количество выборов (показатель интенсивности)
        choice_counts = [len(scene.choices) for scene in scenes]
        choice_variance = np.var(choice_counts) / (np.mean(choice_counts) + 1e-6)
        choice_diversity = min(choice_variance, 1.0)
        pacing_factors.append(choice_diversity)
        
        # Идеальный темп имеет некоторую вариативность
        return np.mean(pacing_factors)
    
    def _analyze_tension_curve(self, scene_texts: List[str]) -> List[float]:
        """Анализ кривой напряжения"""
        tension_scores = []
        
        # Ключевые слова для определения напряжения
        high_tension_words = [
            'опасность', 'угроза', 'страх', 'бежать', 'атака', 'взрыв',
            'кричать', 'паника', 'ужас', 'смерть', 'кровь', 'боль'
        ]
        
        medium_tension_words = [
            'подозрение', 'тайна', 'загадка', 'странный', 'неожиданный',
            'внимание', 'осторожно', 'тихо', 'скрытый'
        ]
        
        for text in scene_texts:
            text_lower = text.lower()
            
            high_count = sum(1 for word in high_tension_words if word in text_lower)
            medium_count = sum(1 for word in medium_tension_words if word in text_lower)
            
            # Подсчитываем восклицательные знаки и вопросы
            exclamations = text.count('!') + text.count('?')
            
            # Формула напряжения
            tension = (high_count * 0.8 + medium_count * 0.4 + exclamations * 0.1)
            tension = min(tension / 5.0, 1.0)  # Нормализуем
            
            tension_scores.append(tension)
        
        return tension_scores
    
    def _generate_improvement_suggestions(
        self, coherence: float, engagement: float, originality: float,
        emotional_impact: float, character_consistency: float, pacing: float
    ) -> List[str]:
        """Генерация предложений по улучшению"""
        suggestions = []
        
        if coherence < 0.6:
            suggestions.append("Улучшить связность между сценами, добавить переходные элементы")
        
        if engagement < 0.6:
            suggestions.append("Добавить больше интерактивных элементов и разнообразных выборов")
        
        if originality < 0.5:
            suggestions.append("Избегать клише, добавить уникальные детали и описания")
        
        if emotional_impact < 0.5:
            suggestions.append("Усилить эмоциональную составляющую сцен")
        
        if character_consistency < 0.6:
            suggestions.append("Обеспечить более последовательное развитие персонажей")
        
        if pacing < 0.5:
            suggestions.append("Улучшить темп повествования, варьировать длину сцен")
        
        return suggestions
    
    def _identify_problematic_scenes(self, scenes: List[Scene], tension_curve: List[float]) -> List[str]:
        """Определение проблемных сцен"""
        problematic = []
        
        for i, scene in enumerate(scenes):
            issues = []
            
            # Слишком короткая сцена
            if len(scene.text.split()) < 50:
                issues.append("слишком короткая")
            
            # Слишком длинная сцена
            if len(scene.text.split()) > 400:
                issues.append("слишком длинная")
            
            # Мало выборов
            if len(scene.choices) < 1:
                issues.append("недостаточно выборов")
            
            # Низкое напряжение
            if i < len(tension_curve) and tension_curve[i] < 0.1:
                issues.append("низкое напряжение")
            
            if issues:
                problematic.append(f"{scene.scene_id}: {', '.join(issues)}")
        
        return problematic
    
    def _get_text_embeddings(self, texts: List[str]) -> np.ndarray:
        """Получение векторных представлений текстов с кешированием"""
        embeddings = []
        
        for text in texts:
            text_hash = hash(text)
            if text_hash in self.embeddings_cache:
                embeddings.append(self.embeddings_cache[text_hash])
            else:
                embedding = self.sentence_model.encode(text)
                self.embeddings_cache[text_hash] = embedding
                embeddings.append(embedding)
        
        return np.array(embeddings)
    
    def _sigmoid_score(self, value: float, optimal: float, width: float) -> float:
        """Сигмоидальная функция оценки"""
        return 1.0 / (1.0 + np.exp(abs(value - optimal) / width))


class AdversarialNarrativeCritic:
    """Критик нарратива на основе adversarial подхода"""
    
    def __init__(self, config: GenerationConfig):
        self.config = config
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async def critique_narrative(self, quest: Quest, analysis: NarrativeAnalysis) -> Dict[str, Any]:
        """Критический анализ нарратива"""
        
        # Создаем промпт для критика
        critique_prompt = self._build_critic_prompt(quest, analysis)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": "Ты - строгий критик интерактивных повествований. Твоя задача - найти недостатки и предложить конкретные улучшения."},
                    {"role": "user", "content": critique_prompt}
                ],
                temperature=0.3,  # Низкая температура для более критичного анализа
                max_tokens=1000
            )
            
            critique_text = response.choices[0].message.content
            return self._parse_critique_response(critique_text)
            
        except Exception as e:
            logger.error(f"Ошибка в adversarial критике: {e}")
            return {"error": str(e)}
    
    def _build_critic_prompt(self, quest: Quest, analysis: NarrativeAnalysis) -> str:
        """Построение промпта для критика"""
        
        # Берем первые 3 сцены для анализа
        sample_scenes = quest.scenes[:3]
        scenes_text = "\n\n".join([
            f"Сцена {scene.scene_id}:\n{scene.text}\nВыборы: {[choice.text for choice in scene.choices]}"
            for scene in sample_scenes
        ])
        
        prompt = f"""Проанализируй качество этого интерактивного квеста:

НАЗВАНИЕ: {quest.title}
ЖАНР: {quest.genre}
ЦЕЛЬ: {quest.goal}

ОБРАЗЦЫ СЦЕН:
{scenes_text}

ТЕКУЩИЕ МЕТРИКИ КАЧЕСТВА:
- Связность: {analysis.coherence_score:.2f}
- Вовлеченность: {analysis.engagement_score:.2f}
- Оригинальность: {analysis.originality_score:.2f}
- Эмоциональное воздействие: {analysis.emotional_impact_score:.2f}
- Последовательность персонажей: {analysis.character_consistency_score:.2f}
- Темп: {analysis.pacing_score:.2f}

НАЙДИ КОНКРЕТНЫЕ НЕДОСТАТКИ:
1. Проблемы с логикой и связностью
2. Слабые или неинтересные выборы
3. Клише и банальности
4. Проблемы с персонажами
5. Недостатки стиля и языка

ПРЕДЛОЖИ КОНКРЕТНЫЕ УЛУЧШЕНИЯ для каждой проблемы.
"""
        return prompt
    
    def _parse_critique_response(self, critique_text: str) -> Dict[str, Any]:
        """Парсинг ответа критика"""
        return {
            "critique": critique_text,
            "structured_feedback": self._extract_structured_feedback(critique_text)
        }
    
    def _extract_structured_feedback(self, text: str) -> Dict[str, List[str]]:
        """Извлечение структурированной обратной связи"""
        feedback = {
            "problems": [],
            "improvements": [],
            "strengths": []
        }
        
        lines = text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if any(word in line.lower() for word in ['проблем', 'недостат', 'слаб']):
                current_section = "problems"
            elif any(word in line.lower() for word in ['улучш', 'предлаг', 'рекоменд']):
                current_section = "improvements"
            elif any(word in line.lower() for word in ['сильн', 'хорош', 'удачн']):
                current_section = "strengths"
            
            if current_section and line.startswith(('•', '-', '1.', '2.', '3.')):
                feedback[current_section].append(line)
        
        return feedback


class NarrativeEnhancer:
    """Основной класс для улучшения нарративов"""
    
    def __init__(self, config: Optional[EnhancementConfig] = None):
        self.config = config or EnhancementConfig()
        self.analyzer = NarrativeAnalyzer()
        self.critic = None  # Инициализируется при необходимости
        
        # LLM клиенты
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    async def enhance_quest_narrative(
        self, 
        quest: Quest, 
        scenario: ScenarioInput,
        generation_config: GenerationConfig
    ) -> Tuple[Quest, NarrativeAnalysis]:
        """Улучшение нарратива квеста"""
        
        logger.info(f"Начинаем улучшение нарратива квеста: {quest.title}")
        
        current_quest = quest
        best_analysis = None
        
        for iteration in range(self.config.max_iterations):
            logger.info(f"Итерация улучшения {iteration + 1}/{self.config.max_iterations}")
            
            # Анализируем текущее состояние
            analysis = self.analyzer.analyze_quest_narrative(current_quest)
            
            logger.info(f"Общее качество: {analysis.overall_quality:.2f}")
            
            # Если качество достаточно высокое, завершаем
            if analysis.overall_quality >= self.config.target_quality_threshold:
                logger.info("Достигнут целевой уровень качества")
                return current_quest, analysis
            
            # Если это не первая итерация, сравниваем с предыдущим результатом
            if best_analysis and analysis.overall_quality <= best_analysis.overall_quality:
                logger.info("Качество не улучшается, останавливаем")
                break
            
            best_analysis = analysis
            
            # Получаем критику от adversarial критика
            if self.config.use_adversarial_feedback:
                if not self.critic:
                    self.critic = AdversarialNarrativeCritic(generation_config)
                
                critique = await self.critic.critique_narrative(current_quest, analysis)
            else:
                critique = None
            
            # Улучшаем квест
            improved_quest = await self._improve_quest(
                current_quest, analysis, critique, scenario, generation_config
            )
            
            current_quest = improved_quest
        
        final_analysis = self.analyzer.analyze_quest_narrative(current_quest)
        logger.info(f"Финальное качество: {final_analysis.overall_quality:.2f}")
        
        return current_quest, final_analysis
    
    async def _improve_quest(
        self,
        quest: Quest,
        analysis: NarrativeAnalysis,
        critique: Optional[Dict[str, Any]],
        scenario: ScenarioInput,
        generation_config: GenerationConfig
    ) -> Quest:
        """Улучшение квеста на основе анализа"""
        
        # Определяем приоритетные сцены для улучшения
        scenes_to_improve = self._select_scenes_for_improvement(quest, analysis)
        
        improved_scenes = []
        
        for scene in quest.scenes:
            if scene.scene_id in scenes_to_improve:
                # Улучшаем сцену
                improved_scene = await self._improve_scene(
                    scene, quest, analysis, critique, scenario, generation_config
                )
                improved_scenes.append(improved_scene)
            else:
                # Оставляем сцену без изменений
                improved_scenes.append(scene)
        
        # Создаем улучшенную версию квеста
        improved_quest = Quest(
            title=quest.title,
            genre=quest.genre,
            hero=quest.hero,
            goal=quest.goal,
            scenes=improved_scenes,
            start_scene=quest.start_scene,
            paths=quest.paths,
            metadata=quest.metadata
        )
        
        return improved_quest
    
    def _select_scenes_for_improvement(
        self, 
        quest: Quest, 
        analysis: NarrativeAnalysis
    ) -> List[str]:
        """Выбор сцен для улучшения"""
        
        scenes_to_improve = []
        
        # Добавляем проблемные сцены
        for problem_desc in analysis.problematic_scenes:
            scene_id = problem_desc.split(':')[0]
            scenes_to_improve.append(scene_id)
        
        # Добавляем сцены с низким напряжением
        for i, tension in enumerate(analysis.tension_curve):
            if tension < 0.2 and i < len(quest.scenes):
                scenes_to_improve.append(quest.scenes[i].scene_id)
        
        # Ограничиваем количество сцен для улучшения
        return list(set(scenes_to_improve))[:3]
    
    async def _improve_scene(
        self,
        scene: Scene,
        quest: Quest,
        analysis: NarrativeAnalysis,
        critique: Optional[Dict[str, Any]],
        scenario: ScenarioInput,
        generation_config: GenerationConfig
    ) -> Scene:
        """Улучшение отдельной сцены"""
        
        improvement_prompt = self._build_scene_improvement_prompt(
            scene, quest, analysis, critique, scenario
        )
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=generation_config.model,
                messages=[
                    {"role": "system", "content": "Ты - мастер интерактивных повествований. Улучши данную сцену, сохранив её структуру и связи."},
                    {"role": "user", "content": improvement_prompt}
                ],
                temperature=self.config.creative_temperature,
                max_tokens=1500
            )
            
            improved_content = response.choices[0].message.content
            return self._parse_improved_scene(improved_content, scene)
            
        except Exception as e:
            logger.error(f"Ошибка улучшения сцены {scene.scene_id}: {e}")
            return scene  # Возвращаем оригинальную сцену при ошибке
    
    def _build_scene_improvement_prompt(
        self,
        scene: Scene,
        quest: Quest,
        analysis: NarrativeAnalysis,
        critique: Optional[Dict[str, Any]],
        scenario: ScenarioInput
    ) -> str:
        """Построение промпта для улучшения сцены"""
        
        prompt = f"""Улучши эту сцену интерактивного квеста:

КОНТЕКСТ КВЕСТА:
- Название: {quest.title}
- Жанр: {scenario.genre}
- Герой: {scenario.hero}
- Цель: {scenario.goal}

ТЕКУЩАЯ СЦЕНА ({scene.scene_id}):
{scene.text}

ВЫБОРЫ:
{chr(10).join([f"- {choice.text} → {choice.next_scene}" for choice in scene.choices])}

ПРОБЛЕМЫ КАЧЕСТВА:
- Общее качество: {analysis.overall_quality:.2f}
- Связность: {analysis.coherence_score:.2f}
- Вовлеченность: {analysis.engagement_score:.2f}
- Оригинальность: {analysis.originality_score:.2f}
"""
        
        if critique and "structured_feedback" in critique:
            feedback = critique["structured_feedback"]
            if feedback.get("problems"):
                prompt += f"\nВЫЯВЛЕННЫЕ ПРОБЛЕМЫ:\n"
                prompt += "\n".join(feedback["problems"][:3])
        
        prompt += f"""

ТРЕБОВАНИЯ К УЛУЧШЕНИЮ:
1. Сохрани структуру выборов и их связи
2. Улучши описательность и атмосферность
3. Добавь больше сенсорных деталей
4. Усиль эмоциональное воздействие
5. Избегай клише и банальностей
6. Сделай язык более живым и интересным

Ответь в формате JSON:
{{
    "improved_text": "Улучшенный текст сцены...",
    "improved_choices": [
        {{"text": "Улучшенный текст выбора 1", "next_scene": "{scene.choices[0].next_scene if scene.choices else 'scene_end'}"}},
        ...
    ],
    "mood": "настроение сцены",
    "improvements_made": ["список внесенных улучшений"]
}}
"""
        
        return prompt
    
    def _parse_improved_scene(self, improved_content: str, original_scene: Scene) -> Scene:
        """Парсинг улучшенной сцены"""
        
        try:
            # Пытаемся распарсить JSON
            import json
            improved_data = json.loads(improved_content)
            
            # Создаем улучшенные выборы
            improved_choices = []
            for i, choice_data in enumerate(improved_data.get("improved_choices", [])):
                if i < len(original_scene.choices):
                    # Сохраняем оригинальную связь
                    original_choice = original_scene.choices[i]
                    improved_choice = Choice(
                        text=choice_data.get("text", original_choice.text),
                        next_scene=choice_data.get("next_scene", original_choice.next_scene),
                        condition=original_choice.condition,
                        effect=original_choice.effect
                    )
                    improved_choices.append(improved_choice)
            
            # Если не удалось получить улучшенные выборы, используем оригинальные
            if not improved_choices:
                improved_choices = original_scene.choices
            
            # Создаем улучшенную сцену
            improved_scene = Scene(
                scene_id=original_scene.scene_id,
                text=improved_data.get("improved_text", original_scene.text),
                choices=improved_choices,
                image_prompt=original_scene.image_prompt,
                mood=improved_data.get("mood", original_scene.mood),
                location=original_scene.location
            )
            
            return improved_scene
            
        except Exception as e:
            logger.warning(f"Не удалось распарсить улучшенную сцену: {e}")
            return original_scene
    
    def export_analysis_report(self, analysis: NarrativeAnalysis, output_path: str):
        """Экспорт отчета об анализе"""
        
        report = {
            "quality_metrics": {
                "coherence": analysis.coherence_score,
                "engagement": analysis.engagement_score,
                "originality": analysis.originality_score,
                "emotional_impact": analysis.emotional_impact_score,
                "character_consistency": analysis.character_consistency_score,
                "pacing": analysis.pacing_score,
                "overall_quality": analysis.overall_quality
            },
            "tension_curve": analysis.tension_curve,
            "suggestions": analysis.suggestions,
            "problematic_scenes": analysis.problematic_scenes
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Отчет об анализе сохранен: {output_path}")