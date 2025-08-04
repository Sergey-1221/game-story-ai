"""
Гибридный пайплайн генерации игрового контента, 
сочетающий LLM (Large Language Models) и PCG (Procedural Content Generation) методы
для создания комплексного игрового опыта
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import json
import numpy as np
from loguru import logger

from src.core.models import Quest, Scene, Choice, ScenarioInput, GenerationConfig
from src.modules.level_generator import LevelGenerator, GeneratedLevel, LevelConfig
from src.modules.object_placement import ObjectPlacementEngine, GameObject, ObjectType
from src.modules.diffusion_visualizer import DiffusionVisualizer, VisualizationConfig, GeneratedVisualization
from src.modules.narrative_enhancer import NarrativeEnhancer, EnhancementConfig, NarrativeAnalysis
from src.modules.personalization_engine import PersonalizationEngine, PlayerProfile
from src.modules.quality_metrics import QualityMetricsManager, QualityReport
from src.modules.game_engine_exporters import GameEngineExportManager, ExportConfig, GameEngine
from src.quest_generator import QuestGenerator


class PipelineStage(Enum):
    """Этапы гибридного пайплайна"""
    NARRATIVE_GENERATION = "narrative_generation"
    LEVEL_GENERATION = "level_generation"
    OBJECT_PLACEMENT = "object_placement"
    VISUAL_GENERATION = "visual_generation"
    NARRATIVE_ENHANCEMENT = "narrative_enhancement"
    PERSONALIZATION = "personalization"
    QUALITY_ASSESSMENT = "quality_assessment"
    EXPORT = "export"


class IntegrationStrategy(Enum):
    """Стратегии интеграции LLM и PCG"""
    SEQUENTIAL = "sequential"           # Последовательное выполнение
    PARALLEL = "parallel"               # Параллельное выполнение
    ITERATIVE = "iterative"            # Итеративное улучшение
    ADAPTIVE = "adaptive"              # Адаптивная стратегия
    COLLABORATIVE = "collaborative"    # Совместная генерация


@dataclass
class PipelineConfig:
    """Конфигурация гибридного пайплайна"""
    
    # Общие настройки
    integration_strategy: IntegrationStrategy = IntegrationStrategy.SEQUENTIAL
    enabled_stages: List[PipelineStage] = None
    max_iterations: int = 3
    quality_threshold: float = 0.75
    
    # Настройки компонентов
    generation_config: GenerationConfig = None
    level_config: LevelConfig = None
    visualization_config: VisualizationConfig = None
    enhancement_config: EnhancementConfig = None
    export_configs: List[ExportConfig] = None
    
    # Персонализация
    enable_personalization: bool = False
    player_id: Optional[str] = None
    
    # Оптимизация производительности
    use_caching: bool = True
    parallel_workers: int = 2
    memory_optimization: bool = True
    
    # Экспериментальные функции
    enable_cross_modal_feedback: bool = False
    enable_multi_objective_optimization: bool = False
    
    def __post_init__(self):
        if self.enabled_stages is None:
            self.enabled_stages = [
                PipelineStage.NARRATIVE_GENERATION,
                PipelineStage.LEVEL_GENERATION,
                PipelineStage.OBJECT_PLACEMENT,
                PipelineStage.QUALITY_ASSESSMENT
            ]
        
        if self.generation_config is None:
            self.generation_config = GenerationConfig()
        
        if self.level_config is None:
            self.level_config = LevelConfig()


@dataclass
class PipelineResult:
    """Результат работы гибридного пайплайна"""
    quest: Quest
    level: Optional[GeneratedLevel] = None
    objects: Optional[List[GameObject]] = None
    visualizations: Optional[List[GeneratedVisualization]] = None
    quality_report: Optional[QualityReport] = None
    narrative_analysis: Optional[NarrativeAnalysis] = None
    
    # Метаданные процесса
    generation_time: float = 0.0
    stages_completed: List[PipelineStage] = None
    iterations_performed: int = 0
    final_quality_score: float = 0.0
    
    # Диагностическая информация
    stage_timings: Dict[PipelineStage, float] = None
    memory_usage: Dict[str, float] = None
    optimization_log: List[str] = None
    
    def __post_init__(self):
        if self.stages_completed is None:
            self.stages_completed = []
        if self.stage_timings is None:
            self.stage_timings = {}
        if self.memory_usage is None:
            self.memory_usage = {}
        if self.optimization_log is None:
            self.optimization_log = []


class CrossModalFeedbackSystem:
    """Система межмодальной обратной связи между компонентами"""
    
    def __init__(self):
        self.feedback_cache = {}
    
    def generate_level_feedback_for_narrative(self, level: GeneratedLevel, quest: Quest) -> Dict[str, Any]:
        """Генерация обратной связи от уровня к нарративу"""
        
        feedback = {
            "spatial_constraints": [],
            "narrative_opportunities": [],
            "pacing_suggestions": []
        }
        
        # Анализируем пространственные ограничения
        if level.width * level.height < 500:  # Маленький уровень
            feedback["spatial_constraints"].append("compact_narrative")
            feedback["pacing_suggestions"].append("faster_pacing")
        
        # Ищем возможности для нарратива на основе особых областей
        for area_type, positions in level.special_areas.items():
            if area_type == "secret" and len(positions) > 0:
                feedback["narrative_opportunities"].append("hidden_story_elements")
            elif area_type == "trap" and len(positions) > 2:
                feedback["narrative_opportunities"].append("danger_escalation")
        
        # Анализируем пути между спавном и целями
        if len(level.spawn_points) > 1:
            feedback["narrative_opportunities"].append("multiple_entry_points")
        
        return feedback
    
    def generate_narrative_feedback_for_level(self, quest: Quest) -> Dict[str, Any]:
        """Генерация обратной связи от нарратива к уровню"""
        
        feedback = {
            "required_areas": [],
            "atmosphere_requirements": [],
            "layout_preferences": []
        }
        
        # Анализируем сцены для определения требований к уровню
        for scene in quest.scenes:
            # Анализируем локации
            if scene.location:
                if "лаборатория" in scene.location.lower():
                    feedback["required_areas"].append("tech_area")
                elif "коридор" in scene.location.lower():
                    feedback["layout_preferences"].append("corridor_heavy")
                elif "комната" in scene.location.lower():
                    feedback["required_areas"].append("room_based")
            
            # Анализируем настроение
            if scene.mood:
                if "напряженная" in scene.mood.lower():
                    feedback["atmosphere_requirements"].append("tight_spaces")
                elif "таинственная" in scene.mood.lower():
                    feedback["atmosphere_requirements"].append("hidden_areas")
        
        # Анализируем выборы для определения требований к навигации
        complex_choices = sum(1 for scene in quest.scenes for choice in scene.choices 
                            if "исследовать" in choice.text.lower() or "поискать" in choice.text.lower())
        
        if complex_choices > len(quest.scenes) * 0.3:  # Более 30% исследовательских выборов
            feedback["layout_preferences"].append("exploration_friendly")
        
        return feedback
    
    def generate_visual_feedback_for_narrative(self, visualizations: List[GeneratedVisualization], 
                                             quest: Quest) -> Dict[str, Any]:
        """Генерация обратной связи от визуализации к нарративу"""
        
        feedback = {
            "visual_consistency": [],
            "narrative_enhancements": [],
            "style_adaptations": []
        }
        
        if not visualizations:
            return feedback
        
        # Анализируем визуальную консистентность
        visual_styles = [viz.metadata.get("style", "unknown") for viz in visualizations]
        if len(set(visual_styles)) > 1:
            feedback["visual_consistency"].append("mixed_styles_detected")
        
        # Предлагаем улучшения нарратива на основе визуализации
        for viz in visualizations:
            if viz.metadata.get("error"):
                feedback["narrative_enhancements"].append("simplify_visual_descriptions")
            elif "dramatic" in viz.prompt.lower():
                feedback["narrative_enhancements"].append("enhance_drama")
        
        return feedback


class AdaptiveOptimizer:
    """Адаптивный оптимизатор для гибридного пайплайна"""
    
    def __init__(self):
        self.performance_history = []
        self.optimization_strategies = {
            "memory": self._optimize_memory_usage,
            "speed": self._optimize_generation_speed,
            "quality": self._optimize_quality
        }
    
    def optimize_pipeline_config(self, config: PipelineConfig, 
                                performance_metrics: Dict[str, float]) -> PipelineConfig:
        """Оптимизация конфигурации пайплайна"""
        
        optimized_config = config
        
        # Записываем метрики производительности
        self.performance_history.append(performance_metrics)
        
        # Если недостаточно памяти
        if performance_metrics.get("memory_usage", 0) > 0.8:
            optimized_config = self._optimize_memory_usage(optimized_config)
        
        # Если генерация слишком медленная
        if performance_metrics.get("generation_time", 0) > 300:  # 5 минут
            optimized_config = self._optimize_generation_speed(optimized_config)
        
        # Если качество ниже порога
        if performance_metrics.get("quality_score", 1.0) < config.quality_threshold:
            optimized_config = self._optimize_quality(optimized_config)
        
        return optimized_config
    
    def _optimize_memory_usage(self, config: PipelineConfig) -> PipelineConfig:
        """Оптимизация использования памяти"""
        
        config.memory_optimization = True
        config.parallel_workers = max(1, config.parallel_workers - 1)
        
        # Отключаем ресурсоемкие этапы если необходимо
        if PipelineStage.VISUAL_GENERATION in config.enabled_stages:
            if len(config.enabled_stages) > 3:
                config.enabled_stages.remove(PipelineStage.VISUAL_GENERATION)
        
        return config
    
    def _optimize_generation_speed(self, config: PipelineConfig) -> PipelineConfig:
        """Оптимизация скорости генерации"""
        
        # Увеличиваем параллелизм
        config.parallel_workers = min(4, config.parallel_workers + 1)
        
        # Уменьшаем количество итераций
        config.max_iterations = max(1, config.max_iterations - 1)
        
        # Снижаем качественные требования для ускорения
        if config.generation_config:
            config.generation_config.max_tokens = min(1500, config.generation_config.max_tokens)
        
        return config
    
    def _optimize_quality(self, config: PipelineConfig) -> PipelineConfig:
        """Оптимизация качества"""
        
        # Включаем улучшение нарратива
        if PipelineStage.NARRATIVE_ENHANCEMENT not in config.enabled_stages:
            config.enabled_stages.append(PipelineStage.NARRATIVE_ENHANCEMENT)
        
        # Увеличиваем количество итераций
        config.max_iterations = min(5, config.max_iterations + 1)
        
        # Повышаем настройки качества для LLM
        if config.generation_config:
            config.generation_config.temperature = max(0.1, config.generation_config.temperature - 0.1)
        
        return config


class HybridContentPipeline:
    """Главный класс гибридного пайплайна генерации контента"""
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        
        # Инициализируем компоненты
        self.quest_generator = QuestGenerator(self.config.generation_config)
        self.level_generator = LevelGenerator()
        self.object_placement_engine = ObjectPlacementEngine()
        self.diffusion_visualizer = DiffusionVisualizer(self.config.visualization_config)
        self.narrative_enhancer = NarrativeEnhancer(self.config.enhancement_config)
        self.personalization_engine = PersonalizationEngine()
        self.quality_metrics_manager = QualityMetricsManager()
        self.export_manager = GameEngineExportManager()
        
        # Системы обратной связи и оптимизации
        self.feedback_system = CrossModalFeedbackSystem()
        self.adaptive_optimizer = AdaptiveOptimizer()
        
        # Кеш для оптимизации
        self.component_cache = {}
        
        logger.info("Гибридный пайплайн инициализирован")
    
    async def generate_content(self, scenario: ScenarioInput) -> PipelineResult:
        """Основной метод генерации контента"""
        
        start_time = time.time()
        result = PipelineResult()
        
        logger.info(f"Запускаем генерацию контента: {self.config.integration_strategy.value}")
        
        try:
            # Выбираем стратегию интеграции
            if self.config.integration_strategy == IntegrationStrategy.SEQUENTIAL:
                result = await self._sequential_generation(scenario, result)
            elif self.config.integration_strategy == IntegrationStrategy.PARALLEL:
                result = await self._parallel_generation(scenario, result)
            elif self.config.integration_strategy == IntegrationStrategy.ITERATIVE:
                result = await self._iterative_generation(scenario, result)
            elif self.config.integration_strategy == IntegrationStrategy.ADAPTIVE:
                result = await self._adaptive_generation(scenario, result)
            else:
                result = await self._collaborative_generation(scenario, result)
            
            # Финализируем результат
            result.generation_time = time.time() - start_time
            result.final_quality_score = result.quality_report.overall_score if result.quality_report else 0.0
            
            logger.info(f"Генерация завершена за {result.generation_time:.2f}с, качество: {result.final_quality_score:.2f}")
            
        except Exception as e:
            logger.error(f"Ошибка в пайплайне генерации: {e}")
            result.optimization_log.append(f"ERROR: {str(e)}")
        
        return result
    
    async def _sequential_generation(self, scenario: ScenarioInput, result: PipelineResult) -> PipelineResult:
        """Последовательная генерация контента"""
        
        # Этап 1: Генерация нарратива
        if PipelineStage.NARRATIVE_GENERATION in self.config.enabled_stages:
            result = await self._execute_narrative_generation(scenario, result)
        
        # Этап 2: Генерация уровня
        if PipelineStage.LEVEL_GENERATION in self.config.enabled_stages:
            result = await self._execute_level_generation(scenario, result)
        
        # Этап 3: Размещение объектов
        if PipelineStage.OBJECT_PLACEMENT in self.config.enabled_stages:
            result = await self._execute_object_placement(scenario, result)
        
        # Этап 4: Визуализация
        if PipelineStage.VISUAL_GENERATION in self.config.enabled_stages:
            result = await self._execute_visual_generation(scenario, result)
        
        # Этап 5: Улучшение нарратива
        if PipelineStage.NARRATIVE_ENHANCEMENT in self.config.enabled_stages:
            result = await self._execute_narrative_enhancement(scenario, result)
        
        # Этап 6: Персонализация
        if PipelineStage.PERSONALIZATION in self.config.enabled_stages:
            result = await self._execute_personalization(scenario, result)
        
        # Этап 7: Оценка качества
        if PipelineStage.QUALITY_ASSESSMENT in self.config.enabled_stages:
            result = await self._execute_quality_assessment(scenario, result)
        
        # Этап 8: Экспорт
        if PipelineStage.EXPORT in self.config.enabled_stages:
            result = await self._execute_export(scenario, result)
        
        return result
    
    async def _parallel_generation(self, scenario: ScenarioInput, result: PipelineResult) -> PipelineResult:
        """Параллельная генерация контента"""
        
        # Сначала генерируем нарратив (базовый компонент)
        if PipelineStage.NARRATIVE_GENERATION in self.config.enabled_stages:
            result = await self._execute_narrative_generation(scenario, result)
        
        # Параллельно запускаем независимые компоненты
        parallel_tasks = []
        
        if PipelineStage.LEVEL_GENERATION in self.config.enabled_stages:
            parallel_tasks.append(self._execute_level_generation_async(scenario, result))
        
        if PipelineStage.VISUAL_GENERATION in self.config.enabled_stages and result.quest:
            parallel_tasks.append(self._execute_visual_generation_async(scenario, result))
        
        # Ждем завершения параллельных задач
        if parallel_tasks:
            parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
            
            # Интегрируем результаты
            for i, task_result in enumerate(parallel_results):
                if isinstance(task_result, Exception):
                    logger.error(f"Ошибка в параллельной задаче {i}: {task_result}")
                else:
                    result = self._merge_parallel_results(result, task_result)
        
        # Последовательно выполняем зависимые этапы
        if PipelineStage.OBJECT_PLACEMENT in self.config.enabled_stages and result.level:
            result = await self._execute_object_placement(scenario, result)
        
        if PipelineStage.QUALITY_ASSESSMENT in self.config.enabled_stages:
            result = await self._execute_quality_assessment(scenario, result)
        
        return result
    
    async def _iterative_generation(self, scenario: ScenarioInput, result: PipelineResult) -> PipelineResult:
        """Итеративная генерация с улучшением"""
        
        best_result = None
        best_quality = 0.0
        
        for iteration in range(self.config.max_iterations):
            logger.info(f"Итерация {iteration + 1}/{self.config.max_iterations}")
            
            iteration_result = PipelineResult()
            
            # Выполняем основные этапы
            iteration_result = await self._sequential_generation(scenario, iteration_result)
            
            # Оцениваем качество
            if iteration_result.quality_report:
                quality_score = iteration_result.quality_report.overall_score
                
                if quality_score > best_quality:
                    best_result = iteration_result
                    best_quality = quality_score
                
                # Если достигли порога качества, завершаем
                if quality_score >= self.config.quality_threshold:
                    logger.info(f"Достигнут порог качества на итерации {iteration + 1}")
                    break
            
            # Адаптируем конфигурацию для следующей итерации
            if iteration < self.config.max_iterations - 1:
                self._adapt_config_for_next_iteration(iteration_result)
        
        result = best_result or result
        result.iterations_performed = iteration + 1
        
        return result
    
    async def _adaptive_generation(self, scenario: ScenarioInput, result: PipelineResult) -> PipelineResult:
        """Адаптивная генерация с динамической оптимизацией"""
        
        # Начинаем с базовой генерации
        result = await self._sequential_generation(scenario, result)
        
        # Анализируем производительность
        performance_metrics = {
            "generation_time": result.generation_time,
            "quality_score": result.quality_report.overall_score if result.quality_report else 0.0,
            "memory_usage": self._estimate_memory_usage(result)
        }
        
        # Оптимизируем конфигурацию
        optimized_config = self.adaptive_optimizer.optimize_pipeline_config(
            self.config, performance_metrics
        )
        
        # Если конфигурация изменилась, запускаем повторную генерацию
        if optimized_config != self.config:
            logger.info("Применяем оптимизированную конфигурацию")
            self.config = optimized_config
            
            # Повторная генерация с оптимизированными настройками
            result = await self._sequential_generation(scenario, result)
        
        return result
    
    async def _collaborative_generation(self, scenario: ScenarioInput, result: PipelineResult) -> PipelineResult:
        """Совместная генерация с межкомпонентной обратной связью"""
        
        # Этап 1: Базовая генерация нарратива
        result = await self._execute_narrative_generation(scenario, result)
        
        # Этап 2: Генерация уровня с учетом нарратива
        if PipelineStage.LEVEL_GENERATION in self.config.enabled_stages:
            narrative_feedback = self.feedback_system.generate_narrative_feedback_for_level(result.quest)
            result = await self._execute_level_generation_with_feedback(scenario, result, narrative_feedback)
        
        # Этап 3: Адаптация нарратива к уровню
        if result.level and self.config.enable_cross_modal_feedback:
            level_feedback = self.feedback_system.generate_level_feedback_for_narrative(result.level, result.quest)
            result = await self._adapt_narrative_to_level(scenario, result, level_feedback)
        
        # Этап 4: Размещение объектов с учетом нарратива и уровня
        if PipelineStage.OBJECT_PLACEMENT in self.config.enabled_stages and result.level:
            result = await self._execute_object_placement(scenario, result)
        
        # Этап 5: Визуализация с обратной связью
        if PipelineStage.VISUAL_GENERATION in self.config.enabled_stages:
            result = await self._execute_visual_generation(scenario, result)
            
            if self.config.enable_cross_modal_feedback and result.visualizations:
                visual_feedback = self.feedback_system.generate_visual_feedback_for_narrative(
                    result.visualizations, result.quest
                )
                result = await self._refine_content_with_visual_feedback(scenario, result, visual_feedback)
        
        # Финальная оценка качества
        if PipelineStage.QUALITY_ASSESSMENT in self.config.enabled_stages:
            result = await self._execute_quality_assessment(scenario, result)
        
        return result
    
    async def _execute_narrative_generation(self, scenario: ScenarioInput, result: PipelineResult) -> PipelineResult:
        """Выполнение генерации нарратива"""
        
        stage_start = time.time()
        
        try:
            logger.info("Генерируем нарратив")
            
            # Генерируем квест
            quest = await self.quest_generator.generate_async(scenario)
            result.quest = quest
            result.stages_completed.append(PipelineStage.NARRATIVE_GENERATION)
            
            logger.info(f"Сгенерирован квест с {len(quest.scenes)} сценами")
            
        except Exception as e:
            logger.error(f"Ошибка генерации нарратива: {e}")
            result.optimization_log.append(f"Narrative generation failed: {str(e)}")
        
        result.stage_timings[PipelineStage.NARRATIVE_GENERATION] = time.time() - stage_start
        return result
    
    async def _execute_level_generation(self, scenario: ScenarioInput, result: PipelineResult) -> PipelineResult:
        """Выполнение генерации уровня"""
        
        stage_start = time.time()
        
        try:
            logger.info("Генерируем уровень")
            
            # Адаптируем конфигурацию уровня под сценарий
            level_config = self._adapt_level_config_to_scenario(scenario)
            
            # Генерируем уровень
            level = self.level_generator.generate_level(scenario, level_config)
            result.level = level
            result.stages_completed.append(PipelineStage.LEVEL_GENERATION)
            
            logger.info(f"Сгенерирован уровень {level.width}x{level.height}")
            
        except Exception as e:
            logger.error(f"Ошибка генерации уровня: {e}")
            result.optimization_log.append(f"Level generation failed: {str(e)}")
        
        result.stage_timings[PipelineStage.LEVEL_GENERATION] = time.time() - stage_start
        return result
    
    async def _execute_object_placement(self, scenario: ScenarioInput, result: PipelineResult) -> PipelineResult:
        """Выполнение размещения объектов"""
        
        stage_start = time.time()
        
        try:
            if not result.level:
                logger.warning("Нет уровня для размещения объектов")
                return result
            
            logger.info("Размещаем объекты")
            
            # Размещаем объекты
            objects = self.object_placement_engine.place_objects(result.level, scenario)
            result.objects = objects
            result.stages_completed.append(PipelineStage.OBJECT_PLACEMENT)
            
            logger.info(f"Размещено {len(objects)} объектов")
            
        except Exception as e:
            logger.error(f"Ошибка размещения объектов: {e}")
            result.optimization_log.append(f"Object placement failed: {str(e)}")
        
        result.stage_timings[PipelineStage.OBJECT_PLACEMENT] = time.time() - stage_start
        return result
    
    async def _execute_visual_generation(self, scenario: ScenarioInput, result: PipelineResult) -> PipelineResult:
        """Выполнение визуальной генерации"""
        
        stage_start = time.time()
        
        try:
            if not result.quest:
                logger.warning("Нет квеста для визуализации")
                return result
            
            logger.info("Генерируем визуализации")
            
            # Генерируем визуализации для ключевых сцен
            key_scenes = result.quest.scenes[:3]  # Первые 3 сцены
            visualizations = []
            
            for scene in key_scenes:
                try:
                    visualization = await self.diffusion_visualizer.generate_scene_visualization(
                        scene, scenario, result.level
                    )
                    visualizations.append(visualization)
                except Exception as e:
                    logger.warning(f"Не удалось создать визуализацию для сцены {scene.scene_id}: {e}")
            
            result.visualizations = visualizations
            result.stages_completed.append(PipelineStage.VISUAL_GENERATION)
            
            logger.info(f"Создано {len(visualizations)} визуализаций")
            
        except Exception as e:
            logger.error(f"Ошибка визуальной генерации: {e}")
            result.optimization_log.append(f"Visual generation failed: {str(e)}")
        
        result.stage_timings[PipelineStage.VISUAL_GENERATION] = time.time() - stage_start
        return result
    
    async def _execute_narrative_enhancement(self, scenario: ScenarioInput, result: PipelineResult) -> PipelineResult:
        """Выполнение улучшения нарратива"""
        
        stage_start = time.time()
        
        try:
            if not result.quest:
                logger.warning("Нет квеста для улучшения")
                return result
            
            logger.info("Улучшаем нарратив")
            
            # Улучшаем квест
            enhanced_quest, narrative_analysis = await self.narrative_enhancer.enhance_quest_narrative(
                result.quest, scenario, self.config.generation_config
            )
            
            result.quest = enhanced_quest
            result.narrative_analysis = narrative_analysis
            result.stages_completed.append(PipelineStage.NARRATIVE_ENHANCEMENT)
            
            logger.info(f"Нарратив улучшен, итоговое качество: {narrative_analysis.overall_quality:.2f}")
            
        except Exception as e:
            logger.error(f"Ошибка улучшения нарратива: {e}")
            result.optimization_log.append(f"Narrative enhancement failed: {str(e)}")
        
        result.stage_timings[PipelineStage.NARRATIVE_ENHANCEMENT] = time.time() - stage_start
        return result
    
    async def _execute_personalization(self, scenario: ScenarioInput, result: PipelineResult) -> PipelineResult:
        """Выполнение персонализации"""
        
        stage_start = time.time()
        
        try:
            if not result.quest or not self.config.player_id:
                logger.info("Пропускаем персонализацию")
                return result
            
            logger.info("Персонализируем контент")
            
            # Персонализируем квест
            personalized_quest = self.personalization_engine.personalize_quest(
                result.quest, self.config.player_id
            )
            
            result.quest = personalized_quest
            result.stages_completed.append(PipelineStage.PERSONALIZATION)
            
            logger.info("Контент персонализирован")
            
        except Exception as e:
            logger.error(f"Ошибка персонализации: {e}")
            result.optimization_log.append(f"Personalization failed: {str(e)}")
        
        result.stage_timings[PipelineStage.PERSONALIZATION] = time.time() - stage_start
        return result
    
    async def _execute_quality_assessment(self, scenario: ScenarioInput, result: PipelineResult) -> PipelineResult:
        """Выполнение оценки качества"""
        
        stage_start = time.time()
        
        try:
            if not result.quest:
                logger.warning("Нет контента для оценки качества")
                return result
            
            logger.info("Оцениваем качество")
            
            # Оцениваем качество квеста
            quality_report = self.quality_metrics_manager.evaluate_quest(result.quest)
            result.quality_report = quality_report
            result.stages_completed.append(PipelineStage.QUALITY_ASSESSMENT)
            
            logger.info(f"Оценка качества завершена: {quality_report.overall_score:.2f}")
            
        except Exception as e:
            logger.error(f"Ошибка оценки качества: {e}")
            result.optimization_log.append(f"Quality assessment failed: {str(e)}")
        
        result.stage_timings[PipelineStage.QUALITY_ASSESSMENT] = time.time() - stage_start
        return result
    
    async def _execute_export(self, scenario: ScenarioInput, result: PipelineResult) -> PipelineResult:
        """Выполнение экспорта"""
        
        stage_start = time.time()
        
        try:
            if not result.quest or not self.config.export_configs:
                logger.info("Пропускаем экспорт")
                return result
            
            logger.info("Экспортируем контент")
            
            # Экспортируем в каждый указанный движок
            for export_config in self.config.export_configs:
                try:
                    self.export_manager.export_quest(
                        result.quest, export_config, result.level, result.objects
                    )
                    logger.info(f"Экспорт в {export_config.target_engine.value} завершен")
                except Exception as e:
                    logger.error(f"Ошибка экспорта в {export_config.target_engine.value}: {e}")
            
            result.stages_completed.append(PipelineStage.EXPORT)
            
        except Exception as e:
            logger.error(f"Ошибка экспорта: {e}")
            result.optimization_log.append(f"Export failed: {str(e)}")
        
        result.stage_timings[PipelineStage.EXPORT] = time.time() - stage_start
        return result
    
    async def _execute_level_generation_async(self, scenario: ScenarioInput, result: PipelineResult) -> Dict[str, Any]:
        """Асинхронная генерация уровня для параллельного выполнения"""
        try:
            level_config = self._adapt_level_config_to_scenario(scenario)
            level = self.level_generator.generate_level(scenario, level_config)
            return {"level": level, "stage": PipelineStage.LEVEL_GENERATION}
        except Exception as e:
            return {"error": str(e), "stage": PipelineStage.LEVEL_GENERATION}
    
    async def _execute_visual_generation_async(self, scenario: ScenarioInput, result: PipelineResult) -> Dict[str, Any]:
        """Асинхронная визуальная генерация для параллельного выполнения"""
        try:
            if not result.quest:
                return {"error": "No quest for visualization", "stage": PipelineStage.VISUAL_GENERATION}
            
            key_scenes = result.quest.scenes[:2]  # Ограничиваем для параллельной обработки
            visualizations = []
            
            for scene in key_scenes:
                try:
                    visualization = await self.diffusion_visualizer.generate_scene_visualization(
                        scene, scenario, result.level
                    )
                    visualizations.append(visualization)
                except Exception as e:
                    logger.warning(f"Failed to create visualization for scene {scene.scene_id}: {e}")
            
            return {"visualizations": visualizations, "stage": PipelineStage.VISUAL_GENERATION}
        except Exception as e:
            return {"error": str(e), "stage": PipelineStage.VISUAL_GENERATION}
    
    def _merge_parallel_results(self, main_result: PipelineResult, parallel_result: Dict[str, Any]) -> PipelineResult:
        """Объединение результатов параллельной обработки"""
        
        if "error" in parallel_result:
            main_result.optimization_log.append(f"Parallel task error: {parallel_result['error']}")
            return main_result
        
        stage = parallel_result["stage"]
        
        if stage == PipelineStage.LEVEL_GENERATION and "level" in parallel_result:
            main_result.level = parallel_result["level"]
            main_result.stages_completed.append(stage)
        
        elif stage == PipelineStage.VISUAL_GENERATION and "visualizations" in parallel_result:
            main_result.visualizations = parallel_result["visualizations"]
            main_result.stages_completed.append(stage)
        
        return main_result
    
    def _adapt_level_config_to_scenario(self, scenario: ScenarioInput) -> LevelConfig:
        """Адаптация конфигурации уровня под сценарий"""
        
        level_config = self.config.level_config or LevelConfig()
        
        # Адаптируем размер уровня в зависимости от жанра
        if scenario.genre.lower() == "киберпанк":
            level_config.algorithm = "cellular"
            level_config.wall_probability = 0.3
        elif scenario.genre.lower() == "фэнтези":
            level_config.algorithm = "maze"
            level_config.room_count = 6
        elif scenario.genre.lower() == "хоррор":
            level_config.algorithm = "wfc"
            level_config.corridor_width = 1
        
        return level_config
    
    def _adapt_config_for_next_iteration(self, current_result: PipelineResult):
        """Адаптация конфигурации для следующей итерации"""
        
        if current_result.quality_report:
            quality_score = current_result.quality_report.overall_score
            
            # Если качество низкое, усиливаем настройки
            if quality_score < 0.6:
                if self.config.generation_config:
                    self.config.generation_config.temperature = max(0.1, 
                        self.config.generation_config.temperature - 0.1)
                
                # Включаем улучшение нарратива
                if PipelineStage.NARRATIVE_ENHANCEMENT not in self.config.enabled_stages:
                    self.config.enabled_stages.append(PipelineStage.NARRATIVE_ENHANCEMENT)
    
    def _estimate_memory_usage(self, result: PipelineResult) -> float:
        """Приблизительная оценка использования памяти"""
        
        memory_usage = 0.1  # Базовое использование
        
        if result.quest:
            # Приблизительно на основе количества сцен и текста
            text_size = sum(len(scene.text) for scene in result.quest.scenes)
            memory_usage += text_size / 1000000  # МБ
        
        if result.level:
            # Размер уровня
            memory_usage += (result.level.width * result.level.height) / 100000
        
        if result.visualizations:
            # Визуализации потребляют много памяти
            memory_usage += len(result.visualizations) * 50  # ~50 МБ на изображение
        
        return min(memory_usage, 1.0)  # Нормализуем к [0, 1]
    
    def export_pipeline_result(self, result: PipelineResult, output_path: str):
        """Экспорт результата пайплайна"""
        
        export_data = {
            "quest": result.quest.dict() if result.quest else None,
            "level_metadata": result.level.metadata if result.level else None,
            "objects_count": len(result.objects) if result.objects else 0,
            "visualizations_count": len(result.visualizations) if result.visualizations else 0,
            "quality_report": asdict(result.quality_report) if result.quality_report else None,
            "narrative_analysis": asdict(result.narrative_analysis) if result.narrative_analysis else None,
            "performance_metrics": {
                "generation_time": result.generation_time,
                "iterations_performed": result.iterations_performed,
                "final_quality_score": result.final_quality_score,
                "stages_completed": [stage.value for stage in result.stages_completed],
                "stage_timings": {stage.value: timing for stage, timing in result.stage_timings.items()},
                "memory_usage": result.memory_usage,
                "optimization_log": result.optimization_log
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"Результат пайплайна экспортирован в: {output_path}")
    
    def get_pipeline_statistics(self) -> Dict[str, Any]:
        """Получение статистики работы пайплайна"""
        
        return {
            "config": asdict(self.config),
            "components_initialized": {
                "quest_generator": self.quest_generator is not None,
                "level_generator": self.level_generator is not None,
                "object_placement_engine": self.object_placement_engine is not None,
                "diffusion_visualizer": self.diffusion_visualizer is not None,
                "narrative_enhancer": self.narrative_enhancer is not None,
                "personalization_engine": self.personalization_engine is not None,
                "quality_metrics_manager": self.quality_metrics_manager is not None,
                "export_manager": self.export_manager is not None
            },
            "cache_size": len(self.component_cache),
            "performance_history": len(self.adaptive_optimizer.performance_history)
        }


# Пример использования и тестирования
async def main():
    """Пример использования гибридного пайплайна"""
    
    # Настройка конфигурации
    config = PipelineConfig(
        integration_strategy=IntegrationStrategy.COLLABORATIVE,
        enabled_stages=[
            PipelineStage.NARRATIVE_GENERATION,
            PipelineStage.LEVEL_GENERATION,
            PipelineStage.OBJECT_PLACEMENT,
            PipelineStage.QUALITY_ASSESSMENT
        ],
        quality_threshold=0.7,
        enable_personalization=False,
        enable_cross_modal_feedback=True
    )
    
    # Создание пайплайна
    pipeline = HybridContentPipeline(config)
    
    # Сценарий для генерации
    scenario = ScenarioInput(
        genre="киберпанк",
        hero="хакер-одиночка",
        goal="взломать корпоративный сервер и получить секретные данные"
    )
    
    # Запуск генерации
    result = await pipeline.generate_content(scenario)
    
    # Анализ результатов
    print(f"Генерация завершена за {result.generation_time:.2f} секунд")
    print(f"Качество: {result.final_quality_score:.2f}")
    print(f"Выполнено этапов: {len(result.stages_completed)}")
    print(f"Итераций: {result.iterations_performed}")
    
    if result.quest:
        print(f"Сгенерировано сцен: {len(result.quest.scenes)}")
    
    if result.level:
        print(f"Размер уровня: {result.level.width}x{result.level.height}")
    
    if result.objects:
        print(f"Размещено объектов: {len(result.objects)}")
    
    # Экспорт результатов
    pipeline.export_pipeline_result(result, "pipeline_result.json")


if __name__ == "__main__":
    asyncio.run(main())