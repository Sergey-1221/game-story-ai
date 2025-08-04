"""
Модуль оценки качества генерации игрового контента
с использованием различных метрик для квестов, уровней и объектов
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json
from pathlib import Path
from loguru import logger
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score
import pandas as pd
from collections import Counter
import networkx as nx
import re

from src.core.models import Quest, Scene, Choice
from src.modules.level_generator import GeneratedLevel, TileType
from src.modules.object_placement import GameObject


class QualityDimension(Enum):
    """Измерения качества"""
    COHERENCE = "coherence"           # Связность
    DIVERSITY = "diversity"           # Разнообразие
    COMPLEXITY = "complexity"         # Сложность
    BALANCE = "balance"              # Баланс
    ORIGINALITY = "originality"       # Оригинальность
    PLAYABILITY = "playability"       # Играбельность
    ENGAGEMENT = "engagement"         # Вовлеченность
    TECHNICAL_QUALITY = "technical"   # Техническое качество


@dataclass
class QualityScore:
    """Оценка качества"""
    dimension: QualityDimension
    score: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    details: Dict[str, Any]
    suggestions: List[str]


@dataclass
class QualityReport:
    """Отчет о качестве"""
    overall_score: float
    dimension_scores: Dict[QualityDimension, QualityScore]
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any]


class QuestQualityEvaluator:
    """Оценщик качества квестов"""
    
    def __init__(self):
        self.sentence_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.tfidf_vectorizer = TfidfVectorizer(max_features=1000, stop_words=None)
    
    def evaluate_quest(self, quest: Quest) -> QualityReport:
        """Комплексная оценка качества квеста"""
        
        logger.info(f"Оцениваем качество квеста: {quest.title}")
        
        dimension_scores = {}
        
        # Оцениваем по каждому измерению
        dimension_scores[QualityDimension.COHERENCE] = self._evaluate_coherence(quest)
        dimension_scores[QualityDimension.DIVERSITY] = self._evaluate_diversity(quest)
        dimension_scores[QualityDimension.COMPLEXITY] = self._evaluate_complexity(quest)
        dimension_scores[QualityDimension.BALANCE] = self._evaluate_balance(quest)
        dimension_scores[QualityDimension.ORIGINALITY] = self._evaluate_originality(quest)
        dimension_scores[QualityDimension.PLAYABILITY] = self._evaluate_playability(quest)
        dimension_scores[QualityDimension.ENGAGEMENT] = self._evaluate_engagement(quest)
        dimension_scores[QualityDimension.TECHNICAL_QUALITY] = self._evaluate_technical_quality(quest)
        
        # Вычисляем общую оценку
        overall_score = np.mean([score.score for score in dimension_scores.values()])
        
        # Анализируем сильные и слабые стороны
        strengths, weaknesses = self._analyze_strengths_weaknesses(dimension_scores)
        
        # Генерируем рекомендации
        recommendations = self._generate_recommendations(dimension_scores)
        
        return QualityReport(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            metadata={
                "quest_title": quest.title,
                "scene_count": len(quest.scenes),
                "total_choices": sum(len(scene.choices) for scene in quest.scenes),
                "evaluation_timestamp": pd.Timestamp.now().isoformat()
            }
        )
    
    def _evaluate_coherence(self, quest: Quest) -> QualityScore:
        """Оценка связности квеста"""
        
        scene_texts = [scene.text for scene in quest.scenes]
        
        # Семантическая связность
        semantic_coherence = self._calculate_semantic_coherence(scene_texts)
        
        # Структурная связность (граф сцен)
        structural_coherence = self._calculate_structural_coherence(quest)
        
        # Тематическая связность
        thematic_coherence = self._calculate_thematic_coherence(scene_texts)
        
        # Общая оценка связности
        overall_coherence = np.mean([semantic_coherence, structural_coherence, thematic_coherence])
        
        details = {
            "semantic_coherence": semantic_coherence,
            "structural_coherence": structural_coherence,
            "thematic_coherence": thematic_coherence,
            "scene_connectivity": self._analyze_scene_connectivity(quest)
        }
        
        suggestions = []
        if semantic_coherence < 0.6:
            suggestions.append("Улучшить семантическую связь между сценами")
        if structural_coherence < 0.6:
            suggestions.append("Оптимизировать структуру переходов между сценами")
        if thematic_coherence < 0.6:
            suggestions.append("Усилить тематическое единство квеста")
        
        return QualityScore(
            dimension=QualityDimension.COHERENCE,
            score=overall_coherence,
            confidence=0.8,
            details=details,
            suggestions=suggestions
        )
    
    def _calculate_semantic_coherence(self, scene_texts: List[str]) -> float:
        """Вычисление семантической связности"""
        if len(scene_texts) < 2:
            return 1.0
        
        embeddings = self.sentence_model.encode(scene_texts)
        
        # Вычисляем косинусное сходство между соседними сценами
        coherence_scores = []
        for i in range(len(embeddings) - 1):
            similarity = cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0]
            coherence_scores.append(similarity)
        
        return np.mean(coherence_scores)
    
    def _calculate_structural_coherence(self, quest: Quest) -> float:
        """Вычисление структурной связности"""
        
        # Создаем граф переходов между сценами
        G = nx.DiGraph()
        
        # Добавляем узлы (сцены)
        for scene in quest.scenes:
            G.add_node(scene.scene_id)
        
        # Добавляем рёбра (переходы)
        for scene in quest.scenes:
            for choice in scene.choices:
                if choice.next_scene and choice.next_scene != scene.scene_id:
                    G.add_edge(scene.scene_id, choice.next_scene)
        
        # Анализируем связность графа
        if len(G.nodes) == 0:
            return 0.0
        
        # Слабая связность (в направленном графе)
        weakly_connected = nx.is_weakly_connected(G)
        
        # Количество компонент связности
        num_components = nx.number_weakly_connected_components(G)
        
        # Средняя степень узлов
        degrees = [G.degree(node) for node in G.nodes()]
        avg_degree = np.mean(degrees) if degrees else 0
        
        # Нормализуем показатели
        connectivity_score = 1.0 if weakly_connected else 0.5
        component_score = 1.0 / num_components
        degree_score = min(avg_degree / 3.0, 1.0)  # Оптимально ~3 связи на сцену
        
        return np.mean([connectivity_score, component_score, degree_score])
    
    def _calculate_thematic_coherence(self, scene_texts: List[str]) -> float:
        """Вычисление тематической связности"""
        
        if len(scene_texts) < 2:
            return 1.0
        
        # Анализируем TF-IDF векторы
        try:
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(scene_texts)
            
            # Вычисляем среднее косинусное сходство
            similarities = cosine_similarity(tfidf_matrix)
            
            # Исключаем диагональ (сходство с самим собой)
            mask = np.ones(similarities.shape, dtype=bool)
            np.fill_diagonal(mask, False)
            
            avg_similarity = np.mean(similarities[mask])
            return avg_similarity
            
        except Exception as e:
            logger.warning(f"Ошибка при вычислении тематической связности: {e}")
            return 0.5
    
    def _analyze_scene_connectivity(self, quest: Quest) -> Dict[str, Any]:
        """Анализ связности сцен"""
        
        connectivity_info = {
            "total_scenes": len(quest.scenes),
            "scenes_with_choices": sum(1 for scene in quest.scenes if scene.choices),
            "total_transitions": sum(len(scene.choices) for scene in quest.scenes),
            "dead_ends": [],
            "unreachable_scenes": []
        }
        
        # Поиск тупиковых сцен
        for scene in quest.scenes:
            if not scene.choices:
                connectivity_info["dead_ends"].append(scene.scene_id)
        
        # Поиск недостижимых сцен
        reachable_scenes = {quest.start_scene}
        to_visit = [quest.start_scene]
        
        scene_dict = {scene.scene_id: scene for scene in quest.scenes}
        
        while to_visit:
            current_scene_id = to_visit.pop(0)
            if current_scene_id in scene_dict:
                current_scene = scene_dict[current_scene_id]
                for choice in current_scene.choices:
                    if choice.next_scene and choice.next_scene not in reachable_scenes:
                        reachable_scenes.add(choice.next_scene)
                        to_visit.append(choice.next_scene)
        
        all_scene_ids = {scene.scene_id for scene in quest.scenes}
        unreachable = all_scene_ids - reachable_scenes
        connectivity_info["unreachable_scenes"] = list(unreachable)
        
        return connectivity_info
    
    def _evaluate_diversity(self, quest: Quest) -> QualityScore:
        """Оценка разнообразия квеста"""
        
        # Разнообразие выборов
        choice_diversity = self._calculate_choice_diversity(quest)
        
        # Разнообразие сцен
        scene_diversity = self._calculate_scene_diversity(quest)
        
        # Лексическое разнообразие
        lexical_diversity = self._calculate_lexical_diversity(quest)
        
        overall_diversity = np.mean([choice_diversity, scene_diversity, lexical_diversity])
        
        details = {
            "choice_diversity": choice_diversity,
            "scene_diversity": scene_diversity,
            "lexical_diversity": lexical_diversity,
            "unique_choice_count": len(set(choice.text for scene in quest.scenes for choice in scene.choices)),
            "avg_choices_per_scene": np.mean([len(scene.choices) for scene in quest.scenes])
        }
        
        suggestions = []
        if choice_diversity < 0.6:
            suggestions.append("Увеличить разнообразие вариантов выбора")
        if scene_diversity < 0.6:
            suggestions.append("Добавить больше разнообразия в сцены")
        if lexical_diversity < 0.6:
            suggestions.append("Расширить словарный запас в описаниях")
        
        return QualityScore(
            dimension=QualityDimension.DIVERSITY,
            score=overall_diversity,
            confidence=0.7,
            details=details,
            suggestions=suggestions
        )
    
    def _calculate_choice_diversity(self, quest: Quest) -> float:
        """Вычисление разнообразия выборов"""
        
        all_choices = [choice.text for scene in quest.scenes for choice in scene.choices]
        
        if not all_choices:
            return 0.0
        
        # Анализируем уникальность выборов
        unique_choices = len(set(all_choices))
        total_choices = len(all_choices)
        uniqueness_ratio = unique_choices / total_choices
        
        # Анализируем семантическое разнообразие
        if len(all_choices) > 1:
            choice_embeddings = self.sentence_model.encode(all_choices)
            
            # Средняя дистанция между выборами
            similarities = cosine_similarity(choice_embeddings)
            mask = np.ones(similarities.shape, dtype=bool)
            np.fill_diagonal(mask, False)
            
            avg_similarity = np.mean(similarities[mask])
            semantic_diversity = 1.0 - avg_similarity
        else:
            semantic_diversity = 0.0
        
        return np.mean([uniqueness_ratio, semantic_diversity])
    
    def _calculate_scene_diversity(self, quest: Quest) -> float:
        """Вычисление разнообразия сцен"""
        
        scene_texts = [scene.text for scene in quest.scenes]
        
        if len(scene_texts) < 2:
            return 1.0
        
        # Длина сцен
        scene_lengths = [len(text.split()) for text in scene_texts]
        length_variance = np.var(scene_lengths) / (np.mean(scene_lengths) + 1e-6)
        length_diversity = min(length_variance / 100, 1.0)  # Нормализуем
        
        # Настроения сцен
        moods = [scene.mood for scene in quest.scenes if scene.mood]
        mood_diversity = len(set(moods)) / max(len(moods), 1) if moods else 0.5
        
        # Локации сцен
        locations = [scene.location for scene in quest.scenes if scene.location]
        location_diversity = len(set(locations)) / max(len(locations), 1) if locations else 0.5
        
        return np.mean([length_diversity, mood_diversity, location_diversity])
    
    def _calculate_lexical_diversity(self, quest: Quest) -> float:
        """Вычисление лексического разнообразия"""
        
        all_text = ' '.join([scene.text for scene in quest.scenes])
        words = all_text.lower().split()
        
        if not words:
            return 0.0
        
        # Коэффициент лексического разнообразия (TTR - Type-Token Ratio)
        unique_words = len(set(words))
        total_words = len(words)
        ttr = unique_words / total_words
        
        # Нормализуем по длине текста (чтобы длинные тексты не штрафовались)
        normalized_ttr = ttr * (total_words / (total_words + 100))
        
        return min(normalized_ttr * 2, 1.0)  # Масштабируем
    
    def _evaluate_complexity(self, quest: Quest) -> QualityScore:
        """Оценка сложности квеста"""
        
        # Структурная сложность
        structural_complexity = self._calculate_structural_complexity(quest)
        
        # Нарративная сложность
        narrative_complexity = self._calculate_narrative_complexity(quest)
        
        # Сложность выборов
        choice_complexity = self._calculate_choice_complexity(quest)
        
        overall_complexity = np.mean([structural_complexity, narrative_complexity, choice_complexity])
        
        details = {
            "structural_complexity": structural_complexity,
            "narrative_complexity": narrative_complexity,
            "choice_complexity": choice_complexity,
            "branching_factor": self._calculate_branching_factor(quest),
            "max_path_length": self._calculate_max_path_length(quest)
        }
        
        suggestions = []
        if overall_complexity < 0.3:
            suggestions.append("Увеличить сложность квеста добавлением ветвлений")
        elif overall_complexity > 0.8:
            suggestions.append("Упростить структуру квеста для лучшей понятности")
        
        return QualityScore(
            dimension=QualityDimension.COMPLEXITY,
            score=overall_complexity,
            confidence=0.75,
            details=details,
            suggestions=suggestions
        )
    
    def _calculate_structural_complexity(self, quest: Quest) -> float:
        """Вычисление структурной сложности"""
        
        # Количество сцен
        scene_count = len(quest.scenes)
        scene_complexity = min(scene_count / 10.0, 1.0)  # Нормализуем к 10 сценам
        
        # Среднее количество выборов
        avg_choices = np.mean([len(scene.choices) for scene in quest.scenes]) if quest.scenes else 0
        choice_complexity = min(avg_choices / 4.0, 1.0)  # Нормализуем к 4 выборам
        
        # Глубина ветвления
        branching_factor = self._calculate_branching_factor(quest)
        branching_complexity = min(branching_factor / 3.0, 1.0)
        
        return np.mean([scene_complexity, choice_complexity, branching_complexity])
    
    def _calculate_narrative_complexity(self, quest: Quest) -> float:
        """Вычисление нарративной сложности"""
        
        all_text = ' '.join([scene.text for scene in quest.scenes])
        
        # Длина текста
        word_count = len(all_text.split())
        length_complexity = min(word_count / 2000.0, 1.0)  # Нормализуем к 2000 слов
        
        # Сложность предложений
        sentences = all_text.split('.')
        avg_sentence_length = np.mean([len(s.split()) for s in sentences if s.strip()]) if sentences else 0
        sentence_complexity = min(avg_sentence_length / 20.0, 1.0)  # Нормализуем к 20 словам
        
        # Словарное разнообразие
        words = all_text.lower().split()
        vocabulary_size = len(set(words))
        vocab_complexity = min(vocabulary_size / 500.0, 1.0)  # Нормализуем к 500 уникальных слов
        
        return np.mean([length_complexity, sentence_complexity, vocab_complexity])
    
    def _calculate_choice_complexity(self, quest: Quest) -> float:
        """Вычисление сложности выборов"""
        
        all_choices = [choice.text for scene in quest.scenes for choice in scene.choices]
        
        if not all_choices:
            return 0.0
        
        # Средняя длина выборов
        avg_choice_length = np.mean([len(choice.split()) for choice in all_choices])
        length_complexity = min(avg_choice_length / 10.0, 1.0)
        
        # Наличие условий и эффектов
        conditional_choices = sum(1 for scene in quest.scenes for choice in scene.choices 
                                if choice.condition or choice.effect)
        conditional_ratio = conditional_choices / len(all_choices)
        
        return np.mean([length_complexity, conditional_ratio])
    
    def _calculate_branching_factor(self, quest: Quest) -> float:
        """Вычисление коэффициента ветвления"""
        
        total_choices = sum(len(scene.choices) for scene in quest.scenes)
        non_terminal_scenes = sum(1 for scene in quest.scenes if scene.choices)
        
        if non_terminal_scenes == 0:
            return 0.0
        
        return total_choices / non_terminal_scenes
    
    def _calculate_max_path_length(self, quest: Quest) -> int:
        """Вычисление максимальной длины пути"""
        
        # Создаем граф переходов
        G = nx.DiGraph()
        scene_dict = {scene.scene_id: scene for scene in quest.scenes}
        
        for scene in quest.scenes:
            G.add_node(scene.scene_id)
            for choice in scene.choices:
                if choice.next_scene and choice.next_scene in scene_dict:
                    G.add_edge(scene.scene_id, choice.next_scene)
        
        # Ищем самый длинный путь от стартовой сцены
        if quest.start_scene not in G:
            return 0
        
        try:
            # Находим все достижимые узлы
            reachable = nx.descendants(G, quest.start_scene)
            reachable.add(quest.start_scene)
            
            # Вычисляем кратчайшие пути ко всем достижимым узлам
            paths = nx.single_source_shortest_path_length(G, quest.start_scene)
            
            return max(paths.values()) if paths else 0
            
        except Exception:
            return len(quest.scenes)  # Fallback
    
    def _evaluate_balance(self, quest: Quest) -> QualityScore:
        """Оценка баланса квеста"""
        
        # Баланс длины сцен
        scene_balance = self._calculate_scene_length_balance(quest)
        
        # Баланс выборов
        choice_balance = self._calculate_choice_balance(quest)
        
        # Баланс сложности по ходу квеста
        progression_balance = self._calculate_progression_balance(quest)
        
        overall_balance = np.mean([scene_balance, choice_balance, progression_balance])
        
        details = {
            "scene_balance": scene_balance,
            "choice_balance": choice_balance,
            "progression_balance": progression_balance,
            "scene_length_variance": np.var([len(scene.text.split()) for scene in quest.scenes]),
            "choice_count_variance": np.var([len(scene.choices) for scene in quest.scenes])
        }
        
        suggestions = []
        if scene_balance < 0.6:
            suggestions.append("Выровнять длину сцен для лучшего баланса")
        if choice_balance < 0.6:
            suggestions.append("Сбалансировать количество выборов в сценах")
        
        return QualityScore(
            dimension=QualityDimension.BALANCE,
            score=overall_balance,
            confidence=0.7,
            details=details,
            suggestions=suggestions
        )
    
    def _calculate_scene_length_balance(self, quest: Quest) -> float:
        """Вычисление баланса длины сцен"""
        
        scene_lengths = [len(scene.text.split()) for scene in quest.scenes]
        
        if not scene_lengths:
            return 1.0
        
        # Коэффициент вариации (нормализованное стандартное отклонение)
        mean_length = np.mean(scene_lengths)
        std_length = np.std(scene_lengths)
        
        if mean_length == 0:
            return 1.0
        
        cv = std_length / mean_length
        
        # Преобразуем в оценку баланса (меньше вариации = лучше баланс)
        balance_score = max(0.0, 1.0 - cv)
        
        return balance_score
    
    def _calculate_choice_balance(self, quest: Quest) -> float:
        """Вычисление баланса выборов"""
        
        choice_counts = [len(scene.choices) for scene in quest.scenes]
        
        if not choice_counts:
            return 1.0
        
        # Аналогично балансу длины сцен
        mean_choices = np.mean(choice_counts)
        std_choices = np.std(choice_counts)
        
        if mean_choices == 0:
            return 1.0
        
        cv = std_choices / mean_choices
        balance_score = max(0.0, 1.0 - cv)
        
        return balance_score
    
    def _calculate_progression_balance(self, quest: Quest) -> float:
        """Вычисление баланса прогрессии сложности"""
        
        # Простая эвристика: сложность должна нарастать к концу
        scene_complexities = []
        
        for i, scene in enumerate(quest.scenes):
            # Оцениваем сложность сцены по различным факторам
            text_complexity = len(scene.text.split()) / 200.0  # Нормализуем
            choice_complexity = len(scene.choices) / 4.0  # Нормализуем
            position_weight = (i + 1) / len(quest.scenes)  # Позиция в квесте
            
            scene_complexity = np.mean([text_complexity, choice_complexity]) * position_weight
            scene_complexities.append(scene_complexity)
        
        # Проверяем, есть ли тенденция к росту сложности
        if len(scene_complexities) < 2:
            return 1.0
        
        # Вычисляем корреляцию между позицией и сложностью
        positions = list(range(len(scene_complexities)))
        correlation = np.corrcoef(positions, scene_complexities)[0, 1]
        
        # Преобразуем корреляцию в оценку (положительная корреляция хорошо)
        progression_score = max(0.0, (correlation + 1) / 2)
        
        return progression_score
    
    def _evaluate_originality(self, quest: Quest) -> QualityScore:
        """Оценка оригинальности квеста"""
        
        # Анализ клише и стереотипов
        cliche_score = self._analyze_cliches(quest)
        
        # Уникальность терминологии
        terminology_uniqueness = self._analyze_terminology_uniqueness(quest)
        
        # Новизна сюжетных поворотов
        plot_novelty = self._analyze_plot_novelty(quest)
        
        overall_originality = np.mean([cliche_score, terminology_uniqueness, plot_novelty])
        
        details = {
            "cliche_score": cliche_score,
            "terminology_uniqueness": terminology_uniqueness,
            "plot_novelty": plot_novelty,
            "detected_cliches": self._detect_common_cliches(quest)
        }
        
        suggestions = []
        if cliche_score < 0.6:
            suggestions.append("Избегать распространенных клише в описаниях")
        if terminology_uniqueness < 0.6:
            suggestions.append("Использовать более оригинальную терминологию")
        
        return QualityScore(
            dimension=QualityDimension.ORIGINALITY,
            score=overall_originality,
            confidence=0.6,  # Оригинальность сложно оценить объективно
            details=details,
            suggestions=suggestions
        )
    
    def _analyze_cliches(self, quest: Quest) -> float:
        """Анализ наличия клише"""
        
        common_cliches = [
            "темная ночь", "яркий свет", "таинственный незнакомец",
            "древний артефакт", "последняя надежда", "смертельная опасность",
            "скрытые силы", "судьба мира", "избранный", "темная сторона"
        ]
        
        all_text = ' '.join([scene.text for scene in quest.scenes]).lower()
        
        cliche_count = sum(1 for cliche in common_cliches if cliche in all_text)
        max_possible_cliches = len(common_cliches)
        
        # Инвертируем: меньше клише = выше оценка
        cliche_ratio = cliche_count / max_possible_cliches
        originality_score = 1.0 - cliche_ratio
        
        return max(0.0, originality_score)
    
    def _analyze_terminology_uniqueness(self, quest: Quest) -> float:
        """Анализ уникальности терминологии"""
        
        all_text = ' '.join([scene.text for scene in quest.scenes])
        words = all_text.lower().split()
        
        # Ищем редкие/необычные слова
        word_freq = Counter(words)
        
        # Считаем долю слов, встречающихся только один раз
        hapax_legomena = sum(1 for count in word_freq.values() if count == 1)
        total_unique_words = len(word_freq)
        
        if total_unique_words == 0:
            return 0.0
        
        uniqueness_ratio = hapax_legomena / total_unique_words
        
        return min(uniqueness_ratio * 2, 1.0)  # Масштабируем
    
    def _analyze_plot_novelty(self, quest: Quest) -> float:
        """Анализ новизны сюжетных поворотов"""
        
        # Простая эвристика: анализируем неожиданность переходов
        scene_dict = {scene.scene_id: scene for scene in quest.scenes}
        novelty_scores = []
        
        for scene in quest.scenes:
            for choice in scene.choices:
                if choice.next_scene and choice.next_scene in scene_dict:
                    next_scene = scene_dict[choice.next_scene]
                    
                    # Семантическая дистанция между текущей сценой и следующей
                    current_embedding = self.sentence_model.encode([scene.text])
                    next_embedding = self.sentence_model.encode([next_scene.text])
                    
                    similarity = cosine_similarity(current_embedding, next_embedding)[0][0]
                    novelty = 1.0 - similarity  # Больше различий = больше новизны
                    
                    novelty_scores.append(novelty)
        
        return np.mean(novelty_scores) if novelty_scores else 0.5
    
    def _detect_common_cliches(self, quest: Quest) -> List[str]:
        """Обнаружение конкретных клише"""
        
        cliches = [
            "темная ночь", "яркий свет", "таинственный незнакомец",
            "древний артефакт", "последняя надежда", "смертельная опасность"
        ]
        
        all_text = ' '.join([scene.text for scene in quest.scenes]).lower()
        detected = [cliche for cliche in cliches if cliche in all_text]
        
        return detected
    
    def _evaluate_playability(self, quest: Quest) -> QualityScore:
        """Оценка играбельности квеста"""
        
        # Техническая корректность
        technical_correctness = self._check_technical_correctness(quest)
        
        # Понятность для игрока
        clarity = self._evaluate_clarity(quest)
        
        # Сбалансированность выборов
        choice_balance = self._evaluate_choice_meaningfulness(quest)
        
        overall_playability = np.mean([technical_correctness, clarity, choice_balance])
        
        details = {
            "technical_correctness": technical_correctness,
            "clarity": clarity,
            "choice_balance": choice_balance,
            "broken_links": self._find_broken_links(quest),
            "unclear_choices": self._find_unclear_choices(quest)
        }
        
        suggestions = []
        if technical_correctness < 0.8:
            suggestions.append("Исправить технические проблемы с переходами")
        if clarity < 0.7:
            suggestions.append("Улучшить ясность описаний и инструкций")
        
        return QualityScore(
            dimension=QualityDimension.PLAYABILITY,
            score=overall_playability,
            confidence=0.85,
            details=details,
            suggestions=suggestions
        )
    
    def _check_technical_correctness(self, quest: Quest) -> float:
        """Проверка технической корректности"""
        
        issues = 0
        total_checks = 0
        
        scene_ids = {scene.scene_id for scene in quest.scenes}
        
        # Проверяем все переходы
        for scene in quest.scenes:
            for choice in scene.choices:
                total_checks += 1
                
                # Проверяем, существует ли целевая сцена
                if choice.next_scene and choice.next_scene not in scene_ids:
                    issues += 1
        
        # Проверяем, доступна ли стартовая сцена
        total_checks += 1
        if quest.start_scene not in scene_ids:
            issues += 1
        
        if total_checks == 0:
            return 1.0
        
        correctness_ratio = 1.0 - (issues / total_checks)
        return max(0.0, correctness_ratio)
    
    def _evaluate_clarity(self, quest: Quest) -> float:
        """Оценка ясности квеста"""
        
        clarity_scores = []
        
        # Анализируем каждую сцену
        for scene in quest.scenes:
            # Длина описания (не слишком короткое, не слишком длинное)
            word_count = len(scene.text.split())
            length_score = self._sigmoid_score(word_count, optimal=150, width=50)
            
            # Наличие ясных инструкций/описаний
            instruction_words = ['можешь', 'нужно', 'следует', 'выбери', 'реши']
            has_instructions = any(word in scene.text.lower() for word in instruction_words)
            instruction_score = 1.0 if has_instructions else 0.5
            
            # Ясность выборов
            choice_clarity = np.mean([len(choice.text.split()) for choice in scene.choices]) / 10.0
            choice_clarity = min(choice_clarity, 1.0)
            
            scene_clarity = np.mean([length_score, instruction_score, choice_clarity])
            clarity_scores.append(scene_clarity)
        
        return np.mean(clarity_scores) if clarity_scores else 0.0
    
    def _evaluate_choice_meaningfulness(self, quest: Quest) -> float:
        """Оценка значимости выборов"""
        
        meaningful_choices = 0
        total_choices = 0
        
        for scene in quest.scenes:
            for choice in scene.choices:
                total_choices += 1
                
                # Проверяем, есть ли различия в выборах
                choice_words = set(choice.text.lower().split())
                
                # Сравниваем с другими выборами в той же сцене
                is_meaningful = True
                for other_choice in scene.choices:
                    if choice != other_choice:
                        other_words = set(other_choice.text.lower().split())
                        # Если выборы слишком похожи, это плохо
                        overlap = len(choice_words & other_words) / len(choice_words | other_words)
                        if overlap > 0.8:
                            is_meaningful = False
                            break
                
                if is_meaningful:
                    meaningful_choices += 1
        
        if total_choices == 0:
            return 1.0
        
        return meaningful_choices / total_choices
    
    def _find_broken_links(self, quest: Quest) -> List[str]:
        """Поиск битых ссылок"""
        
        scene_ids = {scene.scene_id for scene in quest.scenes}
        broken_links = []
        
        for scene in quest.scenes:
            for choice in scene.choices:
                if choice.next_scene and choice.next_scene not in scene_ids:
                    broken_links.append(f"{scene.scene_id} -> {choice.next_scene}")
        
        return broken_links
    
    def _find_unclear_choices(self, quest: Quest) -> List[str]:
        """Поиск неясных выборов"""
        
        unclear_choices = []
        
        for scene in quest.scenes:
            for choice in scene.choices:
                # Слишком короткие выборы
                if len(choice.text.split()) < 2:
                    unclear_choices.append(f"{scene.scene_id}: '{choice.text}' (слишком короткий)")
                
                # Слишком длинные выборы
                elif len(choice.text.split()) > 15:
                    unclear_choices.append(f"{scene.scene_id}: '{choice.text[:50]}...' (слишком длинный)")
        
        return unclear_choices
    
    def _evaluate_engagement(self, quest: Quest) -> QualityScore:
        """Оценка вовлеченности квеста"""
        
        # Эмоциональное воздействие
        emotional_impact = self._calculate_emotional_impact(quest)
        
        # Интерактивность
        interactivity = self._calculate_interactivity(quest)
        
        # Темп повествования
        pacing = self._calculate_pacing(quest)
        
        overall_engagement = np.mean([emotional_impact, interactivity, pacing])
        
        details = {
            "emotional_impact": emotional_impact,
            "interactivity": interactivity,
            "pacing": pacing,
            "emotional_words_count": self._count_emotional_words(quest),
            "interactive_elements": self._count_interactive_elements(quest)
        }
        
        suggestions = []
        if emotional_impact < 0.6:
            suggestions.append("Усилить эмоциональное воздействие сцен")
        if interactivity < 0.6:
            suggestions.append("Добавить больше интерактивных элементов")
        
        return QualityScore(
            dimension=QualityDimension.ENGAGEMENT,
            score=overall_engagement,
            confidence=0.7,
            details=details,
            suggestions=suggestions
        )
    
    def _calculate_emotional_impact(self, quest: Quest) -> float:
        """Вычисление эмоционального воздействия"""
        
        emotional_words = [
            'страх', 'радость', 'гнев', 'удивление', 'печаль', 'восторг',
            'ужас', 'восхищение', 'тревога', 'волнение', 'напряжение'
        ]
        
        all_text = ' '.join([scene.text for scene in quest.scenes]).lower()
        
        emotional_word_count = sum(1 for word in emotional_words if word in all_text)
        text_length = len(all_text.split())
        
        if text_length == 0:
            return 0.0
        
        # Нормализуем по длине текста
        emotional_density = emotional_word_count / (text_length / 100)  # на 100 слов
        
        return min(emotional_density / 5.0, 1.0)  # Нормализуем к максимуму
    
    def _calculate_interactivity(self, quest: Quest) -> float:
        """Вычисление интерактивности"""
        
        interactive_elements = 0
        total_scenes = len(quest.scenes)
        
        for scene in quest.scenes:
            # Количество выборов
            choice_score = min(len(scene.choices) / 3.0, 1.0)
            
            # Наличие интерактивных слов
            interactive_words = ['выбери', 'реши', 'действуй', 'попробуй', 'используй']
            has_interactive = any(word in scene.text.lower() for word in interactive_words)
            interactive_score = 1.0 if has_interactive else 0.0
            
            scene_interactivity = (choice_score + interactive_score) / 2
            interactive_elements += scene_interactivity
        
        if total_scenes == 0:
            return 0.0
        
        return interactive_elements / total_scenes
    
    def _calculate_pacing(self, quest: Quest) -> float:
        """Вычисление темпа повествования"""
        
        scene_lengths = [len(scene.text.split()) for scene in quest.scenes]
        
        if len(scene_lengths) < 2:
            return 0.5
        
        # Вариативность длины сцен (хороший темп имеет вариации)
        length_variance = np.var(scene_lengths) / (np.mean(scene_lengths) + 1e-6)
        variance_score = min(length_variance / 100, 1.0)
        
        # Прогрессия напряжения
        tension_words = ['опасность', 'угроза', 'быстро', 'срочно', 'немедленно']
        tension_scores = []
        
        for scene in quest.scenes:
            tension_count = sum(1 for word in tension_words if word in scene.text.lower())
            tension_scores.append(tension_count)
        
        # Проверяем, нарастает ли напряжение
        if len(tension_scores) > 1:
            positions = list(range(len(tension_scores)))
            tension_correlation = np.corrcoef(positions, tension_scores)[0, 1]
            progression_score = max(0.0, (tension_correlation + 1) / 2)
        else:
            progression_score = 0.5
        
        return np.mean([variance_score, progression_score])
    
    def _count_emotional_words(self, quest: Quest) -> int:
        """Подсчет эмоциональных слов"""
        
        emotional_words = [
            'страх', 'радость', 'гнев', 'удивление', 'печаль', 'восторг',
            'ужас', 'восхищение', 'тревога', 'волнение', 'напряжение'
        ]
        
        all_text = ' '.join([scene.text for scene in quest.scenes]).lower()
        
        return sum(1 for word in emotional_words if word in all_text)
    
    def _count_interactive_elements(self, quest: Quest) -> int:
        """Подсчет интерактивных элементов"""
        
        interactive_elements = 0
        
        for scene in quest.scenes:
            # Выборы
            interactive_elements += len(scene.choices)
            
            # Интерактивные слова
            interactive_words = ['выбери', 'реши', 'действуй', 'попробуй', 'используй']
            interactive_elements += sum(1 for word in interactive_words if word in scene.text.lower())
        
        return interactive_elements
    
    def _evaluate_technical_quality(self, quest: Quest) -> QualityScore:
        """Оценка технического качества"""
        
        # Корректность структуры
        structure_quality = self._check_structure_quality(quest)
        
        # Качество метаданных
        metadata_quality = self._check_metadata_quality(quest)
        
        # Консистентность
        consistency = self._check_consistency(quest)
        
        overall_technical = np.mean([structure_quality, metadata_quality, consistency])
        
        details = {
            "structure_quality": structure_quality,
            "metadata_quality": metadata_quality,
            "consistency": consistency,
            "validation_errors": self._validate_quest_structure(quest)
        }
        
        suggestions = []
        if structure_quality < 0.8:
            suggestions.append("Исправить структурные проблемы квеста")
        if metadata_quality < 0.7:
            suggestions.append("Улучшить качество метаданных")
        
        return QualityScore(
            dimension=QualityDimension.TECHNICAL_QUALITY,
            score=overall_technical,
            confidence=0.9,
            details=details,
            suggestions=suggestions
        )
    
    def _check_structure_quality(self, quest: Quest) -> float:
        """Проверка качества структуры"""
        
        quality_score = 1.0
        
        # Проверяем обязательные поля
        if not quest.title or not quest.title.strip():
            quality_score -= 0.2
        
        if not quest.genre or not quest.genre.strip():
            quality_score -= 0.1
        
        if not quest.scenes:
            quality_score -= 0.5
        
        # Проверяем корректность ссылок
        scene_ids = {scene.scene_id for scene in quest.scenes}
        
        if quest.start_scene not in scene_ids:
            quality_score -= 0.3
        
        # Проверяем циклические ссылки и корректность переходов
        for scene in quest.scenes:
            for choice in scene.choices:
                if choice.next_scene and choice.next_scene not in scene_ids:
                    quality_score -= 0.1
        
        return max(0.0, quality_score)
    
    def _check_metadata_quality(self, quest: Quest) -> float:
        """Проверка качества метаданных"""
        
        quality_score = 0.0
        
        # Проверяем наличие базовых метаданных
        if quest.metadata:
            if 'generation_time' in quest.metadata:
                quality_score += 0.2
            if 'tokens_used' in quest.metadata:
                quality_score += 0.2
            if len(quest.metadata) >= 3:
                quality_score += 0.3
        
        # Проверяем качество описаний сцен
        scenes_with_mood = sum(1 for scene in quest.scenes if scene.mood)
        mood_ratio = scenes_with_mood / len(quest.scenes) if quest.scenes else 0
        quality_score += mood_ratio * 0.3
        
        return min(quality_score, 1.0)
    
    def _check_consistency(self, quest: Quest) -> float:
        """Проверка консистентности"""
        
        consistency_score = 1.0
        
        # Проверяем консистентность именования
        scene_id_pattern = re.compile(r'^scene_\d+$')
        inconsistent_ids = sum(1 for scene in quest.scenes 
                             if not scene_id_pattern.match(scene.scene_id))
        
        if inconsistent_ids > 0:
            consistency_score -= (inconsistent_ids / len(quest.scenes)) * 0.3
        
        # Проверяем консистентность жанра
        genre_keywords = {
            'киберпанк': ['кибер', 'нео', 'хакер', 'сеть', 'имплант'],
            'фэнтези': ['магия', 'эльф', 'дракон', 'заклинание', 'зелье'],
            'хоррор': ['ужас', 'страх', 'тьма', 'монстр', 'кровь']
        }
        
        if quest.genre.lower() in genre_keywords:
            expected_keywords = genre_keywords[quest.genre.lower()]
            all_text = ' '.join([scene.text for scene in quest.scenes]).lower()
            
            keyword_matches = sum(1 for keyword in expected_keywords if keyword in all_text)
            genre_consistency = keyword_matches / len(expected_keywords)
            
            if genre_consistency < 0.3:
                consistency_score -= 0.2
        
        return max(0.0, consistency_score)
    
    def _validate_quest_structure(self, quest: Quest) -> List[str]:
        """Валидация структуры квеста"""
        
        errors = []
        
        # Базовые проверки
        if not quest.title:
            errors.append("Отсутствует название квеста")
        
        if not quest.scenes:
            errors.append("Квест не содержит сцен")
            return errors
        
        scene_ids = {scene.scene_id for scene in quest.scenes}
        
        # Проверяем стартовую сцену
        if quest.start_scene not in scene_ids:
            errors.append(f"Стартовая сцена '{quest.start_scene}' не существует")
        
        # Проверяем переходы
        for scene in quest.scenes:
            if not scene.scene_id:
                errors.append("Обнаружена сцена без ID")
            
            for i, choice in enumerate(scene.choices):
                if not choice.text:
                    errors.append(f"Пустой текст выбора в сцене {scene.scene_id}")
                
                if choice.next_scene and choice.next_scene not in scene_ids:
                    errors.append(f"Битая ссылка: {scene.scene_id} -> {choice.next_scene}")
        
        return errors
    
    def _analyze_strengths_weaknesses(self, dimension_scores: Dict[QualityDimension, QualityScore]) -> Tuple[List[str], List[str]]:
        """Анализ сильных и слабых сторон"""
        
        strengths = []
        weaknesses = []
        
        for dimension, score in dimension_scores.items():
            if score.score >= 0.8:
                strengths.append(f"Высокое качество по измерению '{dimension.value}' ({score.score:.2f})")
            elif score.score <= 0.5:
                weaknesses.append(f"Низкое качество по измерению '{dimension.value}' ({score.score:.2f})")
        
        return strengths, weaknesses
    
    def _generate_recommendations(self, dimension_scores: Dict[QualityDimension, QualityScore]) -> List[str]:
        """Генерация рекомендаций по улучшению"""
        
        recommendations = []
        
        # Собираем все предложения из отдельных измерений
        for dimension, score in dimension_scores.items():
            recommendations.extend(score.suggestions)
        
        # Добавляем общие рекомендации
        overall_score = np.mean([score.score for score in dimension_scores.values()])
        
        if overall_score < 0.6:
            recommendations.append("Рассмотрите возможность регенерации квеста с другими параметрами")
        elif overall_score > 0.8:
            recommendations.append("Квест имеет высокое качество, можно использовать как есть")
        
        # Приоритизируем по важности
        priority_recommendations = []
        for dimension in [QualityDimension.TECHNICAL_QUALITY, QualityDimension.PLAYABILITY, 
                         QualityDimension.COHERENCE]:
            if dimension in dimension_scores and dimension_scores[dimension].score < 0.7:
                priority_recommendations.extend(dimension_scores[dimension].suggestions)
        
        return priority_recommendations + recommendations
    
    def _sigmoid_score(self, value: float, optimal: float, width: float) -> float:
        """Сигмоидальная функция оценки"""
        return 1.0 / (1.0 + np.exp(abs(value - optimal) / width))


class LevelQualityEvaluator:
    """Оценщик качества уровней"""
    
    def __init__(self):
        pass
    
    def evaluate_level(self, level: GeneratedLevel) -> QualityReport:
        """Оценка качества сгенерированного уровня"""
        
        logger.info(f"Оцениваем качество уровня {level.width}x{level.height}")
        
        dimension_scores = {}
        
        # Структурная целостность
        dimension_scores[QualityDimension.TECHNICAL_QUALITY] = self._evaluate_structural_integrity(level)
        
        # Баланс и играбельность
        dimension_scores[QualityDimension.BALANCE] = self._evaluate_level_balance(level)
        
        # Разнообразие и интересность
        dimension_scores[QualityDimension.DIVERSITY] = self._evaluate_level_diversity(level)
        
        # Сложность навигации
        dimension_scores[QualityDimension.COMPLEXITY] = self._evaluate_navigation_complexity(level)
        
        # Общая оценка
        overall_score = np.mean([score.score for score in dimension_scores.values()])
        
        return QualityReport(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            strengths=[],
            weaknesses=[],
            recommendations=[],
            metadata={
                "level_size": f"{level.width}x{level.height}",
                "tile_types": len(set(level.tiles.flatten())),
                "spawn_points": len(level.spawn_points),
                "goal_points": len(level.goal_points)
            }
        )
    
    def _evaluate_structural_integrity(self, level: GeneratedLevel) -> QualityScore:
        """Оценка структурной целостности уровня"""
        
        # Проверяем связность проходимых областей
        connectivity = self._check_level_connectivity(level)
        
        # Проверяем корректность границ
        boundary_quality = self._check_boundary_quality(level)
        
        # Проверяем размещение спавнов и целей
        spawn_goal_quality = self._check_spawn_goal_placement(level)
        
        integrity_score = np.mean([connectivity, boundary_quality, spawn_goal_quality])
        
        return QualityScore(
            dimension=QualityDimension.TECHNICAL_QUALITY,
            score=integrity_score,
            confidence=0.9,
            details={
                "connectivity": connectivity,
                "boundary_quality": boundary_quality,
                "spawn_goal_quality": spawn_goal_quality
            },
            suggestions=[]
        )
    
    def _check_level_connectivity(self, level: GeneratedLevel) -> float:
        """Проверка связности уровня"""
        
        # Найдем все проходимые тайлы
        walkable_tiles = [TileType.FLOOR.value, TileType.DOOR.value, 
                         TileType.SPAWN.value, TileType.GOAL.value]
        
        walkable_positions = []
        for y in range(level.height):
            for x in range(level.width):
                if level.tiles[y, x] in walkable_tiles:
                    walkable_positions.append((x, y))
        
        if not walkable_positions:
            return 0.0
        
        # Используем BFS для проверки связности
        visited = set()
        queue = [walkable_positions[0]]
        visited.add(walkable_positions[0])
        
        while queue:
            x, y = queue.pop(0)
            
            # Проверяем соседей
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = x + dx, y + dy
                
                if (0 <= nx < level.width and 0 <= ny < level.height and 
                    (nx, ny) not in visited and 
                    level.tiles[ny, nx] in walkable_tiles):
                    
                    visited.add((nx, ny))
                    queue.append((nx, ny))
        
        # Процент связанных проходимых тайлов
        connectivity_ratio = len(visited) / len(walkable_positions)
        
        return connectivity_ratio
    
    def _check_boundary_quality(self, level: GeneratedLevel) -> float:
        """Проверка качества границ уровня"""
        
        boundary_score = 1.0
        
        # Проверяем, что края уровня окружены стенами
        edges = [
            level.tiles[0, :],      # верхняя граница
            level.tiles[-1, :],     # нижняя граница
            level.tiles[:, 0],      # левая граница
            level.tiles[:, -1]      # правая граница
        ]
        
        for edge in edges:
            wall_ratio = np.sum(edge == TileType.WALL.value) / len(edge)
            if wall_ratio < 0.8:  # Ожидаем хотя бы 80% стен на границах
                boundary_score -= 0.2
        
        return max(0.0, boundary_score)
    
    def _check_spawn_goal_placement(self, level: GeneratedLevel) -> float:
        """Проверка размещения точек спавна и целей"""
        
        placement_score = 1.0
        
        # Проверяем, что есть хотя бы одна точка спавна и одна цель
        if not level.spawn_points:
            placement_score -= 0.5
        
        if not level.goal_points:
            placement_score -= 0.5
        
        # Проверяем, что точки находятся на проходимых тайлах
        walkable_tiles = [TileType.FLOOR.value, TileType.SPAWN.value, TileType.GOAL.value]
        
        for spawn in level.spawn_points:
            x, y = spawn
            if (0 <= x < level.width and 0 <= y < level.height and 
                level.tiles[y, x] not in walkable_tiles):
                placement_score -= 0.1
        
        for goal in level.goal_points:
            x, y = goal
            if (0 <= x < level.width and 0 <= y < level.height and 
                level.tiles[y, x] not in walkable_tiles):
                placement_score -= 0.1
        
        return max(0.0, placement_score)
    
    def _evaluate_level_balance(self, level: GeneratedLevel) -> QualityScore:
        """Оценка баланса уровня"""
        
        # Баланс типов тайлов
        tile_balance = self._calculate_tile_type_balance(level)
        
        # Баланс плотности препятствий
        density_balance = self._calculate_density_balance(level)
        
        # Баланс размещения особых областей
        special_area_balance = self._calculate_special_area_balance(level)
        
        overall_balance = np.mean([tile_balance, density_balance, special_area_balance])
        
        return QualityScore(
            dimension=QualityDimension.BALANCE,
            score=overall_balance,
            confidence=0.8,
            details={
                "tile_balance": tile_balance,
                "density_balance": density_balance,
                "special_area_balance": special_area_balance
            },
            suggestions=[]
        )
    
    def _calculate_tile_type_balance(self, level: GeneratedLevel) -> float:
        """Вычисление баланса типов тайлов"""
        
        tile_counts = Counter(level.tiles.flatten())
        total_tiles = level.width * level.height
        
        # Ожидаемые пропорции для разных типов тайлов
        expected_ratios = {
            TileType.FLOOR.value: 0.4,      # 40% пола
            TileType.WALL.value: 0.35,      # 35% стен
            TileType.DOOR.value: 0.05,      # 5% дверей
            TileType.WATER.value: 0.1,      # 10% воды
            TileType.OBSTACLE.value: 0.1    # 10% препятствий
        }
        
        balance_score = 0.0
        
        for tile_type, expected_ratio in expected_ratios.items():
            actual_count = tile_counts.get(tile_type, 0)
            actual_ratio = actual_count / total_tiles
            
            # Вычисляем отклонение от ожидаемого
            deviation = abs(actual_ratio - expected_ratio)
            type_score = max(0.0, 1.0 - deviation * 2)  # Штрафуем отклонения
            
            balance_score += type_score
        
        return balance_score / len(expected_ratios)
    
    def _calculate_density_balance(self, level: GeneratedLevel) -> float:
        """Вычисление баланса плотности"""
        
        # Разбиваем уровень на квадранты и анализируем плотность препятствий
        mid_x, mid_y = level.width // 2, level.height // 2
        
        quadrants = [
            level.tiles[0:mid_y, 0:mid_x],        # верхний левый
            level.tiles[0:mid_y, mid_x:],         # верхний правый
            level.tiles[mid_y:, 0:mid_x],         # нижний левый
            level.tiles[mid_y:, mid_x:]           # нижний правый
        ]
        
        densities = []
        obstacle_tiles = [TileType.WALL.value, TileType.OBSTACLE.value, TileType.WATER.value]
        
        for quadrant in quadrants:
            obstacle_count = np.sum(np.isin(quadrant, obstacle_tiles))
            total_count = quadrant.size
            density = obstacle_count / total_count if total_count > 0 else 0
            densities.append(density)
        
        # Хороший баланс = низкая вариация плотности между квадрантами
        density_variance = np.var(densities)
        balance_score = max(0.0, 1.0 - density_variance * 4)  # Нормализуем
        
        return balance_score
    
    def _calculate_special_area_balance(self, level: GeneratedLevel) -> float:
        """Вычисление баланса особых областей"""
        
        if not level.special_areas:
            return 0.5  # Нейтральная оценка при отсутствии особых областей
        
        total_special_tiles = sum(len(positions) for positions in level.special_areas.values())
        total_tiles = level.width * level.height
        
        special_ratio = total_special_tiles / total_tiles
        
        # Оптимальное соотношение особых областей: 5-15%
        if 0.05 <= special_ratio <= 0.15:
            return 1.0
        elif special_ratio < 0.05:
            return special_ratio / 0.05  # Линейное снижение
        else:
            return max(0.0, 1.0 - (special_ratio - 0.15) / 0.1)
    
    def _evaluate_level_diversity(self, level: GeneratedLevel) -> QualityScore:
        """Оценка разнообразия уровня"""
        
        # Разнообразие типов тайлов
        tile_diversity = self._calculate_tile_diversity(level)
        
        # Пространственное разнообразие
        spatial_diversity = self._calculate_spatial_diversity(level)
        
        # Разнообразие паттернов
        pattern_diversity = self._calculate_pattern_diversity(level)
        
        overall_diversity = np.mean([tile_diversity, spatial_diversity, pattern_diversity])
        
        return QualityScore(
            dimension=QualityDimension.DIVERSITY,
            score=overall_diversity,
            confidence=0.7,
            details={
                "tile_diversity": tile_diversity,
                "spatial_diversity": spatial_diversity,
                "pattern_diversity": pattern_diversity
            },
            suggestions=[]
        )
    
    def _calculate_tile_diversity(self, level: GeneratedLevel) -> float:
        """Вычисление разнообразия типов тайлов"""
        
        unique_tiles = len(set(level.tiles.flatten()))
        max_possible_tiles = len(TileType)
        
        diversity_ratio = unique_tiles / max_possible_tiles
        
        return diversity_ratio
    
    def _calculate_spatial_diversity(self, level: GeneratedLevel) -> float:
        """Вычисление пространственного разнообразия"""
        
        # Анализируем энтропию распределения тайлов
        tile_counts = Counter(level.tiles.flatten())
        total_tiles = level.width * level.height
        
        entropy = 0.0
        for count in tile_counts.values():
            probability = count / total_tiles
            if probability > 0:
                entropy -= probability * np.log2(probability)
        
        # Нормализуем энтропию
        max_entropy = np.log2(len(tile_counts)) if len(tile_counts) > 1 else 1
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
        
        return normalized_entropy
    
    def _calculate_pattern_diversity(self, level: GeneratedLevel) -> float:
        """Вычисление разнообразия паттернов"""
        
        # Анализируем локальные паттерны 3x3
        patterns = set()
        
        for y in range(level.height - 2):
            for x in range(level.width - 2):
                pattern = level.tiles[y:y+3, x:x+3]
                patterns.add(pattern.tobytes())
        
        total_possible_positions = (level.height - 2) * (level.width - 2)
        
        if total_possible_positions == 0:
            return 0.0
        
        pattern_diversity = len(patterns) / total_possible_positions
        
        return min(pattern_diversity * 2, 1.0)  # Масштабируем
    
    def _evaluate_navigation_complexity(self, level: GeneratedLevel) -> QualityScore:
        """Оценка сложности навигации"""
        
        # Сложность путей от спавна к целям
        path_complexity = self._calculate_path_complexity(level)
        
        # Количество альтернативных путей
        path_alternatives = self._calculate_path_alternatives(level)
        
        # Сложность принятия решений
        decision_complexity = self._calculate_decision_complexity(level)
        
        overall_complexity = np.mean([path_complexity, path_alternatives, decision_complexity])
        
        return QualityScore(
            dimension=QualityDimension.COMPLEXITY,
            score=overall_complexity,
            confidence=0.8,
            details={
                "path_complexity": path_complexity,
                "path_alternatives": path_alternatives,
                "decision_complexity": decision_complexity
            },
            suggestions=[]
        )
    
    def _calculate_path_complexity(self, level: GeneratedLevel) -> float:
        """Вычисление сложности путей"""
        
        if not level.spawn_points or not level.goal_points:
            return 0.0
        
        # Вычисляем кратчайшие пути от каждого спавна к каждой цели
        path_lengths = []
        
        for spawn in level.spawn_points:
            for goal in level.goal_points:
                path_length = self._find_shortest_path(level, spawn, goal)
                if path_length > 0:
                    path_lengths.append(path_length)
        
        if not path_lengths:
            return 0.0
        
        # Сложность = нормализованная средняя длина пути
        avg_path_length = np.mean(path_lengths)
        max_possible_length = level.width + level.height  # Манхэттенское расстояние
        
        complexity = min(avg_path_length / max_possible_length, 1.0)
        
        return complexity
    
    def _find_shortest_path(self, level: GeneratedLevel, start: Tuple[int, int], 
                           goal: Tuple[int, int]) -> int:
        """Поиск кратчайшего пути с помощью BFS"""
        
        walkable_tiles = [TileType.FLOOR.value, TileType.DOOR.value, 
                         TileType.SPAWN.value, TileType.GOAL.value]
        
        queue = [(start, 0)]
        visited = {start}
        
        while queue:
            (x, y), distance = queue.pop(0)
            
            if (x, y) == goal:
                return distance
            
            # Проверяем соседей
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = x + dx, y + dy
                
                if (0 <= nx < level.width and 0 <= ny < level.height and 
                    (nx, ny) not in visited and 
                    level.tiles[ny, nx] in walkable_tiles):
                    
                    visited.add((nx, ny))
                    queue.append(((nx, ny), distance + 1))
        
        return 0  # Путь не найден
    
    def _calculate_path_alternatives(self, level: GeneratedLevel) -> float:
        """Вычисление количества альтернативных путей"""
        
        # Упрощенная оценка: считаем количество развилок
        walkable_tiles = [TileType.FLOOR.value, TileType.DOOR.value]
        
        junction_count = 0
        
        for y in range(1, level.height - 1):
            for x in range(1, level.width - 1):
                if level.tiles[y, x] in walkable_tiles:
                    # Считаем проходимых соседей
                    neighbors = [
                        level.tiles[y-1, x], level.tiles[y+1, x],
                        level.tiles[y, x-1], level.tiles[y, x+1]
                    ]
                    
                    walkable_neighbors = sum(1 for tile in neighbors if tile in walkable_tiles)
                    
                    # Развилка = 3 или более проходимых направления
                    if walkable_neighbors >= 3:
                        junction_count += 1
        
        # Нормализуем по размеру уровня
        total_walkable = np.sum(np.isin(level.tiles, walkable_tiles))
        
        if total_walkable == 0:
            return 0.0
        
        junction_density = junction_count / total_walkable
        
        return min(junction_density * 10, 1.0)  # Масштабируем
    
    def _calculate_decision_complexity(self, level: GeneratedLevel) -> float:
        """Вычисление сложности принятия решений"""
        
        # Анализируем области, где игрок должен принимать решения о направлении
        decision_points = 0
        
        walkable_tiles = [TileType.FLOOR.value, TileType.DOOR.value]
        
        for y in range(1, level.height - 1):
            for x in range(1, level.width - 1):
                if level.tiles[y, x] in walkable_tiles:
                    # Проверяем, есть ли выбор направления
                    directions = [
                        level.tiles[y-1, x] in walkable_tiles,  # север
                        level.tiles[y+1, x] in walkable_tiles,  # юг
                        level.tiles[y, x-1] in walkable_tiles,  # запад
                        level.tiles[y, x+1] in walkable_tiles   # восток
                    ]
                    
                    open_directions = sum(directions)
                    
                    # Точка принятия решения = 2 или более направления
                    if open_directions >= 2:
                        decision_points += 1
        
        # Нормализуем
        total_walkable = np.sum(np.isin(level.tiles, walkable_tiles))
        
        if total_walkable == 0:
            return 0.0
        
        decision_density = decision_points / total_walkable
        
        return min(decision_density * 5, 1.0)  # Масштабируем


class QualityMetricsManager:
    """Менеджер метрик качества"""
    
    def __init__(self):
        self.quest_evaluator = QuestQualityEvaluator()
        self.level_evaluator = LevelQualityEvaluator()
    
    def evaluate_quest(self, quest: Quest) -> QualityReport:
        """Оценка качества квеста"""
        return self.quest_evaluator.evaluate_quest(quest)
    
    def evaluate_level(self, level: GeneratedLevel) -> QualityReport:
        """Оценка качества уровня"""
        return self.level_evaluator.evaluate_level(level)
    
    def evaluate_batch(self, quests: List[Quest], levels: Optional[List[GeneratedLevel]] = None) -> List[QualityReport]:
        """Батчевая оценка качества"""
        
        reports = []
        
        # Оцениваем квесты
        for quest in quests:
            report = self.evaluate_quest(quest)
            reports.append(report)
        
        # Оцениваем уровни если предоставлены
        if levels:
            for level in levels:
                report = self.evaluate_level(level)
                reports.append(report)
        
        return reports
    
    def export_quality_report(self, report: QualityReport, output_path: str):
        """Экспорт отчета о качестве"""
        
        export_data = {
            "overall_score": report.overall_score,
            "dimension_scores": {
                dim.value: {
                    "score": score.score,
                    "confidence": score.confidence,
                    "details": score.details,
                    "suggestions": score.suggestions
                }
                for dim, score in report.dimension_scores.items()
            },
            "strengths": report.strengths,
            "weaknesses": report.weaknesses,
            "recommendations": report.recommendations,
            "metadata": report.metadata
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Отчет о качестве экспортирован в: {output_path}")
    
    def compare_quality_reports(self, reports: List[QualityReport]) -> Dict[str, Any]:
        """Сравнение отчетов о качестве"""
        
        if not reports:
            return {}
        
        comparison = {
            "average_scores": {},
            "best_performer": None,
            "worst_performer": None,
            "improvement_trends": {},
            "consistency_analysis": {}
        }
        
        # Средние оценки по измерениям
        all_dimensions = set()
        for report in reports:
            all_dimensions.update(report.dimension_scores.keys())
        
        for dimension in all_dimensions:
            scores = [report.dimension_scores[dimension].score 
                     for report in reports if dimension in report.dimension_scores]
            
            if scores:
                comparison["average_scores"][dimension.value] = {
                    "mean": np.mean(scores),
                    "std": np.std(scores),
                    "min": np.min(scores),
                    "max": np.max(scores)
                }
        
        # Лучший и худший исполнители
        overall_scores = [report.overall_score for report in reports]
        
        if overall_scores:
            best_idx = np.argmax(overall_scores)
            worst_idx = np.argmin(overall_scores)
            
            comparison["best_performer"] = {
                "index": best_idx,
                "score": overall_scores[best_idx],
                "metadata": reports[best_idx].metadata
            }
            
            comparison["worst_performer"] = {
                "index": worst_idx,
                "score": overall_scores[worst_idx],
                "metadata": reports[worst_idx].metadata
            }
        
        return comparison