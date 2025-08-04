# Game Story AI 🎮✨

<div align="center">

[🇷🇺 Русский](README.md) | [🇬🇧 English](README-EN.md)

AI-генератор игровых историй, который превращает текстовые описания в интерактивные квесты и сюжетные линии.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)

</div>

<div align="center">
  <h2>🎬 Демонстрация</h2>
  
  <table>
    <tr>
      <td width="50%" align="center">
        <b>🏠 Главное меню</b><br>
        <img src="screenshot/menu.png" alt="Main Menu" width="100%"/>
        <i>Интуитивный интерфейс для быстрого старта</i>
      </td>
      <td width="50%" align="center">
        <b>⚙️ Генератор квестов</b><br>
        <img src="screenshot/generator-1.png" alt="Quest Generator" width="100%"/>
        <i>Гибкие настройки генерации</i>
      </td>
    </tr>
    <tr>
      <td width="50%" align="center">
        <b>🔄 Процесс генерации</b><br>
        <img src="screenshot/generator-2.png" alt="Generation Process" width="100%"/>
        <i>Отслеживание прогресса в реальном времени</i>
      </td>
      <td width="50%" align="center">
        <b>📊 Аналитика и статистика</b><br>
        <img src="screenshot/stats.png" alt="Statistics" width="100%"/>
        <i>Детальные метрики генерации</i>
      </td>
    </tr>
  </table>
  
  <details open>
  <summary><b>🎭 Галерея сгенерированных сцен</b></summary>
  
  <br>
  
  <table>
    <tr>
      <td width="33%" align="center">
        <img src="screenshot/scenes-1.png" alt="Scene 1" width="100%"/>
        <i>Начальная локация</i>
      </td>
      <td width="33%" align="center">
        <img src="screenshot/scenes-2.png" alt="Scene 2" width="100%"/>
        <i>Развитие сюжета</i>
      </td>
      <td width="33%" align="center">
        <img src="screenshot/scenes-3.png" alt="Scene 3" width="100%"/>
        <i>Ключевой выбор</i>
      </td>
    </tr>
    <tr>
      <td width="33%" align="center">
        <img src="screenshot/scenes-4.png" alt="Scene 4" width="100%"/>
        <i>Альтернативный путь</i>
      </td>
      <td width="33%" align="center">
        <img src="screenshot/scenes-5.png" alt="Scene 5" width="100%"/>
        <i>Кульминация</i>
      </td>
      <td width="33%" align="center">
        <img src="screenshot/scenes-6.png" alt="Scene 6" width="100%"/>
        <i>Финальная сцена</i>
      </td>
    </tr>
  </table>
  
  </details>
  
  <details open>
  <summary><b>🎮 Интерактивные элементы</b></summary>
  
  <br>
  
  <table>
    <tr>
      <td width="33%" align="center">
        <img src="screenshot/scenes-interactive-1.png" alt="Interactive 1" width="100%"/>
        <i>Выбор действий</i>
      </td>
      <td width="33%" align="center">
        <img src="screenshot/scenes-interactive-2.png" alt="Interactive 2" width="100%"/>
        <i>Диалоговая система</i>
      </td>
      <td width="33%" align="center">
        <img src="screenshot/scenes-interactive-3.png" alt="Interactive 3" width="100%"/>
        <i>Управление инвентарем</i>
      </td>
    </tr>
  </table>
  
  </details>
  
  <details>
  <summary><b>🎯 Ключевые особенности интерфейса</b></summary>
  
  <br>
  
  - ✨ **Современный дизайн** - Чистый и интуитивный интерфейс на базе Streamlit
  - 🚀 **Быстрая навигация** - Легкое переключение между разделами
  - 📈 **Визуализация прогресса** - Отслеживание каждого этапа генерации
  - 💾 **Управление квестами** - Сохранение и загрузка сгенерированных историй
  - 🌍 **Мультиязычность** - Поддержка русского и английского языков
  - 🎨 **Богатая визуализация** - Детальные сцены с множеством вариантов отображения
  - 🔀 **Интерактивность** - Полноценная система выборов и последствий
  
  </details>
</div>

---

## 🌟 Возможности

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

## 🎮 Как это работает?

<div align="center">
  <table>
    <tr>
      <td align="center" width="25%">
        <h4>1️⃣ Опишите сценарий</h4>
        <p>Введите текстовое описание вашей истории</p>
      </td>
      <td align="center" width="25%">
        <h4>2️⃣ Настройте параметры</h4>
        <p>Выберите модель ИИ и параметры генерации</p>
      </td>
      <td align="center" width="25%">
        <h4>3️⃣ Генерация</h4>
        <p>ИИ создает интерактивный квест</p>
      </td>
      <td align="center" width="25%">
        <h4>4️⃣ Результат</h4>
        <p>Получите готовый квест с визуализацией</p>
      </td>
    </tr>
  </table>
</div>

## 🚀 Быстрый старт

### Требования

- Python 3.8+
- OpenAI API ключ (обязательно)
- Anthropic API ключ (опционально, для моделей Claude)

### Установка

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

### Запуск приложения

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

## 📖 Примеры использования

### Базовая генерация квеста

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

### Расширенная интеграция с Story2Game и SceneCraft

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

### Использование CLI

```bash
# Генерация квеста из файла
python main.py --input scenario.txt --output quest.json

# Быстрая генерация
python main.py --text "Космический исследователь обнаружил инопланетный артефакт" --format json
```

### Использование API

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

## 🏗️ Архитектура

### Пайплайн генерации

```
Входной текст → Парсер → Извлечение знаний → Планирование истории → Генерация сцен
                                                                            ↓
Выход ← Форматирование ← Валидация ← Улучшение логики ← Визуализация
```

### Ключевые компоненты

- **InputParser**: Извлекает параметры сценария (жанр, герой, цель)
- **KnowledgeBase**: RAG система для жанрового контента
- **StoryPlanner**: Создает структуру квеста с ветвлениями
- **SceneGenerator**: Генерирует детальные описания сцен
- **Story2GameEngine**: Добавляет игровую логику (предусловия, эффекты)
- **SceneCraftVisualizer**: Создает 3D макеты и визуализации
- **BranchManager**: Обеспечивает целостность квеста
- **OutputFormatter**: Производит различные форматы вывода

## 📁 Структура проекта

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

## 🛠️ Конфигурация

### Переменные окружения

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

### Опции конфигурации генерации

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

## 📊 Примеры вывода

### Структура JSON квеста

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

### Расширенный вывод с логикой

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

## 🔌 API справочник

### REST эндпоинты

- `POST /generate` - Генерация квеста из JSON
- `POST /generate/file` - Генерация из загруженного файла
- `POST /generate/quick` - Быстрая генерация с параметрами
- `GET /quest/{quest_id}` - Получить сгенерированный квест
- `GET /examples` - Получить примеры сценариев

### Поддержка WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.send(JSON.stringify({
  action: 'generate',
  scenario: 'Фэнтезийное приключение'
}));
```

## 🧪 Тестирование

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

## 🎮 Интеграция с игровыми движками

### Экспорт Unity

```csharp
// Сгенерированный Unity-совместимый код
public class QuestManager : MonoBehaviour {
    private QuestData questData;
    
    void Start() {
        LoadQuest("quest.json");
    }
}
```

### Экспорт Unreal Engine

```cpp
// Сгенерированный Unreal-совместимый код
UCLASS()
class AQuestManager : public AActor {
    GENERATED_BODY()
    
public:
    void LoadQuest(const FString& QuestPath);
};
```

## 🤝 Вклад в проект

Приветствуются pull requests! Пожалуйста, не стесняйтесь отправлять свои предложения.

1. Форкните репозиторий
2. Создайте ветку для фичи (`git checkout -b feature/AmazingFeature`)
3. Закоммитьте изменения (`git commit -m 'Add some AmazingFeature'`)
4. Отправьте в ветку (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📝 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 🙏 Благодарности

- OpenAI за GPT модели
- Anthropic за модели Claude
- Story2Game фреймворк за структурированную игровую логику
- SceneCraft за возможности 3D визуализации
- Spacy за NLP обработку

## 📧 Контакты

Sergey - [@Sergey-1221](https://github.com/Sergey-1221)

Ссылка на проект: [https://github.com/Sergey-1221/game-story-ai](https://github.com/Sergey-1221/game-story-ai)

---

<p align="center">
  Сделано с ❤️ командой Game Story AI
</p>