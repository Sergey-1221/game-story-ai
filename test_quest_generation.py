"""
Тестовый скрипт для проверки генерации квестов
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.quest_generator import QuestGenerator
from src.core.models import ScenarioInput

def test_quest_generation():
    """Тестируем генерацию квестов"""
    print("[TEST] Тестируем систему генерации квестов...")
    
    try:
        # Создаем генератор
        print("[STEP] Создаем генератор...")
        generator = QuestGenerator()
        print("[OK] Генератор создан успешно")
        
        # Создаем тестовый сценарий
        print("[STEP] Создаем тестовый сценарий...")
        scenario = ScenarioInput(
            genre="киберпанк",
            hero="хакер-одиночка",
            goal="взломать корпоративную базу данных"
        )
        print("[OK] Сценарий создан")
        
        # Генерируем квест
        print("[STEP] Запускаем генерацию квеста...")
        quest = generator.generate(scenario)
        print("[OK] Квест сгенерирован успешно!")
        
        # Выводим информацию о квесте
        print(f"\n[RESULT] Результат:")
        print(f"Название: {quest.title}")
        print(f"Жанр: {quest.genre}")
        print(f"Количество сцен: {len(quest.scenes)}")
        print(f"Время генерации: {quest.metadata.get('generation_time', 0):.2f}с")
        
        # Выводим первую сцену
        if quest.scenes:
            first_scene = quest.scenes[0]
            print(f"\n[SCENE] Первая сцена ({first_scene.scene_id}):")
            print(f"Текст: {first_scene.text[:200]}...")
            print(f"Количество выборов: {len(first_scene.choices)}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_quest_generation()
    if success:
        print("\n[SUCCESS] Тест пройден успешно!")
    else:
        print("\n[FAIL] Тест провален!")
        sys.exit(1)