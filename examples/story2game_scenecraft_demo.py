"""
Демонстрация интеграции подходов Story2Game и SceneCraft
"""

import asyncio
from pathlib import Path
import json
import sys
sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger

from src.modules.integrated_quest_generator import IntegratedQuestGenerator
from src.core.models import ScenarioInput, GenerationConfig


async def demo_integrated_generation():
    """Демонстрация расширенной генерации с логикой и визуализацией"""
    
    # Настройка логирования
    logger.add("logs/integrated_demo.log", rotation="10 MB")
    
    print("🎮 Демонстрация интегрированной генерации квестов")
    print("=" * 50)
    
    # Конфигурация
    config = GenerationConfig(
        model="gpt-4o-mini",
        temperature=0.8,
        use_rag=True,
        ensure_branching_depth=3
    )
    
    # Инициализация генератора
    generator = IntegratedQuestGenerator(config)
    
    # Сценарий для демонстрации
    scenario = ScenarioInput(
        genre="киберпанк",
        hero="хакер-одиночка по прозвищу Призрак",
        goal="проникнуть в корпоративную лабораторию и украсть экспериментальный чип",
        language="ru"
    )
    
    print(f"\n📝 Сценарий:")
    print(f"   Жанр: {scenario.genre}")
    print(f"   Герой: {scenario.hero}")
    print(f"   Цель: {scenario.goal}")
    
    # 1. Генерация с полной логикой Story2Game
    print("\n1️⃣ Генерация с логикой Story2Game...")
    result_logic = await generator.generate_enhanced_quest(
        scenario,
        with_logic=True,
        with_visuals=False,
        export_code=True
    )
    
    print("✅ Логика сгенерирована!")
    print(f"   - Действий: {len(result_logic['enhancements']['logic']['story_actions'])}")
    print(f"   - Предусловий: {len(result_logic['enhancements']['logic']['preconditions'])}")
    print(f"   - Эффектов: {len(result_logic['enhancements']['logic']['effects'])}")
    
    # Показываем пример сгенерированного кода
    if "generated_code" in result_logic["enhancements"]:
        print("\n📄 Фрагмент сгенерированного кода:")
        code_lines = result_logic["enhancements"]["generated_code"].split('\n')[:20]
        for line in code_lines:
            print(f"   {line}")
        print("   ...")
    
    # 2. Генерация с визуализацией SceneCraft
    print("\n2️⃣ Генерация с визуализацией SceneCraft...")
    result_visual = await generator.generate_enhanced_quest(
        scenario,
        with_logic=False,
        with_visuals=True,
        export_code=False
    )
    
    print("✅ Визуализация создана!")
    viz_data = result_visual['enhancements']['visualization']
    print(f"   - Визуализировано сцен: {len(viz_data['scenes'])}")
    print(f"   - Согласованность визуалов: {viz_data['enhanced_features']['visual_consistency_score']:.2%}")
    
    # 3. Полная интеграция Story2Game + SceneCraft
    print("\n3️⃣ Полная интеграция Story2Game + SceneCraft...")
    result_full = await generator.generate_enhanced_quest(
        scenario,
        with_logic=True,
        with_visuals=True,
        export_code=True
    )
    
    print("✅ Интегрированный квест создан!")
    integrated = result_full['enhancements'].get('integrated', {})
    print(f"   - Интерактивных сцен: {len(integrated.get('interactive_scenes', []))}")
    print(f"   - Визуальных триггеров: {len(integrated.get('visual_triggers', []))}")
    
    # Показываем пример интерактивной сцены
    if integrated.get('interactive_scenes'):
        scene = integrated['interactive_scenes'][0]
        print(f"\n🎬 Пример интерактивной сцены '{scene['scene_id']}':")
        print(f"   - Интерактивных объектов: {len(scene['interactive_objects'])}")
        
        for obj in scene['interactive_objects'][:3]:
            print(f"   • {obj['object']['label']}:")
            for interaction in obj['interactions'][:2]:
                print(f"     - {interaction['type']}: {interaction.get('action', 'N/A')}")
    
    # 4. Демонстрация динамического расширения
    print("\n4️⃣ Демонстрация динамического расширения действий...")
    
    # Включаем динамические действия
    generator.enable_dynamic_actions = True
    
    # Симулируем неожиданное действие игрока
    if result_full['quest'].scenes:
        first_scene = result_full['quest'].scenes[0]
        world_state = generator.story2game.world_state
        
        user_action = "осмотреть вентиляционную решетку на потолке"
        print(f"   Игрок: '{user_action}'")
        
        dynamic_response = await generator.generate_dynamic_response(
            first_scene,
            user_action,
            world_state
        )
        
        if dynamic_response['success']:
            print(f"   ✅ Система: {dynamic_response['action']}")
            print("   Новые опции:")
            for option in dynamic_response['new_options'][:3]:
                print(f"     • {option}")
        else:
            print(f"   ❌ {dynamic_response['message']}")
    
    # 5. Сохранение результатов
    print("\n5️⃣ Сохранение результатов...")
    output_dir = "output/integrated_demo"
    saved_path = generator.save_enhanced_quest(result_full, output_dir)
    print(f"✅ Сохранено в: {saved_path}")
    
    # Статистика
    print("\n📊 Статистика генерации:")
    print(f"   - Время генерации: {result_full['metadata']['generation_time']:.2f} сек")
    print(f"   - Использовано токенов: {result_full['quest'].metadata.get('tokens_used', 'N/A')}")
    print(f"   - Включенные функции: {', '.join(k for k, v in result_full['metadata']['features_enabled'].items() if v)}")
    
    # Визуализация структуры квеста
    print("\n🗺️ Структура сгенерированного квеста:")
    quest = result_full['quest']
    for scene in quest.scenes[:5]:  # Показываем первые 5 сцен
        print(f"\n   [{scene.scene_id}] {scene.text[:100]}...")
        for i, choice in enumerate(scene.choices):
            arrow = "└─>" if i == len(scene.choices) - 1 else "├─>"
            print(f"   {arrow} {choice.text} → {choice.next_scene}")


async def demo_story2game_features():
    """Демонстрация специфичных возможностей Story2Game"""
    
    print("\n\n🎯 Демонстрация возможностей Story2Game")
    print("=" * 50)
    
    generator = IntegratedQuestGenerator()
    
    # Сценарий с явными логическими элементами
    scenario = ScenarioInput(
        genre="фэнтези",
        hero="молодой маг",
        goal="найти три магических кристалла и активировать древний портал",
        language="ru"
    )
    
    print(f"\n📝 Сценарий с логическими элементами:")
    print(f"   Цель: {scenario.goal}")
    
    # Генерация с акцентом на логику
    result = await generator.generate_enhanced_quest(
        scenario,
        with_logic=True,
        with_visuals=False,
        export_code=True
    )
    
    logic = result['enhancements']['logic']
    
    print("\n🔧 Анализ логической структуры:")
    
    # Показываем предусловия
    print("\n   Предусловия действий:")
    for action_id, preconditions in list(logic['preconditions'].items())[:3]:
        if preconditions:
            print(f"   • Действие '{action_id}':")
            for precond in preconditions:
                print(f"     - {precond['type']}: {precond.get('item', precond.get('condition'))}")
    
    # Показываем эффекты
    print("\n   Эффекты действий:")
    for action_id, effects in list(logic['effects'].items())[:3]:
        if effects:
            print(f"   • Действие '{action_id}':")
            for effect in effects:
                print(f"     - {effect['type']}: {effect.get('object', '')} → {effect.get('new_state', '')}")
    
    # Показываем граф доступности действий
    print("\n   Граф доступности:")
    for scene_id, actions in list(logic['action_graph'].items())[:3]:
        print(f"   • Сцена '{scene_id}':")
        for action in actions:
            status = "✅" if action['available'] else "❌"
            print(f"     {status} {action['action_id']} → {action['next_scene']}")


async def demo_scenecraft_features():
    """Демонстрация специфичных возможностей SceneCraft"""
    
    print("\n\n🎨 Демонстрация возможностей SceneCraft")
    print("=" * 50)
    
    generator = IntegratedQuestGenerator()
    
    # Сценарий с богатым визуальным описанием
    scenario = ScenarioInput(
        genre="хоррор",
        hero="детектив-оккультист",
        goal="исследовать заброшенный особняк и найти источник проклятия",
        language="ru"
    )
    
    print(f"\n📝 Сценарий для визуализации:")
    print(f"   Жанр: {scenario.genre}")
    print(f"   Локация: заброшенный особняк")
    
    # Генерация с акцентом на визуализацию
    result = await generator.generate_enhanced_quest(
        scenario,
        with_logic=False,
        with_visuals=True,
        export_code=False
    )
    
    viz = result['enhancements']['visualization']
    
    print("\n🏗️ Анализ сгенерированных макетов:")
    
    for scene_data in viz['scenes'][:3]:
        # Загружаем макет
        with open(scene_data['layout_path'], 'r', encoding='utf-8') as f:
            layout = json.load(f)
        
        print(f"\n   Сцена '{scene_data['scene_id']}':")
        print(f"   - Стиль: {layout['style']}")
        print(f"   - Освещение: {layout['lighting']}")
        
        for room in layout['rooms']:
            print(f"   - Комната '{room['room_type']}':")
            print(f"     Размеры: {room['dimensions']}")
            print(f"     Объектов: {len(room['objects'])}")
            
            # Показываем несколько объектов
            for obj in room['objects'][:3]:
                print(f"     • {obj['label']} ({obj['semantic_class']})")
    
    print(f"\n🖼️ Сгенерированные изображения:")
    for scene_data in viz['scenes'][:2]:
        print(f"   - {scene_data['scene_id']}: {len(scene_data['image_paths'])} ракурсов")
        print(f"     Композит: {scene_data['composite_path']}")


async def main():
    """Главная функция демонстрации"""
    
    print("🚀 ДЕМОНСТРАЦИЯ ИНТЕГРАЦИИ STORY2GAME И SCENECRAFT")
    print("=" * 60)
    
    try:
        # Основная демонстрация
        await demo_integrated_generation()
        
        # Дополнительные демонстрации
        await demo_story2game_features()
        await demo_scenecraft_features()
        
        print("\n\n✨ Демонстрация завершена успешно!")
        print("Проверьте папку 'output/integrated_demo' для результатов.")
        
    except Exception as e:
        logger.error(f"Ошибка в демонстрации: {e}")
        print(f"\n❌ Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())