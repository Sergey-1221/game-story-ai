# AI Game Story Generator

Мощная AI-система для автоматической генерации интерактивных квестов и сюжетов в формате JSON на основе текстового описания. Теперь с поддержкой подходов **Story2Game** и **SceneCraft** для структурированной логики и визуализации!

## Возможности

- **🎨 Визуальный интерфейс** - полнофункциональный UI на Streamlit для удобной работы
- **📝 Генерация структурированных квестов** из краткого текстового описания
- **🔀 Поддержка нелинейных сюжетов** с развилками и альтернативными путями
- **🧠 RAG (Retrieval-Augmented Generation)** для обогащения контента жанровыми деталями
- **⚡ Story2Game интеграция** - структурированная логика с предусловиями и эффектами
- **🎭 SceneCraft визуализация** - генерация 3D-макетов и изображений сцен
- **🏗️ Генерация игровых уровней** с использованием WFC, диффузионных моделей и ML
- **🎮 Экспорт в игровые движки** - Unity, Unreal Engine
- **🔄 Динамическое расширение** - реакция на неожиданные действия игрока
- **📊 Аналитика и метрики** - оценка качества генерации
- **🌍 Поддержка мультиязычности** и различных игровых жанров

## Архитектура

Система состоит из следующих основных модулей:

### Базовые модули:
1. **Input Parser** - обработка входных данных и извлечение параметров сценария
2. **Knowledge Base & RAG** - база знаний и система извлечения релевантной информации
3. **Story Planner** - планировщик структуры квеста и сюжетных веток
4. **Scene Generator** - генератор детализированных описаний сцен с помощью LLM
5. **Branch Manager** - управление ветвлениями и проверка целостности
6. **Output Formatter** - форматирование и вывод в JSON

### Расширенные модули:
7. **Story2Game Engine** - структурированная логика с предусловиями и эффектами
8. **SceneCraft Visualizer** - генерация 3D-макетов и визуализация сцен
9. **Level Generator** - генерация игровых уровней (WFC, ML)
10. **Object Placement Engine** - интеллектуальная расстановка объектов
11. **Diffusion Visualizer** - визуализация через Stable Diffusion
12. **Game Engine Exporters** - экспорт в Unity и Unreal Engine

## Установка

```bash
# Клонировать репозиторий
git clone https://github.com/yourusername/game-story-ai.git
cd game-story-ai

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Скачать языковые модели
python -m spacy download ru_core_news_sm
python -m spacy download en_core_web_sm
```

## Настройка

1. Создайте файл `.env` в корне проекта:

```env
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here  # опционально
CHROMA_PERSIST_DIRECTORY=./data/chroma
LOG_LEVEL=INFO
```

2. Настройте базу знаний, поместив файлы жанровых шаблонов в `data/knowledge_base/`

## Использование

### 🎨 Визуальный интерфейс (Рекомендуется)

```bash
# Windows
run_ui.bat

# Linux/Mac
./run_ui.sh

# Или напрямую
streamlit run streamlit_app.py
```

Откройте http://localhost:8501 в браузере для доступа к полнофункциональному UI.

### Базовый пример (программно)

```python
from src.quest_generator import QuestGenerator

# Инициализация генератора
generator = QuestGenerator()

# Входные данные
scenario = {
    "genre": "киберпанк",
    "hero": "хакер-одиночка",
    "goal": "взломать замок на двери, найти и забрать чип с вирусом"
}

# Генерация квеста
quest = generator.generate(scenario)

# Сохранение результата
generator.save_quest(quest, "quest.json")
```

### Расширенная генерация с Story2Game и SceneCraft

```python
from src.modules.integrated_quest_generator import IntegratedQuestGenerator

# Инициализация расширенного генератора
generator = IntegratedQuestGenerator()

# Генерация с логикой и визуализацией
result = await generator.generate_enhanced_quest(
    scenario,
    with_logic=True,      # Story2Game логика
    with_visuals=True,    # SceneCraft визуализация
    export_code=True      # Экспорт в исполняемый код
)

# Сохранение расширенного квеста
generator.save_enhanced_quest(result, "output/enhanced_quest")
```

### CLI интерфейс

```bash
python main.py --input scenario.txt --output quest.json
```

### API сервер

```bash
# Запуск FastAPI сервера
uvicorn src.api.main:app --reload

# Генерация через API
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"genre": "fantasy", "hero": "knight", "goal": "save princess"}'
```

## Формат входных данных

Текстовый файл должен содержать:
- **Жанр**: например, "киберпанк", "фэнтези", "детектив"
- **Главный герой**: описание протагониста
- **Цель**: основная задача квеста

Пример `scenario.txt`:
```
Жанр: киберпанк
Герой: хакер-одиночка
Цель: взломать замок на двери, найти и забрать чип с вирусом
```

## Формат выходных данных

JSON-структура с массивом сцен:

```json
{
  "quest": {
    "title": "Кража вирусного чипа",
    "genre": "киберпанк",
    "scenes": [
      {
        "scene_id": "scene_1",
        "text": "Ты стоишь перед массивной стальной дверью...",
        "choices": [
          {
            "text": "Использовать кибердеку для взлома",
            "next_scene": "scene_2"
          },
          {
            "text": "Попытаться найти другой вход",
            "next_scene": "scene_3"
          }
        ]
      }
    ]
  }
}
```

## Расширение функциональности

### Добавление новых жанров

1. Создайте файл шаблона в `data/knowledge_base/genres/`
2. Добавьте жанровые описания и терминологию
3. Обновите embeddings базы знаний

### Интеграция с визуализацией

```python
from src.extensions.image_generator import ImageGenerator

# Генерация изображений для сцен
image_gen = ImageGenerator()
for scene in quest.scenes:
    image_url = image_gen.generate_scene_image(scene.text)
    scene.image = image_url
```

## Тестирование

```bash
# Запуск всех тестов
pytest

# Тесты с покрытием
pytest --cov=src

# Только юнит-тесты
pytest tests/unit/

# Интеграционные тесты
pytest tests/integration/
```

## Лицензия

MIT License - см. файл LICENSE

## Вклад в проект

Приветствуются pull requests! Пожалуйста, ознакомьтесь с CONTRIBUTING.md для деталей.