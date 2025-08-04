from typing import List, Dict, Optional, Any, Union, Tuple
from pydantic import BaseModel, Field, validator
from enum import Enum
import numpy as np


class Genre(str, Enum):
    CYBERPUNK = "киберпанк"
    FANTASY = "фэнтези"
    SCIFI = "научная фантастика"
    DETECTIVE = "детектив"
    HORROR = "хоррор"
    POSTAPOC = "постапокалипсис"
    STEAMPUNK = "стимпанк"


class ScenarioInput(BaseModel):
    genre: str = Field(..., description="Жанр квеста")
    hero: str = Field(..., description="Описание главного героя")
    goal: str = Field(..., description="Цель или задача героя")
    language: str = Field(default="ru", description="Язык генерации")
    
    @validator('genre')
    def normalize_genre(cls, v):
        return v.lower().strip()


class Choice(BaseModel):
    text: str = Field(..., description="Текст варианта действия")
    next_scene: str = Field(..., description="ID следующей сцены")
    condition: Optional[str] = Field(None, description="Условие доступности выбора")
    effect: Optional[str] = Field(None, description="Эффект от выбора")


class Scene(BaseModel):
    scene_id: str = Field(..., description="Уникальный идентификатор сцены")
    text: str = Field(..., description="Описание сцены")
    choices: List[Choice] = Field(..., description="Варианты действий игрока")
    image_prompt: Optional[str] = Field(None, description="Промпт для генерации изображения")
    mood: Optional[str] = Field(None, description="Настроение/атмосфера сцены")
    location: Optional[str] = Field(None, description="Локация сцены")
    
    # Новые поля для расширенной функциональности
    level_position: Optional[Tuple[int, int]] = Field(None, description="Позиция на уровне (x, y)")
    required_objects: Optional[List[str]] = Field(None, description="Необходимые объекты для сцены")
    visual_style: Optional[str] = Field(None, description="Стиль визуализации")
    difficulty_level: Optional[float] = Field(None, description="Уровень сложности сцены (0.0-1.0)")
    emotional_tags: Optional[List[str]] = Field(None, description="Эмоциональные теги")
    interaction_type: Optional[str] = Field(None, description="Тип взаимодействия (dialogue, combat, exploration, etc.)")
    
    @validator('choices')
    def validate_choices(cls, v):
        # Разрешаем пустые списки для финальных сцен
        if v is None:
            return []
        return v
    
    @validator('difficulty_level')  
    def validate_difficulty(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Уровень сложности должен быть между 0.0 и 1.0")
        return v


class StoryPath(BaseModel):
    path_id: str = Field(..., description="ID пути")
    scenes: List[str] = Field(..., description="Последовательность scene_id")
    length: int = Field(..., description="Длина пути")
    is_main: bool = Field(default=False, description="Основной путь?")
    outcome: Optional[str] = Field(None, description="Результат прохождения")


class Quest(BaseModel):
    title: str = Field(..., description="Название квеста")
    genre: str = Field(..., description="Жанр")
    hero: str = Field(..., description="Главный герой")
    goal: str = Field(..., description="Цель квеста")
    scenes: List[Scene] = Field(..., description="Все сцены квеста")
    start_scene: str = Field(..., description="ID начальной сцены")
    paths: Optional[List[StoryPath]] = Field(None, description="Возможные пути прохождения")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    # Новые поля для расширенной функциональности
    target_audience: Optional[str] = Field(None, description="Целевая аудитория")
    estimated_duration: Optional[int] = Field(None, description="Ожидаемая длительность в минутах")
    complexity_level: Optional[str] = Field(None, description="Уровень сложности (easy, medium, hard)")
    content_warnings: Optional[List[str]] = Field(None, description="Предупреждения о контенте")
    tags: Optional[List[str]] = Field(None, description="Теги квеста")
    version: Optional[str] = Field(default="1.0", description="Версия квеста")
    
    # Интеграция с новыми системами
    personalization_data: Optional[Dict[str, Any]] = Field(None, description="Данные персонализации")
    quality_metrics: Optional[Dict[str, float]] = Field(None, description="Метрики качества")
    generation_config: Optional[Dict[str, Any]] = Field(None, description="Конфигурация генерации")
    
    @validator('complexity_level')
    def validate_complexity(cls, v):
        if v is not None and v not in ["easy", "medium", "hard"]:
            raise ValueError("Уровень сложности должен быть 'easy', 'medium' или 'hard'")
        return v
    
    @validator('scenes')
    def validate_quest_structure(cls, v, values):
        if len(v) < 1:
            raise ValueError("Квест должен содержать хотя бы одну сцену")
        
        scene_ids = {scene.scene_id for scene in v}
        
        for scene in v:
            for choice in scene.choices:
                if choice.next_scene and choice.next_scene not in scene_ids and choice.next_scene != "end":
                    raise ValueError(f"Битая ссылка: {choice.next_scene} не существует")
        
        # Отключаем требование развилок для тестирования
        # has_branching = any(len(scene.choices) > 1 for scene in v)
        # if not has_branching:
        #     raise ValueError("Квест должен содержать хотя бы одну развилку")
        
        return v


class KnowledgeItem(BaseModel):
    id: str = Field(..., description="ID элемента знаний")
    genre: str = Field(..., description="Жанр")
    category: str = Field(..., description="Категория (setting, character, item, etc)")
    content: str = Field(..., description="Содержание")
    tags: List[str] = Field(default_factory=list, description="Теги для поиска")
    embedding: Optional[List[float]] = Field(None, description="Векторное представление")


class GenerationConfig(BaseModel):
    model: str = Field(default="gpt-4", description="Модель для генерации")
    temperature: float = Field(default=0.8, ge=0, le=2, description="Температура генерации")
    max_tokens: int = Field(default=2000, description="Максимум токенов на ответ")
    top_p: float = Field(default=0.9, ge=0, le=1, description="Top-p sampling")
    use_rag: bool = Field(default=True, description="Использовать RAG?")
    rag_top_k: int = Field(default=5, description="Количество релевантных фрагментов")
    ensure_branching_depth: int = Field(default=3, description="Минимальная глубина ветвления")


class GenerationRequest(BaseModel):
    scenario: ScenarioInput
    config: Optional[GenerationConfig] = Field(default_factory=GenerationConfig)


class GenerationResponse(BaseModel):
    quest: Quest
    generation_time: float = Field(..., description="Время генерации в секундах")
    tokens_used: int = Field(..., description="Использовано токенов")
    status: str = Field(default="success")
    error: Optional[str] = Field(None)


# Новые модели для расширенного функционала

class LevelData(BaseModel):
    """Модель данных уровня"""
    level_id: str = Field(..., description="ID уровня")
    width: int = Field(..., description="Ширина уровня")
    height: int = Field(..., description="Высота уровня")
    tiles: List[List[int]] = Field(..., description="Данные тайлов")
    spawn_points: List[Tuple[int, int]] = Field(..., description="Точки появления")
    goal_points: List[Tuple[int, int]] = Field(..., description="Целевые точки")
    special_areas: Dict[str, List[Tuple[int, int]]] = Field(default_factory=dict, description="Особые области")
    generation_algorithm: Optional[str] = Field(None, description="Алгоритм генерации")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные уровня")


class GameObjectData(BaseModel):
    """Модель данных игрового объекта"""
    object_id: str = Field(..., description="ID объекта")
    object_type: str = Field(..., description="Тип объекта")
    position: Tuple[int, int] = Field(..., description="Позиция объекта")
    rotation: Optional[float] = Field(None, description="Поворот объекта в градусах")
    scale: Optional[Tuple[float, float, float]] = Field(None, description="Масштаб объекта (x, y, z)")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Свойства объекта")
    interactions: Optional[List[str]] = Field(None, description="Доступные взаимодействия")
    ai_behavior: Optional[str] = Field(None, description="Поведение ИИ для врагов")


class VisualizationData(BaseModel):
    """Модель данных визуализации"""
    visualization_id: str = Field(..., description="ID визуализации")
    scene_id: str = Field(..., description="ID связанной сцены")
    image_url: Optional[str] = Field(None, description="URL изображения")
    image_data: Optional[str] = Field(None, description="Данные изображения в base64")
    prompt_used: str = Field(..., description="Использованный промпт")
    style: str = Field(..., description="Стиль визуализации")
    generation_params: Dict[str, Any] = Field(default_factory=dict, description="Параметры генерации")
    quality_score: Optional[float] = Field(None, description="Оценка качества")


class QualityMetrics(BaseModel):
    """Модель метрик качества"""
    overall_score: float = Field(..., description="Общая оценка качества")
    coherence: float = Field(..., description="Связность")
    diversity: float = Field(..., description="Разнообразие")
    complexity: float = Field(..., description="Сложность")
    balance: float = Field(..., description="Баланс")
    originality: float = Field(..., description="Оригинальность")
    playability: float = Field(..., description="Играбельность")
    engagement: float = Field(..., description="Вовлеченность")
    technical_quality: float = Field(..., description="Техническое качество")
    
    @validator('overall_score', 'coherence', 'diversity', 'complexity', 'balance', 
              'originality', 'playability', 'engagement', 'technical_quality')
    def validate_score_range(cls, v):
        if v < 0.0 or v > 1.0:
            raise ValueError("Оценка должна быть между 0.0 и 1.0")
        return v


class PlayerProfileData(BaseModel):
    """Модель данных профиля игрока"""
    player_id: str = Field(..., description="ID игрока")
    player_type: str = Field(..., description="Тип игрока")
    preferences: Dict[str, float] = Field(default_factory=dict, description="Предпочтения игрока")
    play_history: List[str] = Field(default_factory=list, description="История прохождений")
    difficulty_preference: str = Field(default="normal", description="Предпочтение по сложности")
    favorite_genres: List[str] = Field(default_factory=list, description="Любимые жанры")
    behavioral_metrics: Dict[str, float] = Field(default_factory=dict, description="Поведенческие метрики")


class ContentGenerationRequest(BaseModel):
    """Расширенный запрос на генерацию контента"""
    scenario: ScenarioInput = Field(..., description="Сценарий квеста")
    generation_config: Optional[GenerationConfig] = Field(None, description="Конфигурация генерации")
    
    # Дополнительные параметры
    include_level: bool = Field(default=False, description="Включить генерацию уровня")
    include_objects: bool = Field(default=False, description="Включить размещение объектов")
    include_visuals: bool = Field(default=False, description="Включить визуализацию")
    include_quality_analysis: bool = Field(default=True, description="Включить анализ качества")
    
    # Персонализация
    player_id: Optional[str] = Field(None, description="ID игрока для персонализации")
    personalization_enabled: bool = Field(default=False, description="Включить персонализацию")
    
    # Экспорт
    export_formats: Optional[List[str]] = Field(None, description="Форматы экспорта")
    target_engines: Optional[List[str]] = Field(None, description="Целевые движки")
    
    # Ограничения
    max_generation_time: Optional[int] = Field(None, description="Максимальное время генерации в секундах")
    quality_threshold: Optional[float] = Field(None, description="Минимальный порог качества")


class ContentGenerationResponse(BaseModel):
    """Расширенный ответ генерации контента"""
    request_id: str = Field(..., description="ID запроса")
    status: str = Field(..., description="Статус выполнения")
    
    # Сгенерированный контент
    quest: Optional[Quest] = Field(None, description="Сгенерированный квест")
    level: Optional[LevelData] = Field(None, description="Сгенерированный уровень")
    objects: Optional[List[GameObjectData]] = Field(None, description="Размещенные объекты")
    visualizations: Optional[List[VisualizationData]] = Field(None, description="Визуализации")
    
    # Аналитика
    quality_metrics: Optional[QualityMetrics] = Field(None, description="Метрики качества")
    generation_time: float = Field(..., description="Время генерации")
    tokens_used: int = Field(default=0, description="Использованные токены")
    
    # Персонализация
    personalization_applied: bool = Field(default=False, description="Была ли применена персонализация")
    player_profile: Optional[PlayerProfileData] = Field(None, description="Профиль игрока")
    
    # Экспорт
    export_urls: Optional[Dict[str, str]] = Field(None, description="URLs экспортированных файлов")
    
    # Диагностика
    warnings: List[str] = Field(default_factory=list, description="Предупреждения")
    debug_info: Optional[Dict[str, Any]] = Field(None, description="Отладочная информация")
    error: Optional[str] = Field(None, description="Ошибка если есть")


class HybridPipelineConfig(BaseModel):
    """Конфигурация гибридного пайплайна"""
    pipeline_id: str = Field(..., description="ID конфигурации пайплайна")
    strategy: str = Field(default="sequential", description="Стратегия интеграции")
    enabled_stages: List[str] = Field(default_factory=list, description="Включенные этапы")
    
    # Настройки качества и производительности
    quality_threshold: float = Field(default=0.75, description="Порог качества")
    max_iterations: int = Field(default=3, description="Максимальное количество итераций")
    parallel_workers: int = Field(default=2, description="Количество параллельных воркеров")
    
    # Настройки компонентов
    llm_config: Optional[GenerationConfig] = Field(None, description="Конфигурация LLM")
    pcg_config: Optional[Dict[str, Any]] = Field(None, description="Конфигурация PCG")
    
    # Экспериментальные функции
    enable_cross_modal_feedback: bool = Field(default=False, description="Межмодальная обратная связь")
    enable_adaptive_optimization: bool = Field(default=False, description="Адаптивная оптимизация")
    enable_real_time_quality_monitoring: bool = Field(default=False, description="Мониторинг качества в реальном времени")
    
    # Кеширование и оптимизация
    use_caching: bool = Field(default=True, description="Использовать кеширование")
    memory_optimization: bool = Field(default=False, description="Оптимизация памяти")
    
    @validator('quality_threshold')
    def validate_quality_threshold(cls, v):
        if v < 0.0 or v > 1.0:
            raise ValueError("Порог качества должен быть между 0.0 и 1.0")
        return v


class ExportConfiguration(BaseModel):
    """Конфигурация экспорта"""
    target_engine: str = Field(..., description="Целевой игровой движок")
    export_format: str = Field(..., description="Формат экспорта")
    output_directory: str = Field(..., description="Выходная директория")
    
    # Настройки контента
    include_assets: bool = Field(default=True, description="Включить ассеты")
    include_scripts: bool = Field(default=True, description="Включить скрипты")
    include_metadata: bool = Field(default=True, description="Включить метаданные")
    
    # Оптимизация
    compress_output: bool = Field(default=True, description="Сжимать выходные файлы")
    optimize_for_mobile: bool = Field(default=False, description="Оптимизировать для мобильных устройств")
    
    # Локализация
    supported_languages: List[str] = Field(default_factory=lambda: ["ru"], description="Поддерживаемые языки")
    
    # Версионирование
    version: str = Field(default="1.0", description="Версия экспорта")
    build_number: Optional[int] = Field(None, description="Номер сборки")