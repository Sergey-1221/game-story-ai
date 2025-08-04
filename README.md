# Game Story AI 🎮✨

<div align="center">

[English](#english) | [Русский](#русский)

AI-powered game story generator that transforms text descriptions into interactive quests and storylines.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)

</div>

---

<a name="english"></a>
## English

### 🌟 Features

- **🎨 Interactive Web UI** - Full-featured Streamlit interface for easy quest creation
- **🤖 AI-Powered Story Generation** - Creates dynamic quests from simple text descriptions
- **🔀 Branching Narratives** - Multiple paths and choices for player agency
- **⚡ Story2Game Integration** - Structured logic with preconditions and effects
- **🎭 SceneCraft Visualization** - 3D scene layouts and visual generation
- **🧠 RAG-Enhanced Content** - Genre-specific knowledge retrieval for richer narratives
- **📊 Multiple Output Formats** - JSON, Python code, Unity/Unreal formats
- **🌍 Multi-language Support** - English and Russian language models
- **🚀 REST API** - FastAPI backend for programmatic access
- **🏗️ Level Generation** - WFC, diffusion models, and ML-based level design
- **📈 Analytics & Metrics** - Quality assessment and generation insights

### 🚀 Quick Start

#### Prerequisites

- Python 3.8+
- OpenAI API key (required)
- Anthropic API key (optional, for Claude models)

#### Installation

1. **Clone the repository**
```bash
git clone https://github.com/Sergey-1221/game-story-ai.git
cd game-story-ai
```

2. **Create virtual environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python -m venv venv
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt

# Download language models
python -m spacy download ru_core_news_sm
python -m spacy download en_core_web_sm
```

4. **Configure environment**
```bash
# Windows
copy .env.example .env

# Linux/macOS
cp .env.example .env
```

Edit `.env` and add your API keys:
```env
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key  # Optional
```

#### Running the Application

**🎨 Web Interface (Recommended)**
```bash
# Windows
run_ui.bat
# or
venv\Scripts\streamlit.exe run streamlit_app.py

# Linux/macOS
./run_ui.sh
# or
streamlit run streamlit_app.py
```

Open http://localhost:8501 in your browser for the full-featured UI.

**🔌 API Server**
```bash
# Windows
start_api.bat
# or
venv\Scripts\python.exe -m uvicorn src.api.main:app --reload

# Linux/macOS
uvicorn src.api.main:app --reload
```

### 📖 Usage Examples

#### Basic Quest Generation

```python
from src.quest_generator import QuestGenerator
from src.core.models import GenerationConfig

# Initialize generator
generator = QuestGenerator()

# Configure generation
config = GenerationConfig(
    model="gpt-4o-mini",
    temperature=0.7,
    use_rag=True,
    branching_depth=2
)

# Generate quest
scenario = "A brave knight must rescue a princess from a dragon"
quest = await generator.generate(scenario, config)

# Save result
generator.save_quest(quest, "quest.json")
```

#### Advanced Integration with Story2Game and SceneCraft

```python
from src.modules.integrated_quest_generator import IntegratedQuestGenerator

# Initialize integrated generator
generator = IntegratedQuestGenerator()

# Generate with full pipeline
result = await generator.generate(
    scenario="Cyberpunk hacker infiltrates megacorp",
    config=config
)

# Access different outputs
quest_structure = result["quest"]
logic_system = result["logic"]
visualizations = result["visualization"]
```

#### CLI Usage

```bash
# Generate quest from file
python main.py --input scenario.txt --output quest.json

# Quick generation
python main.py --text "Space explorer discovers alien artifact" --format json
```

#### API Usage

```bash
# Generate quest via API
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": "Knight rescues princess from dragon",
    "config": {
      "model": "gpt-4o-mini",
      "temperature": 0.7
    }
  }'
```

### 🏗️ Architecture

#### Generation Pipeline

```
Input Text → Parser → Knowledge Retrieval → Story Planning → Scene Generation
                                                                     ↓
Output ← Formatting ← Validation ← Logic Enhancement ← Visualization
```

#### Key Components

- **InputParser**: Extracts scenario parameters (genre, hero, goal)
- **KnowledgeBase**: RAG system for genre-specific content
- **StoryPlanner**: Creates quest structure with branching paths
- **SceneGenerator**: Generates detailed scene descriptions
- **Story2GameEngine**: Adds game logic (preconditions, effects)
- **SceneCraftVisualizer**: Creates 3D layouts and visuals
- **BranchManager**: Ensures quest integrity and coherence
- **OutputFormatter**: Produces various output formats

### 📁 Project Structure

```
game-story-ai/
├── src/
│   ├── core/
│   │   └── models.py               # Data models and structures
│   ├── modules/
│   │   ├── input_parser.py         # Input processing
│   │   ├── knowledge_base.py       # RAG implementation
│   │   ├── scene_generator.py      # Scene generation
│   │   ├── story2game_engine.py    # Logic system
│   │   ├── scenecraft_visualizer.py # 3D visualization
│   │   └── integrated_quest_generator.py # Full pipeline
│   ├── api/
│   │   └── main.py                # FastAPI server
│   └── quest_generator.py         # Main generator class
├── data/
│   ├── knowledge_base/            # Genre templates and content
│   └── chroma/                    # Vector database storage
├── examples/                      # Demo scripts
├── tests/                         # Test suite
├── streamlit_app.py              # Web UI
└── requirements.txt              # Dependencies
```

### 🛠️ Configuration

#### Environment Variables

Create a `.env` file with:

```env
# Required
OPENAI_API_KEY=your-api-key

# Optional
ANTHROPIC_API_KEY=your-claude-key
DEFAULT_MODEL=gpt-4o-mini
LOG_LEVEL=INFO
CHROMA_PERSIST_DIRECTORY=./data/chroma
```

#### Generation Config Options

```python
config = GenerationConfig(
    model="gpt-4o-mini",          # LLM model
    temperature=0.7,              # Creativity (0-1)
    max_tokens=2000,              # Response length
    use_rag=True,                 # Enable knowledge retrieval
    branching_depth=2,            # Quest complexity
    enable_visualization=True,     # Generate visuals
    output_format="json"          # Output format
)
```

### 📊 Output Examples

#### Quest JSON Structure

```json
{
  "title": "The Dragon's Keep",
  "genre": "fantasy",
  "hero": {
    "name": "Sir Galahad",
    "class": "Knight"
  },
  "scenes": [
    {
      "id": "scene_1",
      "description": "You stand before the dragon's lair...",
      "choices": [
        {
          "text": "Enter stealthily",
          "next_scene": "scene_2a"
        },
        {
          "text": "Challenge the dragon",
          "next_scene": "scene_2b"
        }
      ]
    }
  ]
}
```

#### Enhanced Output with Logic

```json
{
  "quest": { /* Basic quest structure */ },
  "logic": {
    "world_state": {
      "objects": ["sword", "shield", "key"],
      "locations": ["castle", "forest", "cave"]
    },
    "actions": {
      "take_sword": {
        "preconditions": ["at(castle)", "not has(sword)"],
        "effects": ["has(sword)", "armed(true)"]
      }
    }
  },
  "visualization": {
    "scenes": {
      "scene_1": {
        "layout": "3d_layout.json",
        "image": "scene_1.png"
      }
    }
  }
}
```

### 🔌 API Reference

#### REST Endpoints

- `POST /generate` - Generate quest from JSON
- `POST /generate/file` - Generate from uploaded file
- `POST /generate/quick` - Quick generation with parameters
- `GET /quest/{quest_id}` - Retrieve generated quest
- `GET /examples` - Get example scenarios

#### WebSocket Support

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.send(JSON.stringify({
  action: 'generate',
  scenario: 'Fantasy adventure'
}));
```

### 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific tests
pytest tests/unit/
pytest tests/integration/

# Run test scripts
python test_generation.py
python test_quest_generation.py
```

### 🎮 Game Engine Integration

#### Unity Export

```csharp
// Generated Unity-compatible code
public class QuestManager : MonoBehaviour {
    private QuestData questData;
    
    void Start() {
        LoadQuest("quest.json");
    }
}
```

#### Unreal Engine Export

```cpp
// Generated Unreal-compatible code
UCLASS()
class AQuestManager : public AActor {
    GENERATED_BODY()
    
public:
    void LoadQuest(const FString& QuestPath);
};
```

---

<a name="русский"></a>
## Русский

### 🌟 Возможности

- **🎨 Интерактивный веб-интерфейс** - Полнофункциональный UI на Streamlit для удобной работы
- **🤖 Генерация историй с помощью ИИ** - Создание динамических квестов из текстовых описаний
- **🔀 Ветвящиеся повествования** - Множественные пути и выборы для игрока
- **⚡ Интеграция Story2Game** - Структурированная логика с предусловиями и эффектами
- **🎭 Визуализация SceneCraft** - 3D-макеты сцен и генерация изображений
- **🧠 RAG-обогащение контента** - Извлечение жанровых знаний для более богатых историй
- **📊 Множество выходных форматов** - JSON, Python код, форматы Unity/Unreal
- **🌍 Мультиязычная поддержка** - Английские и русские языковые модели
- **🚀 REST API** - FastAPI бэкенд для программного доступа
- **🏗️ Генерация уровней** - WFC, диффузионные модели и ML-генерация
- **📈 Аналитика и метрики** - Оценка качества генерации

### 🚀 Быстрый старт

#### Требования

- Python 3.8+
- OpenAI API ключ (обязательно)
- Anthropic API ключ (опционально, для моделей Claude)

#### Установка

1. **Клонируйте репозиторий**
```bash
git clone https://github.com/Sergey-1221/game-story-ai.git
cd game-story-ai
```

2. **Создайте виртуальное окружение**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python -m venv venv
source venv/bin/activate
```

3. **Установите зависимости**
```bash
pip install -r requirements.txt

# Скачайте языковые модели
python -m spacy download ru_core_news_sm
python -m spacy download en_core_web_sm
```

4. **Настройте окружение**
```bash
# Windows
copy .env.example .env

# Linux/macOS
cp .env.example .env
```

Отредактируйте `.env` и добавьте ваши API ключи:
```env
OPENAI_API_KEY=ваш-openai-api-ключ
ANTHROPIC_API_KEY=ваш-anthropic-api-ключ  # Опционально
```

#### Запуск приложения

**🎨 Веб-интерфейс (Рекомендуется)**
```bash
# Windows
run_ui.bat
# или
venv\Scripts\streamlit.exe run streamlit_app.py

# Linux/macOS
./run_ui.sh
# или
streamlit run streamlit_app.py
```

Откройте http://localhost:8501 в браузере для полнофункционального UI.

**🔌 API сервер**
```bash
# Windows
start_api.bat
# или
venv\Scripts\python.exe -m uvicorn src.api.main:app --reload

# Linux/macOS
uvicorn src.api.main:app --reload
```

### 📖 Примеры использования

#### Базовая генерация квеста

```python
from src.quest_generator import QuestGenerator
from src.core.models import GenerationConfig

# Инициализация генератора
generator = QuestGenerator()

# Настройка генерации
config = GenerationConfig(
    model="gpt-4o-mini",
    temperature=0.7,
    use_rag=True,
    branching_depth=2
)

# Генерация квеста
scenario = "Храбрый рыцарь должен спасти принцессу от дракона"
quest = await generator.generate(scenario, config)

# Сохранение результата
generator.save_quest(quest, "quest.json")
```

#### Расширенная интеграция с Story2Game и SceneCraft

```python
from src.modules.integrated_quest_generator import IntegratedQuestGenerator

# Инициализация интегрированного генератора
generator = IntegratedQuestGenerator()

# Генерация с полным пайплайном
result = await generator.generate(
    scenario="Киберпанк хакер проникает в мегакорпорацию",
    config=config
)

# Доступ к различным выходам
quest_structure = result["quest"]
logic_system = result["logic"]
visualizations = result["visualization"]
```

#### Использование CLI

```bash
# Генерация квеста из файла
python main.py --input scenario.txt --output quest.json

# Быстрая генерация
python main.py --text "Космический исследователь обнаружил инопланетный артефакт" --format json
```

#### Использование API

```bash
# Генерация квеста через API
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": "Рыцарь спасает принцессу от дракона",
    "config": {
      "model": "gpt-4o-mini",
      "temperature": 0.7
    }
  }'
```

### 🏗️ Архитектура

#### Пайплайн генерации

```
Входной текст → Парсер → Извлечение знаний → Планирование истории → Генерация сцен
                                                                            ↓
Выход ← Форматирование ← Валидация ← Улучшение логики ← Визуализация
```

#### Ключевые компоненты

- **InputParser**: Извлекает параметры сценария (жанр, герой, цель)
- **KnowledgeBase**: RAG система для жанрового контента
- **StoryPlanner**: Создает структуру квеста с ветвлениями
- **SceneGenerator**: Генерирует детальные описания сцен
- **Story2GameEngine**: Добавляет игровую логику (предусловия, эффекты)
- **SceneCraftVisualizer**: Создает 3D макеты и визуализации
- **BranchManager**: Обеспечивает целостность квеста
- **OutputFormatter**: Производит различные форматы вывода

### 📁 Структура проекта

```
game-story-ai/
├── src/
│   ├── core/
│   │   └── models.py               # Модели данных и структуры
│   ├── modules/
│   │   ├── input_parser.py         # Обработка входных данных
│   │   ├── knowledge_base.py       # RAG реализация
│   │   ├── scene_generator.py      # Генерация сцен
│   │   ├── story2game_engine.py    # Система логики
│   │   ├── scenecraft_visualizer.py # 3D визуализация
│   │   └── integrated_quest_generator.py # Полный пайплайн
│   ├── api/
│   │   └── main.py                # FastAPI сервер
│   └── quest_generator.py         # Основной класс генератора
├── data/
│   ├── knowledge_base/            # Жанровые шаблоны и контент
│   └── chroma/                    # Хранилище векторной БД
├── examples/                      # Демо скрипты
├── tests/                         # Набор тестов
├── streamlit_app.py              # Веб UI
└── requirements.txt              # Зависимости
```

### 🛠️ Конфигурация

#### Переменные окружения

Создайте файл `.env`:

```env
# Обязательно
OPENAI_API_KEY=ваш-api-ключ

# Опционально
ANTHROPIC_API_KEY=ваш-claude-ключ
DEFAULT_MODEL=gpt-4o-mini
LOG_LEVEL=INFO
CHROMA_PERSIST_DIRECTORY=./data/chroma
```

#### Опции конфигурации генерации

```python
config = GenerationConfig(
    model="gpt-4o-mini",          # LLM модель
    temperature=0.7,              # Креативность (0-1)
    max_tokens=2000,              # Длина ответа
    use_rag=True,                 # Включить извлечение знаний
    branching_depth=2,            # Сложность квеста
    enable_visualization=True,     # Генерировать визуализации
    output_format="json"          # Формат вывода
)
```

### 📊 Примеры вывода

#### Структура JSON квеста

```json
{
  "title": "Логово дракона",
  "genre": "фэнтези",
  "hero": {
    "name": "Сэр Галахад",
    "class": "Рыцарь"
  },
  "scenes": [
    {
      "id": "scene_1",
      "description": "Вы стоите перед логовом дракона...",
      "choices": [
        {
          "text": "Войти незаметно",
          "next_scene": "scene_2a"
        },
        {
          "text": "Бросить вызов дракону",
          "next_scene": "scene_2b"
        }
      ]
    }
  ]
}
```

#### Расширенный вывод с логикой

```json
{
  "quest": { /* Базовая структура квеста */ },
  "logic": {
    "world_state": {
      "objects": ["меч", "щит", "ключ"],
      "locations": ["замок", "лес", "пещера"]
    },
    "actions": {
      "take_sword": {
        "preconditions": ["at(замок)", "not has(меч)"],
        "effects": ["has(меч)", "armed(true)"]
      }
    }
  },
  "visualization": {
    "scenes": {
      "scene_1": {
        "layout": "3d_layout.json",
        "image": "scene_1.png"
      }
    }
  }
}
```

### 🔌 API справочник

#### REST эндпоинты

- `POST /generate` - Генерация квеста из JSON
- `POST /generate/file` - Генерация из загруженного файла
- `POST /generate/quick` - Быстрая генерация с параметрами
- `GET /quest/{quest_id}` - Получить сгенерированный квест
- `GET /examples` - Получить примеры сценариев

#### Поддержка WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.send(JSON.stringify({
  action: 'generate',
  scenario: 'Фэнтезийное приключение'
}));
```

### 🧪 Тестирование

```bash
# Запуск всех тестов
pytest

# Запуск с покрытием
pytest --cov=src

# Запуск отдельных тестов
pytest tests/unit/
pytest tests/integration/

# Запуск тестовых скриптов
python test_generation.py
python test_quest_generation.py
```

### 🎮 Интеграция с игровыми движками

#### Экспорт Unity

```csharp
// Сгенерированный Unity-совместимый код
public class QuestManager : MonoBehaviour {
    private QuestData questData;
    
    void Start() {
        LoadQuest("quest.json");
    }
}
```

#### Экспорт Unreal Engine

```cpp
// Сгенерированный Unreal-совместимый код
UCLASS()
class AQuestManager : public AActor {
    GENERATED_BODY()
    
public:
    void LoadQuest(const FString& QuestPath);
};
```

---

## 🤝 Contributing / Вклад в проект

Contributions are welcome! Please feel free to submit a Pull Request.

Приветствуются pull requests! Пожалуйста, не стесняйтесь отправлять свои предложения.

1. Fork the repository / Форкните репозиторий
2. Create your feature branch / Создайте ветку для фичи (`git checkout -b feature/AmazingFeature`)
3. Commit your changes / Закоммитьте изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch / Отправьте в ветку (`git push origin feature/AmazingFeature`)
5. Open a Pull Request / Откройте Pull Request

## 📝 License / Лицензия

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 🙏 Acknowledgments / Благодарности

- OpenAI for GPT models / OpenAI за GPT модели
- Anthropic for Claude models / Anthropic за модели Claude
- Story2Game framework for structured game logic / Story2Game фреймворк за структурированную игровую логику
- SceneCraft for 3D visualization capabilities / SceneCraft за возможности 3D визуализации
- Spacy for NLP processing / Spacy за NLP обработку

## 📧 Contact / Контакты

Sergey - [@Sergey-1221](https://github.com/Sergey-1221)

Project Link / Ссылка на проект: [https://github.com/Sergey-1221/game-story-ai](https://github.com/Sergey-1221/game-story-ai)

---

<p align="center">
  Made with ❤️ by the Game Story AI team
  <br>
  Сделано с ❤️ командой Game Story AI
</p>