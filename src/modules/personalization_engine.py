"""
Модуль персонализации игрового контента на основе подходов PANGeA
(Personalized AI Narrative Generation Architecture) для адаптации
квестов под предпочтения и стиль игрока
"""

import asyncio
import json
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import pickle
from loguru import logger
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

from src.core.models import Scene, Choice, Quest, ScenarioInput, GenerationConfig


class PlayerType(Enum):
    """Типы игроков по предпочтениям"""
    EXPLORER = "explorer"        # Исследователь
    ACHIEVER = "achiever"        # Достигатор
    SOCIALIZER = "socializer"    # Социализатор
    KILLER = "killer"            # Убийца (PvP ориентированный)
    STORYTELLER = "storyteller"  # Любитель историй
    PUZZLER = "puzzler"          # Любитель головоломок
    COLLECTOR = "collector"      # Коллекционер
    COMPETITOR = "competitor"    # Соревновательный


class ContentPreference(Enum):
    """Предпочтения по контенту"""
    ACTION = "action"
    DIALOGUE = "dialogue"
    EXPLORATION = "exploration"
    PUZZLE = "puzzle"
    COMBAT = "combat"
    STORY = "story"
    STRATEGY = "strategy"
    HUMOR = "humor"
    ROMANCE = "romance"
    MYSTERY = "mystery"


class DifficultyPreference(Enum):
    """Предпочтения по сложности"""
    CASUAL = "casual"
    NORMAL = "normal"
    CHALLENGING = "challenging"
    HARDCORE = "hardcore"


@dataclass
class PlayerProfile:
    """Профиль игрока"""
    player_id: str
    player_type: PlayerType
    content_preferences: Dict[ContentPreference, float]  # 0.0 - 1.0
    difficulty_preference: DifficultyPreference
    
    # Поведенческие метрики
    session_length_preference: float = 0.5  # 0 = короткие, 1 = длинные
    choice_making_speed: float = 0.5        # 0 = медленно, 1 = быстро
    exploration_tendency: float = 0.5       # 0 = прямой путь, 1 = исследование
    risk_tolerance: float = 0.5             # 0 = осторожный, 1 = рискованный
    
    # Стилистические предпочтения
    preferred_narrative_style: str = "balanced"  # formal, casual, dramatic, humorous
    preferred_scene_length: str = "medium"       # short, medium, long
    preferred_choice_count: int = 3              # среднее количество выборов
    
    # История взаимодействий
    completed_quests: List[str] = None
    favorite_genres: List[str] = None
    choice_patterns: Dict[str, float] = None
    
    def __post_init__(self):
        if self.completed_quests is None:
            self.completed_quests = []
        if self.favorite_genres is None:
            self.favorite_genres = []
        if self.choice_patterns is None:
            self.choice_patterns = {}


@dataclass
class PersonalizationContext:
    """Контекст для персонализации"""
    player_profile: PlayerProfile
    current_session_data: Dict[str, Any]
    quest_history: List[Dict[str, Any]]
    real_time_feedback: Dict[str, float]


@dataclass
class AdaptationStrategy:
    """Стратегия адаптации контента"""
    scene_adaptation: Dict[str, Any]
    choice_adaptation: Dict[str, Any]
    difficulty_adaptation: Dict[str, Any]
    pacing_adaptation: Dict[str, Any]
    style_adaptation: Dict[str, Any]


class PlayerBehaviorAnalyzer:
    """Анализатор поведения игрока"""
    
    def __init__(self):
        self.behavior_patterns = {}
        self.clustering_model = None
        self.scaler = StandardScaler()
    
    def analyze_player_choices(self, choice_history: List[Dict[str, Any]]) -> Dict[str, float]:
        """Анализ паттернов выбора игрока"""
        if not choice_history:
            return {}
        
        patterns = {
            "aggressive_choices": 0.0,
            "cautious_choices": 0.0,
            "exploratory_choices": 0.0,
            "direct_choices": 0.0,
            "social_choices": 0.0,
            "solo_choices": 0.0
        }
        
        # Ключевые слова для классификации выборов
        aggressive_keywords = ['атаковать', 'сражаться', 'нападать', 'убить', 'уничтожить']
        cautious_keywords = ['осторожно', 'тихо', 'спрятаться', 'подождать', 'наблюдать']
        exploratory_keywords = ['исследовать', 'изучить', 'поискать', 'осмотреть', 'найти']
        direct_keywords = ['прямо', 'быстро', 'сразу', 'немедленно', 'идти']
        social_keywords = ['говорить', 'спросить', 'договориться', 'помочь', 'объединиться']
        solo_keywords = ['один', 'сам', 'самостоятельно', 'избежать', 'обойти']
        
        keyword_patterns = {
            "aggressive_choices": aggressive_keywords,
            "cautious_choices": cautious_keywords,
            "exploratory_choices": exploratory_keywords,
            "direct_choices": direct_keywords,
            "social_choices": social_keywords,
            "solo_choices": solo_keywords
        }
        
        total_choices = len(choice_history)
        
        for choice_data in choice_history:
            choice_text = choice_data.get('choice_text', '').lower()
            
            for pattern_name, keywords in keyword_patterns.items():
                if any(keyword in choice_text for keyword in keywords):
                    patterns[pattern_name] += 1
        
        # Нормализуем
        for pattern_name in patterns:
            patterns[pattern_name] = patterns[pattern_name] / max(total_choices, 1)
        
        return patterns
    
    def analyze_session_patterns(self, session_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Анализ паттернов сессии"""
        if not session_data:
            return {}
        
        patterns = {
            "average_decision_time": 0.0,
            "scene_completion_rate": 0.0,
            "backtracking_frequency": 0.0,
            "help_seeking_frequency": 0.0,
            "exploration_depth": 0.0
        }
        
        decision_times = []
        completed_scenes = 0
        total_scenes = len(session_data)
        backtrack_count = 0
        help_requests = 0
        unique_scenes_visited = set()
        
        for session_item in session_data:
            # Время принятия решения
            if 'decision_time' in session_item:
                decision_times.append(session_item['decision_time'])
            
            # Завершение сцены
            if session_item.get('completed', False):
                completed_scenes += 1
            
            # Возврат назад
            if session_item.get('action_type') == 'backtrack':
                backtrack_count += 1
            
            # Запрос помощи
            if session_item.get('help_requested', False):
                help_requests += 1
            
            # Посещенные сцены
            if 'scene_id' in session_item:
                unique_scenes_visited.add(session_item['scene_id'])
        
        # Вычисляем метрики
        if decision_times:
            patterns["average_decision_time"] = np.mean(decision_times)
        
        patterns["scene_completion_rate"] = completed_scenes / max(total_scenes, 1)
        patterns["backtracking_frequency"] = backtrack_count / max(total_scenes, 1)
        patterns["help_seeking_frequency"] = help_requests / max(total_scenes, 1)
        patterns["exploration_depth"] = len(unique_scenes_visited) / max(total_scenes, 1)
        
        return patterns
    
    def classify_player_type(self, choice_patterns: Dict[str, float], 
                           session_patterns: Dict[str, float]) -> PlayerType:
        """Классификация типа игрока"""
        
        # Вычисляем скоры для каждого типа игрока
        type_scores = {}
        
        # Explorer (Исследователь)
        type_scores[PlayerType.EXPLORER] = (
            choice_patterns.get("exploratory_choices", 0) * 0.4 +
            session_patterns.get("exploration_depth", 0) * 0.3 +
            session_patterns.get("backtracking_frequency", 0) * 0.3
        )
        
        # Achiever (Достигатор)
        type_scores[PlayerType.ACHIEVER] = (
            session_patterns.get("scene_completion_rate", 0) * 0.4 +
            choice_patterns.get("direct_choices", 0) * 0.3 +
            (1.0 - session_patterns.get("help_seeking_frequency", 0)) * 0.3
        )
        
        # Socializer (Социализатор)
        type_scores[PlayerType.SOCIALIZER] = (
            choice_patterns.get("social_choices", 0) * 0.6 +
            session_patterns.get("help_seeking_frequency", 0) * 0.4
        )
        
        # Killer (PvP ориентированный)
        type_scores[PlayerType.KILLER] = (
            choice_patterns.get("aggressive_choices", 0) * 0.7 +
            (1.0 - choice_patterns.get("cautious_choices", 0)) * 0.3
        )
        
        # Storyteller (Любитель историй)
        type_scores[PlayerType.STORYTELLER] = (
            session_patterns.get("average_decision_time", 0) / 60 * 0.4 +  # Нормализуем время
            session_patterns.get("exploration_depth", 0) * 0.3 +
            (1.0 - choice_patterns.get("direct_choices", 0)) * 0.3
        )
        
        # Puzzler (Любитель головоломок)
        type_scores[PlayerType.PUZZLER] = (
            session_patterns.get("average_decision_time", 0) / 60 * 0.5 +
            choice_patterns.get("cautious_choices", 0) * 0.3 +
            session_patterns.get("backtracking_frequency", 0) * 0.2
        )
        
        # Возвращаем тип с наивысшим скором
        return max(type_scores.items(), key=lambda x: x[1])[0]


class ContentAdaptationEngine:
    """Движок адаптации контента"""
    
    def __init__(self):
        self.adaptation_rules = self._load_adaptation_rules()
    
    def _load_adaptation_rules(self) -> Dict[str, Any]:
        """Загрузка правил адаптации"""
        return {
            PlayerType.EXPLORER: {
                "scene_modifications": {
                    "add_exploration_options": True,
                    "detailed_descriptions": True,
                    "hidden_paths": True
                },
                "choice_modifications": {
                    "exploration_choices_weight": 1.5,
                    "investigative_options": True
                },
                "pacing": {
                    "allow_longer_scenes": True,
                    "reduce_time_pressure": True
                }
            },
            PlayerType.ACHIEVER: {
                "scene_modifications": {
                    "clear_objectives": True,
                    "progress_indicators": True,
                    "challenge_scaling": True
                },
                "choice_modifications": {
                    "goal_oriented_choices": True,
                    "efficiency_options": True
                },
                "pacing": {
                    "maintain_momentum": True,
                    "clear_progression": True
                }
            },
            PlayerType.SOCIALIZER: {
                "scene_modifications": {
                    "character_interactions": True,
                    "dialogue_focus": True,
                    "emotional_connections": True
                },
                "choice_modifications": {
                    "social_interaction_options": True,
                    "empathy_choices": True
                },
                "pacing": {
                    "character_development_time": True,
                    "relationship_building": True
                }
            },
            PlayerType.STORYTELLER: {
                "scene_modifications": {
                    "rich_narrative": True,
                    "atmospheric_details": True,
                    "backstory_elements": True
                },
                "choice_modifications": {
                    "narrative_impact_choices": True,
                    "character_development_options": True
                },
                "pacing": {
                    "allow_contemplation": True,
                    "detailed_exposition": True
                }
            }
        }
    
    def adapt_scene(self, scene: Scene, player_profile: PlayerProfile, 
                   context: PersonalizationContext) -> Scene:
        """Адаптация сцены под игрока"""
        
        player_type = player_profile.player_type
        rules = self.adaptation_rules.get(player_type, {})
        
        # Создаем копию сцены для модификации
        adapted_scene = Scene(
            scene_id=scene.scene_id,
            text=self._adapt_scene_text(scene.text, player_profile, rules),
            choices=self._adapt_choices(scene.choices, player_profile, rules),
            image_prompt=scene.image_prompt,
            mood=scene.mood,
            location=scene.location
        )
        
        return adapted_scene
    
    def _adapt_scene_text(self, original_text: str, player_profile: PlayerProfile, 
                         rules: Dict[str, Any]) -> str:
        """Адаптация текста сцены"""
        
        adapted_text = original_text
        scene_mods = rules.get("scene_modifications", {})
        
        # Адаптация длины в зависимости от предпочтений
        if player_profile.preferred_scene_length == "short":
            # Сокращаем описания
            sentences = adapted_text.split('. ')
            if len(sentences) > 3:
                adapted_text = '. '.join(sentences[:3]) + '.'
        
        elif player_profile.preferred_scene_length == "long":
            # Добавляем детали для любителей длинных описаний
            if scene_mods.get("detailed_descriptions"):
                adapted_text = self._add_detailed_descriptions(adapted_text)
        
        # Адаптация стиля
        if player_profile.preferred_narrative_style == "dramatic":
            adapted_text = self._make_more_dramatic(adapted_text)
        elif player_profile.preferred_narrative_style == "casual":
            adapted_text = self._make_more_casual(adapted_text)
        elif player_profile.preferred_narrative_style == "humorous":
            adapted_text = self._add_humor_elements(adapted_text)
        
        return adapted_text
    
    def _adapt_choices(self, original_choices: List[Choice], player_profile: PlayerProfile,
                      rules: Dict[str, Any]) -> List[Choice]:
        """Адаптация выборов"""
        
        adapted_choices = original_choices.copy()
        choice_mods = rules.get("choice_modifications", {})
        
        # Адаптируем количество выборов
        target_choice_count = player_profile.preferred_choice_count
        
        if len(adapted_choices) > target_choice_count:
            # Оставляем наиболее подходящие выборы
            adapted_choices = self._select_best_choices(
                adapted_choices, target_choice_count, player_profile
            )
        elif len(adapted_choices) < target_choice_count:
            # Добавляем дополнительные выборы если возможно
            adapted_choices = self._add_additional_choices(
                adapted_choices, target_choice_count, player_profile, choice_mods
            )
        
        # Модифицируем тексты выборов
        for choice in adapted_choices:
            choice.text = self._adapt_choice_text(choice.text, player_profile, choice_mods)
        
        return adapted_choices
    
    def _add_detailed_descriptions(self, text: str) -> str:
        """Добавление детализированных описаний"""
        # Простое добавление сенсорных деталей
        enhanced_text = text
        
        # Добавляем атмосферные детали
        if "комната" in text.lower():
            enhanced_text += " Воздух в помещении кажется затхлым, а тени играют на стенах."
        elif "коридор" in text.lower():
            enhanced_text += " Звуки твоих шагов эхом отражаются от стен."
        elif "улица" in text.lower():
            enhanced_text += " Легкий ветер приносит различные городские запахи."
        
        return enhanced_text
    
    def _make_more_dramatic(self, text: str) -> str:
        """Усиление драматичности текста"""
        # Заменяем нейтральные фразы на более драматичные
        dramatic_replacements = {
            "идешь": "решительно направляешься",
            "видишь": "внезапно замечаешь",
            "слышишь": "отчетливо различаешь",
            "открываешь": "с трепетом открываешь"
        }
        
        adapted_text = text
        for neutral, dramatic in dramatic_replacements.items():
            adapted_text = adapted_text.replace(neutral, dramatic)
        
        return adapted_text
    
    def _make_more_casual(self, text: str) -> str:
        """Упрощение стиля текста"""
        # Заменяем формальные конструкции на более простые
        casual_replacements = {
            "направляешься": "идешь",
            "осуществляешь": "делаешь",
            "предпринимаешь": "начинаешь"
        }
        
        adapted_text = text
        for formal, casual in casual_replacements.items():
            adapted_text = adapted_text.replace(formal, casual)
        
        return adapted_text
    
    def _add_humor_elements(self, text: str) -> str:
        """Добавление юмористических элементов"""
        # Простые юмористические вставки
        if "дверь" in text.lower() and "закрыта" in text.lower():
            text += " Впрочем, это было довольно предсказуемо."
        elif "темно" in text.lower():
            text += " Надо было взять фонарик побольше."
        
        return text
    
    def _select_best_choices(self, choices: List[Choice], target_count: int,
                           player_profile: PlayerProfile) -> List[Choice]:
        """Выбор наиболее подходящих вариантов выбора"""
        
        # Оцениваем каждый выбор по релевантности для игрока
        choice_scores = []
        
        for choice in choices:
            score = self._score_choice_relevance(choice, player_profile)
            choice_scores.append((choice, score))
        
        # Сортируем по релевантности и берем лучшие
        choice_scores.sort(key=lambda x: x[1], reverse=True)
        return [choice for choice, _ in choice_scores[:target_count]]
    
    def _score_choice_relevance(self, choice: Choice, player_profile: PlayerProfile) -> float:
        """Оценка релевантности выбора для игрока"""
        
        choice_text = choice.text.lower()
        score = 0.5  # базовый скор
        
        # Анализируем предпочтения по контенту
        content_prefs = player_profile.content_preferences
        
        if ContentPreference.ACTION in content_prefs:
            action_words = ['атаковать', 'бежать', 'прыгнуть', 'сражаться']
            if any(word in choice_text for word in action_words):
                score += content_prefs[ContentPreference.ACTION] * 0.3
        
        if ContentPreference.DIALOGUE in content_prefs:
            dialogue_words = ['спросить', 'сказать', 'поговорить', 'объяснить']
            if any(word in choice_text for word in dialogue_words):
                score += content_prefs[ContentPreference.DIALOGUE] * 0.3
        
        if ContentPreference.EXPLORATION in content_prefs:
            exploration_words = ['исследовать', 'поискать', 'осмотреть', 'изучить']
            if any(word in choice_text for word in exploration_words):
                score += content_prefs[ContentPreference.EXPLORATION] * 0.3
        
        # Учитываем толерантность к риску
        risk_words = ['опасно', 'рискованно', 'осторожно']
        if any(word in choice_text for word in risk_words):
            if player_profile.risk_tolerance > 0.7:
                score += 0.2  # Рисковые игроки любят опасные выборы
            else:
                score -= 0.2  # Осторожные игроки их избегают
        
        return max(0.0, min(1.0, score))
    
    def _add_additional_choices(self, choices: List[Choice], target_count: int,
                              player_profile: PlayerProfile, 
                              choice_mods: Dict[str, Any]) -> List[Choice]:
        """Добавление дополнительных выборов"""
        
        additional_choices = []
        needed_choices = target_count - len(choices)
        
        # Генерируем дополнительные выборы на основе типа игрока
        if choice_mods.get("exploration_choices_weight", 0) > 1:
            additional_choices.append(Choice(
                text="Внимательно осмотреться вокруг",
                next_scene="exploration_branch"
            ))
        
        if choice_mods.get("social_interaction_options"):
            additional_choices.append(Choice(
                text="Попытаться найти кого-то для разговора",
                next_scene="social_branch"
            ))
        
        if choice_mods.get("goal_oriented_choices"):
            additional_choices.append(Choice(
                text="Сосредоточиться на главной цели",
                next_scene="direct_path"
            ))
        
        # Добавляем только нужное количество
        return choices + additional_choices[:needed_choices]
    
    def _adapt_choice_text(self, choice_text: str, player_profile: PlayerProfile,
                          choice_mods: Dict[str, Any]) -> str:
        """Адаптация текста выбора"""
        
        adapted_text = choice_text
        
        # Адаптируем стиль в соответствии с предпочтениями
        if player_profile.preferred_narrative_style == "dramatic":
            adapted_text = self._make_choice_more_dramatic(adapted_text)
        elif player_profile.preferred_narrative_style == "casual":
            adapted_text = self._make_choice_more_casual(adapted_text)
        
        return adapted_text
    
    def _make_choice_more_dramatic(self, choice_text: str) -> str:
        """Усиление драматичности выбора"""
        dramatic_prefixes = {
            "идти": "решительно направиться",
            "взять": "смело схватить",
            "сказать": "торжественно произнести"
        }
        
        for neutral, dramatic in dramatic_prefixes.items():
            if choice_text.startswith(neutral):
                return choice_text.replace(neutral, dramatic, 1)
        
        return choice_text
    
    def _make_choice_more_casual(self, choice_text: str) -> str:
        """Упрощение выбора"""
        # Убираем излишне формальные конструкции
        return choice_text.replace("осуществить", "сделать").replace("предпринять", "попробовать")


class PersonalizationEngine:
    """Основной движок персонализации"""
    
    def __init__(self):
        self.behavior_analyzer = PlayerBehaviorAnalyzer()
        self.content_adapter = ContentAdaptationEngine()
        self.player_profiles = {}
        self.interaction_history = {}
    
    def create_player_profile(self, player_id: str, initial_data: Optional[Dict[str, Any]] = None) -> PlayerProfile:
        """Создание профиля игрока"""
        
        # Базовые предпочтения по умолчанию
        default_content_prefs = {
            ContentPreference.ACTION: 0.5,
            ContentPreference.DIALOGUE: 0.5,
            ContentPreference.EXPLORATION: 0.5,
            ContentPreference.PUZZLE: 0.5,
            ContentPreference.COMBAT: 0.5,
            ContentPreference.STORY: 0.5,
            ContentPreference.STRATEGY: 0.5,
            ContentPreference.HUMOR: 0.3,
            ContentPreference.ROMANCE: 0.2,
            ContentPreference.MYSTERY: 0.4
        }
        
        # Обновляем предпочтения из начальных данных
        if initial_data and 'content_preferences' in initial_data:
            for pref, value in initial_data['content_preferences'].items():
                if isinstance(pref, str):
                    pref_enum = ContentPreference(pref)
                    default_content_prefs[pref_enum] = value
        
        profile = PlayerProfile(
            player_id=player_id,
            player_type=PlayerType.EXPLORER,  # По умолчанию
            content_preferences=default_content_prefs,
            difficulty_preference=DifficultyPreference.NORMAL
        )
        
        # Применяем начальные данные если есть
        if initial_data:
            for key, value in initial_data.items():
                if hasattr(profile, key) and key != 'content_preferences':
                    setattr(profile, key, value)
        
        self.player_profiles[player_id] = profile
        return profile
    
    def update_player_profile(self, player_id: str, interaction_data: Dict[str, Any]):
        """Обновление профиля игрока на основе взаимодействий"""
        
        if player_id not in self.player_profiles:
            self.create_player_profile(player_id)
        
        profile = self.player_profiles[player_id]
        
        # Добавляем данные в историю
        if player_id not in self.interaction_history:
            self.interaction_history[player_id] = []
        
        self.interaction_history[player_id].append(interaction_data)
        
        # Анализируем поведение
        choice_patterns = self.behavior_analyzer.analyze_player_choices(
            self.interaction_history[player_id]
        )
        
        session_patterns = self.behavior_analyzer.analyze_session_patterns(
            self.interaction_history[player_id]
        )
        
        # Обновляем тип игрока
        new_player_type = self.behavior_analyzer.classify_player_type(
            choice_patterns, session_patterns
        )
        
        if new_player_type != profile.player_type:
            logger.info(f"Тип игрока {player_id} изменился: {profile.player_type} -> {new_player_type}")
            profile.player_type = new_player_type
        
        # Обновляем предпочтения контента на основе выборов
        self._update_content_preferences(profile, choice_patterns)
        
        # Обновляем поведенческие метрики
        self._update_behavioral_metrics(profile, session_patterns)
    
    def _update_content_preferences(self, profile: PlayerProfile, choice_patterns: Dict[str, float]):
        """Обновление предпочтений контента"""
        
        # Мягкое обновление предпочтений (learning rate = 0.1)
        learning_rate = 0.1
        
        # Обновляем на основе паттернов выбора
        if choice_patterns.get("aggressive_choices", 0) > 0.3:
            profile.content_preferences[ContentPreference.ACTION] = min(
                profile.content_preferences[ContentPreference.ACTION] + learning_rate * 0.2, 1.0
            )
            profile.content_preferences[ContentPreference.COMBAT] = min(
                profile.content_preferences[ContentPreference.COMBAT] + learning_rate * 0.3, 1.0
            )
        
        if choice_patterns.get("social_choices", 0) > 0.3:
            profile.content_preferences[ContentPreference.DIALOGUE] = min(
                profile.content_preferences[ContentPreference.DIALOGUE] + learning_rate * 0.3, 1.0
            )
        
        if choice_patterns.get("exploratory_choices", 0) > 0.3:
            profile.content_preferences[ContentPreference.EXPLORATION] = min(
                profile.content_preferences[ContentPreference.EXPLORATION] + learning_rate * 0.3, 1.0
            )
    
    def _update_behavioral_metrics(self, profile: PlayerProfile, session_patterns: Dict[str, float]):
        """Обновление поведенческих метрик"""
        
        learning_rate = 0.15
        
        # Обновляем склонность к исследованию
        exploration_score = session_patterns.get("exploration_depth", 0.5)
        profile.exploration_tendency = (
            profile.exploration_tendency * (1 - learning_rate) + 
            exploration_score * learning_rate
        )
        
        # Обновляем толерантность к риску на основе скорости принятия решений
        decision_speed = min(60.0 / max(session_patterns.get("average_decision_time", 30), 1), 1.0)
        profile.risk_tolerance = (
            profile.risk_tolerance * (1 - learning_rate) + 
            decision_speed * learning_rate
        )
        
        # Обновляем предпочтения по длительности сессии
        completion_rate = session_patterns.get("scene_completion_rate", 0.5)
        if completion_rate > 0.8:
            profile.session_length_preference = min(profile.session_length_preference + 0.1, 1.0)
        elif completion_rate < 0.3:
            profile.session_length_preference = max(profile.session_length_preference - 0.1, 0.0)
    
    def personalize_quest(self, quest: Quest, player_id: str, 
                         context_data: Optional[Dict[str, Any]] = None) -> Quest:
        """Персонализация квеста для игрока"""
        
        if player_id not in self.player_profiles:
            self.create_player_profile(player_id)
        
        profile = self.player_profiles[player_id]
        
        logger.info(f"Персонализируем квест '{quest.title}' для игрока {player_id} ({profile.player_type.value})")
        
        # Создаем контекст персонализации
        context = PersonalizationContext(
            player_profile=profile,
            current_session_data=context_data or {},
            quest_history=self.interaction_history.get(player_id, []),
            real_time_feedback={}
        )
        
        # Адаптируем каждую сцену
        personalized_scenes = []
        for scene in quest.scenes:
            adapted_scene = self.content_adapter.adapt_scene(scene, profile, context)
            personalized_scenes.append(adapted_scene)
        
        # Создаем персонализированную версию квеста
        personalized_quest = Quest(
            title=quest.title,
            genre=quest.genre,
            hero=quest.hero,
            goal=quest.goal,
            scenes=personalized_scenes,
            start_scene=quest.start_scene,
            paths=quest.paths,
            metadata={
                **quest.metadata,
                "personalized_for": player_id,
                "player_type": profile.player_type.value,
                "adaptation_timestamp": pd.Timestamp.now().isoformat()
            }
        )
        
        return personalized_quest
    
    def get_player_insights(self, player_id: str) -> Dict[str, Any]:
        """Получение аналитики по игроку"""
        
        if player_id not in self.player_profiles:
            return {"error": "Player profile not found"}
        
        profile = self.player_profiles[player_id]
        history = self.interaction_history.get(player_id, [])
        
        # Анализируем паттерны
        choice_patterns = self.behavior_analyzer.analyze_player_choices(history)
        session_patterns = self.behavior_analyzer.analyze_session_patterns(history)
        
        insights = {
            "player_type": profile.player_type.value,
            "content_preferences": {pref.value: score for pref, score in profile.content_preferences.items()},
            "behavioral_metrics": {
                "exploration_tendency": profile.exploration_tendency,
                "risk_tolerance": profile.risk_tolerance,
                "session_length_preference": profile.session_length_preference,
                "choice_making_speed": profile.choice_making_speed
            },
            "choice_patterns": choice_patterns,
            "session_patterns": session_patterns,
            "total_interactions": len(history),
            "favorite_genres": profile.favorite_genres,
            "completed_quests": len(profile.completed_quests)
        }
        
        return insights
    
    def export_player_profile(self, player_id: str, output_path: str):
        """Экспорт профиля игрока"""
        
        if player_id not in self.player_profiles:
            logger.error(f"Профиль игрока {player_id} не найден")
            return
        
        profile = self.player_profiles[player_id]
        insights = self.get_player_insights(player_id)
        
        export_data = {
            "profile": asdict(profile),
            "insights": insights,
            "export_timestamp": pd.Timestamp.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"Профиль игрока {player_id} экспортирован в {output_path}")
    
    def save_profiles(self, filepath: str):
        """Сохранение всех профилей"""
        save_data = {
            "profiles": self.player_profiles,
            "history": self.interaction_history
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(save_data, f)
        
        logger.info(f"Профили сохранены в {filepath}")
    
    def load_profiles(self, filepath: str):
        """Загрузка профилей"""
        try:
            with open(filepath, 'rb') as f:
                save_data = pickle.load(f)
            
            self.player_profiles = save_data.get("profiles", {})
            self.interaction_history = save_data.get("history", {})
            
            logger.info(f"Загружено {len(self.player_profiles)} профилей из {filepath}")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки профилей: {e}")
    
    def get_recommendation_for_player(self, player_id: str, available_quests: List[Quest]) -> List[Tuple[Quest, float]]:
        """Рекомендации квестов для игрока"""
        
        if player_id not in self.player_profiles:
            return []
        
        profile = self.player_profiles[player_id]
        recommendations = []
        
        for quest in available_quests:
            score = self._score_quest_for_player(quest, profile)
            recommendations.append((quest, score))
        
        # Сортируем по релевантности
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        return recommendations
    
    def _score_quest_for_player(self, quest: Quest, profile: PlayerProfile) -> float:
        """Оценка релевантности квеста для игрока"""
        
        score = 0.5  # базовый скор
        
        # Анализируем жанровые предпочтения
        if quest.genre.lower() in [g.lower() for g in profile.favorite_genres]:
            score += 0.3
        
        # Анализируем сложность
        scene_count = len(quest.scenes)
        if profile.difficulty_preference == DifficultyPreference.CASUAL and scene_count <= 5:
            score += 0.2
        elif profile.difficulty_preference == DifficultyPreference.HARDCORE and scene_count >= 8:
            score += 0.2
        elif profile.difficulty_preference == DifficultyPreference.NORMAL and 5 < scene_count < 8:
            score += 0.2
        
        # Анализируем контент на основе предпочтений
        quest_text = ' '.join([scene.text for scene in quest.scenes]).lower()
        
        # Проверяем соответствие предпочтениям контента
        content_indicators = {
            ContentPreference.ACTION: ['бой', 'атака', 'сражение', 'битва'],
            ContentPreference.DIALOGUE: ['говорить', 'сказать', 'разговор', 'диалог'],
            ContentPreference.EXPLORATION: ['исследовать', 'найти', 'поиск', 'обнаружить'],
            ContentPreference.MYSTERY: ['тайна', 'загадка', 'секрет', 'неизвестно']
        }
        
        for content_type, keywords in content_indicators.items():
            if content_type in profile.content_preferences:
                keyword_score = sum(1 for keyword in keywords if keyword in quest_text)
                normalized_score = min(keyword_score / len(keywords), 1.0)
                score += profile.content_preferences[content_type] * normalized_score * 0.1
        
        return max(0.0, min(1.0, score))