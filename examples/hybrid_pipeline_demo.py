"""
Демонстрация работы гибридного пайплайна генерации игрового контента
с интеграцией всех новых AI и PCG компонентов
"""

import asyncio
import time
from pathlib import Path
import sys

# Добавляем путь к модулям проекта
sys.path.append(str(Path(__file__).parent.parent))

from src.core.models import (
    ScenarioInput, ContentGenerationRequest, GenerationConfig
)
from src.modules.hybrid_pipeline import (
    HybridContentPipeline, PipelineConfig, IntegrationStrategy, PipelineStage
)
from src.modules.level_generator import LevelConfig
from src.modules.diffusion_visualizer import VisualizationConfig, VisualizationStyle
from src.modules.narrative_enhancer import EnhancementConfig
from src.modules.game_engine_exporters import ExportConfig, GameEngine


async def demo_sequential_pipeline():
    """Демонстрация последовательного пайплайна"""
    
    print("=== ДЕМОНСТРАЦИЯ ПОСЛЕДОВАТЕЛЬНОГО ПАЙПЛАЙНА ===\n")
    
    # Конфигурация пайплайна
    config = PipelineConfig(
        integration_strategy=IntegrationStrategy.SEQUENTIAL,
        enabled_stages=[
            PipelineStage.NARRATIVE_GENERATION,
            PipelineStage.LEVEL_GENERATION,
            PipelineStage.OBJECT_PLACEMENT,
            PipelineStage.QUALITY_ASSESSMENT
        ],
        quality_threshold=0.7,
        max_iterations=2,
        
        # Конфигурации компонентов
        generation_config=GenerationConfig(
            model="gpt-4",
            temperature=0.8,
            max_tokens=1500,
            use_rag=True
        ),
        
        level_config=LevelConfig(
            width=24,
            height=24,
            algorithm="hybrid",
            seed=42
        )
    )
    
    # Создаем пайплайн
    pipeline = HybridContentPipeline(config)
    
    # Сценарий для генерации
    scenario = ScenarioInput(
        genre="киберпанк",
        hero="опытный хакер-наемник с кибернетическими имплантами",
        goal="проникнуть в защищенный корпоративный дата-центр и украсть секретные исследования по ИИ"
    )
    
    print(f"Сценарий: {scenario.genre}")
    print(f"Герой: {scenario.hero}")
    print(f"Цель: {scenario.goal}\n")
    
    # Запускаем генерацию
    start_time = time.time()
    result = await pipeline.generate_content(scenario)
    total_time = time.time() - start_time
    
    # Выводим результаты
    print(f"✅ Генерация завершена за {total_time:.2f} секунд")
    print(f"📊 Итоговое качество: {result.final_quality_score:.2f}")
    print(f"🔄 Выполнено этапов: {len(result.stages_completed)}")
    print(f"⚡ Итераций: {result.iterations_performed}\n")
    
    if result.quest:
        print(f"📖 Квест: '{result.quest.title}'")
        print(f"   Сцен: {len(result.quest.scenes)}")
        print(f"   Выборов: {sum(len(scene.choices) for scene in result.quest.scenes)}")
    
    if result.level:
        print(f"🗺️  Уровень: {result.level.width}x{result.level.height}")
        print(f"   Алгоритм: {result.level.metadata.get('algorithm', 'Unknown')}")
        print(f"   Точки спавна: {len(result.level.spawn_points)}")
        print(f"   Целевые точки: {len(result.level.goal_points)}")
    
    if result.objects:
        print(f"🎯 Объектов размещено: {len(result.objects)}")
        object_types = {}
        for obj in result.objects:
            obj_type = obj.object_type.value
            object_types[obj_type] = object_types.get(obj_type, 0) + 1
        
        for obj_type, count in object_types.items():
            print(f"   {obj_type}: {count}")
    
    if result.quality_report:
        print(f"\n📈 Детальные метрики качества:")
        for dimension, score in result.quality_report.dimension_scores.items():
            print(f"   {dimension.value}: {score.score:.2f}")
    
    # Таймировки этапов
    if result.stage_timings:
        print(f"\n⏱️  Время выполнения этапов:")
        for stage, timing in result.stage_timings.items():
            print(f"   {stage.value}: {timing:.2f}с")
    
    # Экспортируем результат
    pipeline.export_pipeline_result(result, "output/sequential_demo_result.json")
    print(f"\n💾 Результат сохранен в output/sequential_demo_result.json")
    
    return result


async def demo_collaborative_pipeline():
    """Демонстрация совместного пайплайна с межкомпонентной обратной связью"""
    
    print("\n=== ДЕМОНСТРАЦИЯ СОВМЕСТНОГО ПАЙПЛАЙНА ===\n")
    
    # Конфигурация с обратной связью
    config = PipelineConfig(
        integration_strategy=IntegrationStrategy.COLLABORATIVE,
        enabled_stages=[
            PipelineStage.NARRATIVE_GENERATION,
            PipelineStage.LEVEL_GENERATION,
            PipelineStage.OBJECT_PLACEMENT,
            PipelineStage.VISUAL_GENERATION,
            PipelineStage.NARRATIVE_ENHANCEMENT,
            PipelineStage.QUALITY_ASSESSMENT
        ],
        quality_threshold=0.75,
        max_iterations=3,
        enable_cross_modal_feedback=True,
        
        # Конфигурации для визуализации
        visualization_config=VisualizationConfig(
            style=VisualizationStyle.CYBERPUNK,
            image_size=(512, 512),
            num_inference_steps=15,
            use_controlnet=False  # Отключаем для демо
        ),
        
        # Конфигурация улучшения нарратива
        enhancement_config=EnhancementConfig(
            target_quality_threshold=0.8,
            max_iterations=2,
            use_adversarial_feedback=True
        )
    )
    
    pipeline = HybridContentPipeline(config)
    
    # Более сложный сценарий
    scenario = ScenarioInput(
        genre="фэнтези",
        hero="молодая эльфийская маг-исследовательница с редким даром предвидения",
        goal="найти утерянный артефакт в заброшенных руинах древнего храма, избегая ловушек и решая магические головоломки"
    )
    
    print(f"Сценарий: {scenario.genre}")
    print(f"Герой: {scenario.hero}")
    print(f"Цель: {scenario.goal}\n")
    
    start_time = time.time()
    result = await pipeline.generate_content(scenario)
    total_time = time.time() - start_time
    
    print(f"✅ Совместная генерация завершена за {total_time:.2f} секунд")
    print(f"📊 Итоговое качество: {result.final_quality_score:.2f}")
    print(f"🔄 Выполнено этапов: {len(result.stages_completed)}")
    
    # Показываем улучшения нарратива
    if result.narrative_analysis:
        print(f"\n📝 Анализ нарратива:")
        print(f"   Общее качество: {result.narrative_analysis.overall_quality:.2f}")
        print(f"   Связность: {result.narrative_analysis.coherence_score:.2f}")
        print(f"   Вовлеченность: {result.narrative_analysis.engagement_score:.2f}")
        print(f"   Оригинальность: {result.narrative_analysis.originality_score:.2f}")
        
        if result.narrative_analysis.suggestions:
            print(f"   Предложения: {len(result.narrative_analysis.suggestions)}")
    
    # Информация о визуализациях
    if result.visualizations:
        print(f"\n🎨 Визуализации: {len(result.visualizations)}")
        for i, viz in enumerate(result.visualizations):
            print(f"   Визуализация {i+1}: {viz.metadata.get('style', 'Unknown')} стиль")
    
    # Лог оптимизации
    if result.optimization_log:
        print(f"\n🔧 Лог оптимизации:")
        for log_entry in result.optimization_log:
            print(f"   - {log_entry}")
    
    pipeline.export_pipeline_result(result, "output/collaborative_demo_result.json")
    print(f"\n💾 Результат сохранен в output/collaborative_demo_result.json")
    
    return result


async def demo_adaptive_pipeline():
    """Демонстрация адаптивного пайплайна с автооптимизацией"""
    
    print("\n=== ДЕМОНСТРАЦИЯ АДАПТИВНОГО ПАЙПЛАЙНА ===\n")
    
    config = PipelineConfig(
        integration_strategy=IntegrationStrategy.ADAPTIVE,
        enabled_stages=[
            PipelineStage.NARRATIVE_GENERATION,
            PipelineStage.LEVEL_GENERATION,
            PipelineStage.OBJECT_PLACEMENT,
            PipelineStage.QUALITY_ASSESSMENT
        ],
        quality_threshold=0.8,
        max_iterations=4,
        memory_optimization=True,
        parallel_workers=1  # Для стабильности демо
    )
    
    pipeline = HybridContentPipeline(config)
    
    # Сценарий с потенциально сложной генерацией
    scenario = ScenarioInput(
        genre="хоррор",
        hero="параноидальный детектив с посттравматическим стрессом",
        goal="расследовать серию мистических исчезновений в заброшенном психиатрическом институте"
    )
    
    print(f"Сценарий: {scenario.genre}")
    print(f"Герой: {scenario.hero}")
    print(f"Цель: {scenario.goal}\n")
    
    start_time = time.time()
    result = await pipeline.generate_content(scenario)
    total_time = time.time() - start_time
    
    print(f"✅ Адаптивная генерация завершена за {total_time:.2f} секунд")
    print(f"📊 Итоговое качество: {result.final_quality_score:.2f}")
    
    # Показываем адаптации
    print(f"\n🤖 Адаптивные оптимизации:")
    if result.optimization_log:
        for log_entry in result.optimization_log:
            print(f"   - {log_entry}")
    else:
        print("   - Оптимизации не потребовались")
    
    # Анализ использования ресурсов
    if result.memory_usage:
        print(f"\n💾 Использование памяти:")
        for component, usage in result.memory_usage.items():
            print(f"   {component}: {usage:.2f}")
    
    pipeline.export_pipeline_result(result, "output/adaptive_demo_result.json")
    print(f"\n💾 Результат сохранен в output/adaptive_demo_result.json")
    
    return result


async def demo_export_functionality():
    """Демонстрация функциональности экспорта"""
    
    print("\n=== ДЕМОНСТРАЦИЯ ЭКСПОРТА В ИГРОВЫЕ ДВИЖКИ ===\n")
    
    # Конфигурация с экспортом
    export_configs = [
        ExportConfig(
            target_engine=GameEngine.UNITY,
            export_format="json",
            output_directory="output/exports",
            include_visuals=False,  # Отключаем для демо
            compress_output=True
        ),
        ExportConfig(
            target_engine=GameEngine.UNREAL_ENGINE,
            export_format="json", 
            output_directory="output/exports",
            include_visuals=False,
            compress_output=True
        )
    ]
    
    config = PipelineConfig(
        integration_strategy=IntegrationStrategy.SEQUENTIAL,
        enabled_stages=[
            PipelineStage.NARRATIVE_GENERATION,
            PipelineStage.LEVEL_GENERATION,
            PipelineStage.OBJECT_PLACEMENT,
            PipelineStage.EXPORT
        ],
        export_configs=export_configs
    )
    
    pipeline = HybridContentPipeline(config)
    
    scenario = ScenarioInput(
        genre="стимпанк",
        hero="изобретатель-механик с паровым экзоскелетом",
        goal="починить главный генератор города, борясь с саботажниками и механическими стражами"
    )
    
    print(f"Сценарий: {scenario.genre}")
    print(f"Герой: {scenario.hero}")
    print(f"Цель: {scenario.goal}\n")
    
    start_time = time.time()
    result = await pipeline.generate_content(scenario)
    total_time = time.time() - start_time
    
    print(f"✅ Генерация с экспортом завершена за {total_time:.2f} секунд")
    print(f"📊 Итоговое качество: {result.final_quality_score:.2f}")
    
    # Проверяем, был ли выполнен экспорт
    if PipelineStage.EXPORT in result.stages_completed:
        print(f"\n📦 Экспорт выполнен для {len(export_configs)} движков:")
        for export_config in export_configs:
            print(f"   - {export_config.target_engine.value}")
    
    pipeline.export_pipeline_result(result, "output/export_demo_result.json")
    print(f"\n💾 Результат сохранен в output/export_demo_result.json")
    
    return result


def compare_pipeline_results(results: list, names: list):
    """Сравнение результатов разных пайплайнов"""
    
    print("\n=== СРАВНЕНИЕ РЕЗУЛЬТАТОВ ПАЙПЛАЙНОВ ===\n")
    
    print(f"{'Пайплайн':<20} {'Время (с)':<10} {'Качество':<10} {'Этапов':<8} {'Сцен':<6}")
    print("-" * 60)
    
    for result, name in zip(results, names):
        print(f"{name:<20} {result.generation_time:<10.2f} {result.final_quality_score:<10.2f} "
              f"{len(result.stages_completed):<8} {len(result.quest.scenes) if result.quest else 0:<6}")
    
    # Находим лучший результат по качеству
    best_idx = max(range(len(results)), key=lambda i: results[i].final_quality_score)
    print(f"\n🏆 Лучший результат: {names[best_idx]} (качество: {results[best_idx].final_quality_score:.2f})")
    
    # Находим самый быстрый
    fastest_idx = min(range(len(results)), key=lambda i: results[i].generation_time)
    print(f"⚡ Самый быстрый: {names[fastest_idx]} ({results[fastest_idx].generation_time:.2f}с)")


async def main():
    """Главная функция демонстрации"""
    
    print("🚀 ДЕМОНСТРАЦИЯ ГИБРИДНОГО ПАЙПЛАЙНА ГЕНЕРАЦИИ ИГРОВОГО КОНТЕНТА")
    print("=" * 80)
    
    # Создаем выходную директорию
    Path("output").mkdir(exist_ok=True)
    Path("output/exports").mkdir(exist_ok=True)
    
    results = []
    names = []
    
    try:
        # Демонстрация последовательного пайплайна
        result1 = await demo_sequential_pipeline()
        results.append(result1)
        names.append("Последовательный")
        
        # Демонстрация совместного пайплайна
        result2 = await demo_collaborative_pipeline()
        results.append(result2)
        names.append("Совместный")
        
        # Демонстрация адаптивного пайплайна
        result3 = await demo_adaptive_pipeline()
        results.append(result3)
        names.append("Адаптивный")
        
        # Демонстрация экспорта
        result4 = await demo_export_functionality()
        results.append(result4)
        names.append("С экспортом")
        
        # Сравнение результатов
        compare_pipeline_results(results, names)
        
        print("\n✅ Все демонстрации успешно завершены!")
        print("\n📁 Результаты сохранены в директории 'output/'")
        print("📁 Экспортированные файлы находятся в 'output/exports/'")
        
    except Exception as e:
        print(f"\n❌ Ошибка во время демонстрации: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Запуск демонстрации
    asyncio.run(main())