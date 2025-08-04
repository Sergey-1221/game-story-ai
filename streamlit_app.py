"""
Визуальный интерфейс для AI Game Story Generator
Позволяет интерактивно работать со всеми функциями системы
"""

import streamlit as st
import asyncio
from pathlib import Path
import json
import time
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from streamlit_option_menu import option_menu
import base64
from PIL import Image
import io
import os
from dotenv import load_dotenv


__import__("pysqlite3")
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

# Загружаем переменные окружения из .env файла
load_dotenv()

from src.quest_generator import QuestGenerator
from src.modules.integrated_quest_generator import IntegratedQuestGenerator
from src.core.models import ScenarioInput, GenerationConfig, Genre
from src.modules.knowledge_base import KnowledgeBase


def get_github_raw_url(file_path: str, use_github: bool = True) -> str:
    """
    Преобразует локальный путь файла в GitHub raw URL.
    
    Args:
        file_path: Локальный путь к файлу
        use_github: Флаг использования GitHub URLs (True для Streamlit Cloud)
    
    Returns:
        GitHub raw URL или локальный путь
    """
    if not use_github:
        return file_path
    
    try:
        # Конфигурация репозитория
        GITHUB_OWNER = "Sergey-1221"
        GITHUB_REPO = "game-story-ai"
        GITHUB_BRANCH = "streamlit-cloud"
        
        # Нормализуем путь - заменяем все обратные слеши на прямые
        normalized_path = str(file_path).replace('\\', '/')
        
        # Если путь уже выглядит как относительный (начинается с saved_quests), используем его как есть
        if normalized_path.startswith('saved_quests/'):
            rel_path_str = normalized_path
        else:
            # Преобразуем путь в относительный
            path = Path(normalized_path)
            if path.is_absolute():
                # Пытаемся получить относительный путь от корня проекта
                try:
                    rel_path = path.relative_to(Path.cwd())
                    rel_path_str = str(rel_path).replace('\\', '/')
                except ValueError:
                    # Если не удается, проверяем, есть ли saved_quests в пути
                    path_str = str(path).replace('\\', '/')
                    if 'saved_quests' in path_str:
                        # Извлекаем часть пути начиная с saved_quests
                        rel_path_str = path_str[path_str.find('saved_quests'):]
                    else:
                        rel_path_str = path_str
            else:
                rel_path_str = normalized_path
        github_url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{rel_path_str}"
        
        # Логирование для отладки
        if st.session_state.get('debug_mode', False):
            st.sidebar.write(f"Original path: {file_path}")
            st.sidebar.write(f"GitHub URL: {github_url}")
        
        return github_url
    except Exception as e:
        # В случае ошибки возвращаем оригинальный путь
        if st.session_state.get('debug_mode', False):
            st.sidebar.error(f"Error creating GitHub URL: {e}")
        return file_path


# Автоматическое определение окружения Streamlit Cloud
# Проверяем различные способы определения Streamlit Cloud
is_streamlit_cloud = (
    # Проверяем специфические переменные окружения
    any(env in os.environ for env in ['STREAMLIT_SHARING_MODE', 'STREAMLIT_SERVER_ADDRESS']) or
    # Проверяем, запущено ли не локально (нет localhost в URL)
    os.environ.get('STREAMLIT_SERVER_HEADLESS', '').lower() == 'true' or
    # Проверяем наличие файла .streamlit/config.toml (обычно есть в Streamlit Cloud)
    Path('.streamlit/config.toml').exists() or
    # Принудительно включаем для Streamlit Cloud через переменную окружения
    os.environ.get('FORCE_GITHUB_URLS', 'false').lower() == 'true'
)

if is_streamlit_cloud:
    os.environ['STREAMLIT_CLOUD'] = 'true'
else:
    os.environ['STREAMLIT_CLOUD'] = 'false'

# Настройка страницы
st.set_page_config(
    page_title="AI Game Story Generator",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS для улучшения внешнего вида
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .stButton>button {
        background-color: #667eea;
        color: white;
        border-radius: 20px;
        padding: 0.5rem 2rem;
        font-weight: bold;
        border: none;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #764ba2;
        transform: translateY(-2px);
    }
    .scene-card {
        background: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)


# Функции для работы с персистентным хранилищем
def load_persistent_data():
    """Загрузка данных из локального хранилища"""
    persistent_file = Path("saved_quests") / "session_data.json"
    if persistent_file.exists():
        try:
            with open(persistent_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except Exception as e:
            st.warning(f"Не удалось загрузить сохраненные данные: {e}")
    return {"quest_history": [], "current_quest": None}

def save_persistent_data():
    """Сохранение данных в локальное хранилище"""
    try:
        save_dir = Path("saved_quests")
        save_dir.mkdir(exist_ok=True)
        
        persistent_file = save_dir / "session_data.json"
        
        # Подготавливаем данные для сохранения
        data_to_save = {
            "quest_history": [],
            "current_quest": None
        }
        
        # Сохраняем историю квестов
        for h in st.session_state.quest_history:
            history_item = {
                'timestamp': h['timestamp'].isoformat() if hasattr(h['timestamp'], 'isoformat') else str(h['timestamp']),
                'quest': h['quest'].model_dump() if hasattr(h['quest'], 'model_dump') else h['quest'].__dict__,
                'type': h['type']
            }
            if 'enhancements' in h:
                history_item['enhancements'] = h['enhancements']
            data_to_save["quest_history"].append(history_item)
        
        # Сохраняем текущий квест
        if st.session_state.current_quest:
            data_to_save["current_quest"] = (
                st.session_state.current_quest.model_dump() 
                if hasattr(st.session_state.current_quest, 'model_dump') 
                else st.session_state.current_quest.__dict__
            )
        
        with open(persistent_file, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2, default=str)
            
    except Exception as e:
        st.warning(f"Не удалось сохранить данные сессии: {e}")

# Инициализация состояния сессии с загрузкой персистентных данных
if 'quest_history' not in st.session_state:
    persistent_data = load_persistent_data()
    st.session_state.quest_history = persistent_data.get("quest_history", [])
    
    # Восстанавливаем временные метки и объекты квестов
    for h in st.session_state.quest_history:
        if isinstance(h.get('timestamp'), str):
            try:
                h['timestamp'] = datetime.fromisoformat(h['timestamp'])
            except:
                h['timestamp'] = datetime.now()
        
        # Восстанавливаем объект квеста из словаря
        if isinstance(h.get('quest'), dict):
            try:
                from src.core.models import Quest
                h['quest'] = Quest(**h['quest'])
            except Exception as e:
                # Если не удается восстановить объект, создаем заглушку
                h['quest'] = type('Quest', (), {
                    'title': h['quest'].get('title', 'Неизвестный квест'),
                    'genre': h['quest'].get('genre', 'неизвестно'),
                    'hero': h['quest'].get('hero', ''),
                    'goal': h['quest'].get('goal', ''),
                    'scenes': h['quest'].get('scenes', []),
                    'paths': h['quest'].get('paths', []),
                    'metadata': h['quest'].get('metadata', {}),
                    'model_dump': lambda: h['quest']
                })()

if 'current_quest' not in st.session_state:
    persistent_data = load_persistent_data()
    current_quest_data = persistent_data.get("current_quest")
    if current_quest_data:
        # Восстанавливаем объект квеста из данных
        try:
            from src.core.models import Quest
            st.session_state.current_quest = Quest(**current_quest_data)
        except:
            st.session_state.current_quest = None
    else:
        st.session_state.current_quest = None

if 'generator' not in st.session_state:
    st.session_state.generator = None
if 'integrated_generator' not in st.session_state:
    st.session_state.integrated_generator = None


def init_generators():
    """Инициализация генераторов"""
    if st.session_state.generator is None:
        with st.spinner("Инициализация системы..."):
            try:
                st.session_state.generator = QuestGenerator()
            except Exception as e:
                st.error(f"Ошибка инициализации QuestGenerator: {e}")
                st.info("Проверьте настройки API ключей и зависимости")
                import traceback
                st.code(traceback.format_exc())
                st.stop()
    
    if st.session_state.integrated_generator is None:
        with st.spinner("Инициализация расширенного генератора..."):
            try:
                st.session_state.integrated_generator = IntegratedQuestGenerator()
            except Exception as e:
                st.error(f"Ошибка инициализации IntegratedQuestGenerator: {e}")
                st.warning("Расширенная генерация будет недоступна")
                import traceback
                st.code(traceback.format_exc())


def main():
    # Заголовок
    st.markdown("""
    <div class="main-header">
        <h1>🎮 AI Game Story Generator</h1>
        <p>Создавайте интерактивные квесты с помощью искусственного интеллекта</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Боковое меню
    with st.sidebar:
        # st.image("https://via.placeholder.com/300x100/667eea/ffffff?text=AI+Story+Generator", use_container_width=True)
        
        # Проверяем флаг для скрытия генератора
        hide_generation = os.getenv("HIDE_GENERATION_UI", "false").lower() == "true"
        
        if hide_generation:
            # Меню без генератора
            menu_items = ["🏠 Главная", "📊 Аналитика", "🎬 Сцены", "⚙️ Настройки", "📚 Справка"]
            menu_icons = ['house', 'graph-up', 'film', 'gear', 'book']
        else:
            # Полное меню
            menu_items = ["🏠 Главная", "✨ Генератор", "📊 Аналитика", "🎬 Сцены", "⚙️ Настройки", "📚 Справка"]
            menu_icons = ['house', 'magic', 'graph-up', 'film', 'gear', 'book']
        
        selected = option_menu(
            "Меню",
            menu_items,
            icons=menu_icons,
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "#fafafa"},
                "icon": {"color": "#667eea", "font-size": "20px"},
                "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "--hover-color": "#eee"},
                "nav-link-selected": {"background-color": "#667eea"},
            }
        )
    
    # Инициализация генераторов только если генератор не скрыт
    if not hide_generation:
        init_generators()
    
    # Роутинг страниц
    if selected == "🏠 Главная":
        show_home_page()
    elif selected == "✨ Генератор" and not hide_generation:
        show_generator_page()
    elif selected == "📊 Аналитика":
        show_analytics_page()
    elif selected == "🎬 Сцены":
        show_history_page()
    elif selected == "⚙️ Настройки":
        show_settings_page()
    elif selected == "📚 Справка":
        show_help_page()


def show_home_page():
    """Главная страница"""
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Добро пожаловать!")
        st.write("""
        **AI Game Story Generator** - это мощная система для автоматической генерации 
        интерактивных квестов и сюжетов. Используя передовые технологии ИИ, мы создаем 
        уникальные истории с ветвящимся сюжетом, логической структурой и визуализацией.
        """)
        
        st.subheader("🚀 Возможности системы")
        
        features = {
            "📝 Текстовая генерация": "Создание детализированных сцен и диалогов",
            "🔀 Нелинейные сюжеты": "Поддержка развилок и альтернативных путей",
            "🧠 Story2Game логика": "Предусловия и эффекты для каждого действия",
            "🎨 Визуализация": "Изображения сцен",
            "📊 Аналитика качества": "Метрики и оценка генерации"
        }
        
        for feature, description in features.items():
            st.markdown(f"**{feature}**: {description}")
        
        st.subheader("📈 Статистика")
        metrics = st.columns(4)
        with metrics[0]:
            st.metric("Квестов создано", len(st.session_state.quest_history))
        with metrics[1]:
            st.metric("Жанров доступно", len(["киберпанк", "фэнтези", "детектив", "хоррор", "научная фантастика", "постапокалипсис", "стимпанк"]))
        with metrics[2]:
            modules_count = 0
            if st.session_state.generator:
                modules_count += 5  # базовые модули
            if st.session_state.integrated_generator:
                modules_count += 3  # расширенные модули
            st.metric("Модулей активно", modules_count)
        with metrics[3]:
            success_rate = 0
            if st.session_state.quest_history:
                success_rate = len([h for h in st.session_state.quest_history if h['quest']]) / len(st.session_state.quest_history) * 100
            st.metric("Успешных генераций", f"{success_rate:.0f}%" if st.session_state.quest_history else "N/A")
    
    with col2:
        st.subheader("🎯 Быстрый старт")
        
        quick_genre = st.selectbox(
            "Выберите жанр",
            ["Киберпанк", "Фэнтези", "Детектив", "Хоррор", "Научная фантастика"]
        )
        
        quick_hero = st.text_input("Герой", placeholder="Например: хакер-одиночка")
        quick_goal = st.text_area("Цель", placeholder="Например: взломать систему и украсть данные", height=100)
        
        if st.button("🚀 Быстрая генерация", use_container_width=True):
            if quick_hero and quick_goal:
                st.session_state.quick_scenario = {
                    "genre": quick_genre.lower(),
                    "hero": quick_hero,
                    "goal": quick_goal
                }
                st.success("Сценарий сохранен! Перейдите на вкладку 'Генератор' для создания квеста.")
                st.info("💡 Ваши данные автоматически заполнят форму в генераторе")
            else:
                st.error("Заполните все поля!")


def show_generator_page():
    """Страница генератора"""
    st.header("✨ Генератор квестов")
    
    # Табы для разных режимов
    tab1, tab2, tab3 = st.tabs(["🎯 Базовая генерация", "🔧 Расширенная генерация", "📁 Загрузка файла"])
    
    with tab1:
        show_basic_generator()
    
    with tab2:
        show_advanced_generator()
    
    with tab3:
        show_file_generator()


def show_basic_generator():
    """Базовый генератор"""
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Параметры сценария")
        
        # Проверяем, есть ли быстрый сценарий
        quick_scenario = st.session_state.get('quick_scenario', {})
        
        # Если есть быстрый сценарий, показываем уведомление
        if quick_scenario:
            st.info("📋 Используются данные из быстрой генерации")
            if st.button("🗑️ Очистить", help="Очистить автозаполненные данные"):
                st.session_state.quick_scenario = {}
                st.rerun()
        
        # Получаем значения по умолчанию из быстрого сценария
        default_genre_idx = 0
        if quick_scenario.get('genre'):
            genres = ["киберпанк", "фэнтези", "детектив", "хоррор", "научная фантастика", "постапокалипсис", "стимпанк"]
            try:
                default_genre_idx = genres.index(quick_scenario['genre'].lower())
            except ValueError:
                default_genre_idx = 0
        
        genre = st.selectbox(
            "Жанр",
            ["киберпанк", "фэнтези", "детектив", "хоррор", "научная фантастика", "постапокалипсис", "стимпанк"],
            index=default_genre_idx,
            help="Выберите жанр вашего квеста"
        )
        
        hero = st.text_input(
            "Главный герой",
            value=quick_scenario.get('hero', ''),
            placeholder="Опишите протагониста",
            help="Например: молодой маг-ученик, опытный детектив, хакер-одиночка"
        )
        
        goal = st.text_area(
            "Цель квеста",
            value=quick_scenario.get('goal', ''),
            placeholder="Опишите основную задачу героя",
            height=150,
            help="Чем подробнее описание, тем интереснее будет квест"
        )
        
        # Дополнительные параметры
        with st.expander("⚙️ Дополнительные настройки"):
            language = st.selectbox("Язык", ["ru", "en"])
            min_scenes = st.slider("Минимум сцен", 5, 8, 5)
            max_scenes = st.slider("Максимум сцен", 7, 10, 10)
            temperature = st.slider("Креативность (temperature)", 0.0, 1.0, 0.8, 0.1)
    
    with col2:
        st.subheader("Предпросмотр")
        
        if hero and goal:
            st.info(f"""
            **Жанр**: {genre}
            **Герой**: {hero}
            **Цель**: {goal}
            """)
            
            # Кнопка генерации
            if st.button("🎮 Сгенерировать квест", use_container_width=True, type="primary"):
                generate_basic_quest(genre, hero, goal, language, temperature)
        else:
            st.warning("Заполните все обязательные поля")
    
    # Результат сохранен в истории


def show_advanced_generator():
    """Расширенный генератор с Story2Game и SceneCraft"""
    st.subheader("🔧 Расширенная генерация")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Основные параметры
        genre = st.selectbox("Жанр", ["киберпанк", "фэнтези", "детектив", "хоррор"])
        hero = st.text_input("Главный герой")
        goal = st.text_area("Цель квеста", height=100)
        
        # Расширенные опции
        st.subheader("Модули генерации")
        with_logic = st.checkbox("🧠 Story2Game логика", value=True, 
                                help="Добавить предусловия и эффекты действий")
        with_visuals = st.checkbox("🎨 Визуализация", value=True,
                                  help="Создать изображения сцен")
        export_code = st.checkbox("💻 Экспорт в код", value=False,
                                 help="Сгенерировать исполняемый Python/JS код")
        
        # Настройки визуализации
        if with_visuals:
            with st.expander("Настройки визуализации"):
                visual_style = st.selectbox("Стиль", ["realistic", "stylized", "pixel_art"])
                lighting = st.selectbox("Освещение", ["natural", "dramatic", "mysterious"])
                camera_angles = st.multiselect("Ракурсы", ["front", "top", "isometric", "cinematic"],
                                             default=["front", "isometric"])
    
    with col2:
        # Настройки логики
        if with_logic:
            st.subheader("Настройки логики")
            
            enable_dynamic = st.checkbox("Динамические действия", 
                                       help="Реагировать на неожиданные действия игрока")
            
            track_inventory = st.checkbox("Отслеживать инвентарь", value=True)
            track_states = st.checkbox("Отслеживать состояния объектов", value=True)
            
            complexity = st.select_slider(
                "Сложность логики",
                options=["простая", "средняя", "сложная"],
                value="средняя"
            )
    
    # Кнопка генерации
    if st.button("🚀 Запустить расширенную генерацию", use_container_width=True, type="primary"):
        if hero and goal:
            generate_advanced_quest(
                genre, hero, goal,
                with_logic, with_visuals, export_code,
                visual_style if with_visuals else None,
                enable_dynamic if with_logic else False
            )
        else:
            st.error("Заполните обязательные поля!")


def show_file_generator():
    """Генератор из файла"""
    st.subheader("📁 Загрузка сценария из файла")
    
    uploaded_file = st.file_uploader(
        "Выберите текстовый файл со сценарием",
        type=['txt'],
        help="Файл должен содержать: Жанр, Герой, Цель"
    )
    
    if uploaded_file:
        content = uploaded_file.read().decode('utf-8')
        st.text_area("Содержимое файла", content, height=200, disabled=True)
        
        if st.button("🎮 Сгенерировать из файла", use_container_width=True):
            with st.spinner("Обработка файла..."):
                # Сохраняем временный файл
                temp_path = Path("temp") / uploaded_file.name
                temp_path.parent.mkdir(exist_ok=True)
                temp_path.write_text(content, encoding='utf-8')
                
                try:
                    quest = st.session_state.generator.generate(str(temp_path))
                    st.session_state.current_quest = quest
                    st.success("Квест успешно сгенерирован!")
                    
                    # Удаляем временный файл
                    temp_path.unlink()
                except Exception as e:
                    st.error(f"Ошибка генерации: {e}")


def generate_basic_quest(genre, hero, goal, language, temperature):
    """Базовая генерация квеста"""
    with st.spinner("🎮 Генерируем квест... Это может занять 30-60 секунд"):
        try:
            scenario = ScenarioInput(
                genre=genre,
                hero=hero,
                goal=goal,
                language=language
            )
            
            config = GenerationConfig(
                temperature=temperature,
                use_rag=True
            )
            
            # Создаем прогресс-бар
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Уведомляем о начале генерации
            status_text.text("🚀 Запускаем генерацию квеста...")
            progress_bar.progress(0.1)
            
            # Реальная генерация
            quest = st.session_state.generator.generate(scenario.model_dump())
            
            # Сохраняем результат
            st.session_state.current_quest = quest
            st.session_state.quest_history.append({
                'timestamp': datetime.now(),
                'quest': quest,
                'type': 'basic'
            })
            
            # Автоматическое сохранение данных
            save_persistent_data()
            
            progress_bar.empty()
            status_text.empty()
            st.success("✅ Квест успешно сгенерирован!")
            
        except Exception as e:
            st.error(f"❌ Ошибка генерации: {e}")


def generate_advanced_quest(genre, hero, goal, with_logic, with_visuals, 
                          export_code, visual_style, enable_dynamic):
    """Расширенная генерация квеста"""
    # Проверяем, что integrated_generator инициализирован
    if st.session_state.integrated_generator is None:
        st.error("❌ Расширенный генератор не инициализирован!")
        st.info("Попробуйте перезагрузить страницу или использовать базовую генерацию")
        return
    
    with st.spinner("🚀 Запускаем расширенную генерацию..."):
        try:
            scenario = ScenarioInput(
                genre=genre,
                hero=hero,
                goal=goal,
                language="ru"
            )
            
            # Прогресс с этапами
            progress_container = st.container()
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                stages = [
                    (0.2, "📝 Базовая генерация квеста..."),
                    (0.4, "🧠 Добавление логики Story2Game...") if with_logic else None,
                    (0.6, "🎨 Создание визуализации SceneCraft...") if with_visuals else None,
                    (0.8, "💻 Генерация исполняемого кода...") if export_code else None,
                    (1.0, "✅ Финализация...")
                ]
                stages = [s for s in stages if s is not None]
                
                # Отображаем текущий этап
                status_text.text("🚀 Запускаем расширенную генерацию...")
                progress_bar.progress(0.1)
            
            # Реальная генерация - используем thread pool для асинхронного кода
            import concurrent.futures
            
            # Создаем уникальную директорию для этой генерации
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Удаляем недопустимые символы для имен папок в Windows
            import re
            quest_title = getattr(scenario, 'goal', 'quest')
            quest_title = re.sub(r'[<>:"/\\|?*]', '_', quest_title)
            quest_title = quest_title.replace(' ', '_')[:30]
            unique_output_dir = f"saved_quests/{quest_title}_{timestamp}"
            
            # Streamlit запускает свой event loop, поэтому используем thread pool
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    st.session_state.integrated_generator.generate_enhanced_quest(
                        scenario,
                        with_logic=with_logic,
                        with_visuals=with_visuals,
                        export_code=export_code,
                        output_dir=unique_output_dir
                    )
                )
                result = future.result(timeout=300)  # 5 минут таймаут
            
            # Сохраняем результат
            st.session_state.current_quest = result['quest']
            st.session_state.current_enhanced_result = result
            
            # Сохраняем в уникальную папку
            timestamp = datetime.now()
            quest_title = getattr(result['quest'], 'title', 'quest')
            # Удаляем недопустимые символы для имен папок в Windows
            quest_title = re.sub(r'[<>:"/\\|?*]', '_', quest_title)
            quest_title = quest_title.replace(' ', '_')[:30]
            unique_folder = f"{quest_title}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            save_dir = Path("saved_quests") / unique_folder
            
            # Сохраняем расширенный квест
            if hasattr(st.session_state, 'integrated_generator'):
                saved_path = st.session_state.integrated_generator.save_enhanced_quest(
                    result, str(save_dir)
                )
                result['saved_path'] = str(saved_path)
            
            st.session_state.quest_history.append({
                'timestamp': timestamp,
                'quest': result['quest'],
                'type': 'advanced',
                'enhancements': result['enhancements'],
                'saved_path': str(save_dir)
            })
            
            # Автоматическое сохранение данных
            save_persistent_data()
            
            progress_container.empty()
            st.success("✅ Расширенная генерация завершена!")
            st.info("📚 Результат сохранен в истории. Перейдите в раздел 'История' для просмотра.")
            
        except Exception as e:
            st.error(f"❌ Ошибка: {e}")
            import traceback
            st.code(traceback.format_exc())


def show_quest_result():
    """Отображение результата генерации"""
    quest = st.session_state.current_quest
    
    if not quest:
        st.warning("Квест не выбран для просмотра")
        return
    
    st.markdown("---")
    title = getattr(quest, 'title', 'Неизвестный квест')
    st.subheader(f"📖 {title}")
    
    # Метаданные квеста с безопасным доступом
    meta_cols = st.columns(4)
    with meta_cols[0]:
        genre = getattr(quest, 'genre', 'неизвестно')
        st.metric("Жанр", genre)
    with meta_cols[1]:
        scenes = getattr(quest, 'scenes', [])
        st.metric("Сцен", len(scenes) if scenes else 0)
    with meta_cols[2]:
        paths = getattr(quest, 'paths', [])
        st.metric("Путей", len(paths) if paths else "N/A")
    with meta_cols[3]:
        metadata = getattr(quest, 'metadata', {})
        gen_time = metadata.get('generation_time', 0) if metadata else 0
        st.metric("Время генерации", f"{gen_time:.1f}с")
    
    # Табы для разных представлений
    view_tabs = st.tabs(["📝 Сцены", "🗺️ Граф квеста", "💾 JSON", "📊 Статистика"])
    
    with view_tabs[0]:
        show_scenes_view(quest)
    
    with view_tabs[1]:
        show_quest_graph(quest)
    
    with view_tabs[2]:
        show_json_view(quest)
    
    with view_tabs[3]:
        show_quest_statistics(quest)
    
    # Кнопки действий
    import time
    quest_title = getattr(quest, 'title', 'unknown').replace(' ', '_').replace(':', '').replace('.', '')[:20]
    button_base_key = f"{quest_title}_{id(quest)}_{int(time.time() * 1000000) % 1000000}"
    
    action_cols = st.columns(4)
    with action_cols[0]:
        if st.button("💾 Сохранить", use_container_width=True, key=f"save_quest_{button_base_key}"):
            save_quest(quest)
    with action_cols[1]:
        if st.button("📤 Экспорт", use_container_width=True, key=f"export_quest_{button_base_key}"):
            export_quest(quest)
    with action_cols[2]:
        if st.button("🎮 Играть", use_container_width=True, key=f"play_quest_{button_base_key}"):
            st.info("Режим игры в разработке")
    with action_cols[3]:
        if st.button("🔄 Новый квест", use_container_width=True, key=f"new_quest_{button_base_key}"):
            st.session_state.current_quest = None
            st.rerun()


def show_scenes_view(quest):
    """Отображение сцен квеста"""
    scenes = getattr(quest, 'scenes', [])
    
    if not scenes:
        st.warning("Сцены не найдены в квесте")
        return
    
    # Выбор режима просмотра
    view_mode = st.radio(
        "Режим просмотра:",
        ["📋 Все сцены", "🎮 Интерактивный квест"],
        horizontal=True
    )
    
    if view_mode == "📋 Все сцены":
        # Режим просмотра всех сцен
        for i, scene in enumerate(scenes):
            # Безопасное получение атрибутов сцены
            scene_id = getattr(scene, 'scene_id', f'scene_{i+1}')
            scene_text = getattr(scene, 'text', 'Текст сцены недоступен')
            scene_mood = getattr(scene, 'mood', None)
            scene_location = getattr(scene, 'location', None)
            scene_choices = getattr(scene, 'choices', [])
            scene_image = getattr(scene, 'image_prompt', None)
            
            with st.expander(f"Сцена {i+1}: {scene_id}", expanded=(i==0)):
                # Проверяем наличие изображения
                # Для расширенной генерации изображения могут быть в другом месте
                if hasattr(st.session_state, 'current_enhanced_result') and st.session_state.current_enhanced_result and 'visualization' in st.session_state.current_enhanced_result.get('enhancements', {}):
                    viz_data = st.session_state.current_enhanced_result['enhancements']['visualization']
                    # Ищем визуализацию для текущей сцены
                    for scene_viz in viz_data.get('scenes', []):
                        if scene_viz['scene_id'] == scene_id:
                            if 'image_paths' in scene_viz and len(scene_viz['image_paths']) > 0:
                                try:
                                    # Берем первое изображение (view_0.png)
                                    view_0_path = scene_viz['image_paths'][0]
                                    
                                    # Определяем, работаем в Streamlit Cloud или локально
                                    is_cloud = os.environ.get('STREAMLIT_CLOUD', 'false').lower() == 'true'
                                    
                                    if is_cloud:
                                        # В облаке используем GitHub URL
                                        image_url = get_github_raw_url(view_0_path, use_github=True)
                                        st.image(image_url, use_container_width=True)
                                    else:
                                        # Локально открываем файл
                                        path_obj = Path(view_0_path)
                                        if path_obj.exists():
                                            image = Image.open(path_obj)
                                            st.image(image, use_container_width=True)
                                        else:
                                            st.warning(f"Изображение не найдено: {view_0_path}")
                                except Exception as e:
                                    st.error(f"Ошибка при загрузке изображения: {e}")
                            break
                # Для базовой генерации
                elif hasattr(scene, 'image_prompt') and scene.image_prompt:
                    st.info("🎨 Изображение доступно только в расширенном режиме генерации")
                
                st.markdown(f"**Текст сцены:**")
                st.write(scene_text)
                
                col1, col2 = st.columns(2)
                with col1:
                    if scene_mood:
                        st.info(f"💭 **Настроение:** {scene_mood}")
                with col2:
                    if scene_location:
                        st.info(f"📍 **Локация:** {scene_location}")
                
                if scene_image:
                    with st.expander("🎨 Промпт для изображения"):
                        st.caption(scene_image)
                
                st.markdown("**Варианты выбора:**")
                if scene_choices:
                    for j, choice in enumerate(scene_choices):
                        choice_text = getattr(choice, 'text', f'Выбор {j+1}')
                        next_scene = getattr(choice, 'next_scene', 'неизвестно')
                        st.write(f"{j+1}. {choice_text} → *{next_scene}*")
                else:
                    st.info("Конец сцены")
    
    else:
        # Интерактивный режим квеста
        if 'current_scene_index' not in st.session_state:
            st.session_state.current_scene_index = 0
        
        current_index = st.session_state.current_scene_index
        
        # Прогресс бар
        progress = (current_index + 1) / len(scenes)
        st.progress(progress, text=f"Прогресс: {current_index + 1} из {len(scenes)} сцен")
        
        if current_index < len(scenes):
            scene = scenes[current_index]
            
            # Безопасное получение атрибутов сцены
            scene_id = getattr(scene, 'scene_id', f'scene_{current_index+1}')
            scene_text = getattr(scene, 'text', 'Текст сцены недоступен')
            scene_mood = getattr(scene, 'mood', None)
            scene_location = getattr(scene, 'location', None)
            scene_choices = getattr(scene, 'choices', [])
            
            # Отображение сцены
            st.markdown(f"### Сцена {current_index + 1}: {scene_id}")
            
            # Проверяем наличие изображения
            # Для расширенной генерации изображения могут быть в другом месте
            if hasattr(st.session_state, 'current_enhanced_result') and st.session_state.current_enhanced_result and 'visualization' in st.session_state.current_enhanced_result.get('enhancements', {}):
                viz_data = st.session_state.current_enhanced_result['enhancements']['visualization']
                # Ищем визуализацию для текущей сцены
                for scene_viz in viz_data.get('scenes', []):
                    if scene_viz['scene_id'] == scene_id:
                        if 'image_paths' in scene_viz and len(scene_viz['image_paths']) > 0:
                            try:
                                # Берем первое изображение (view_0.png)
                                view_0_path = scene_viz['image_paths'][0]
                                
                                # Определяем, работаем в Streamlit Cloud или локально
                                is_cloud = os.environ.get('STREAMLIT_CLOUD', 'false').lower() == 'true'
                                
                                if is_cloud:
                                    # В облаке используем GitHub URL
                                    image_url = get_github_raw_url(view_0_path, use_github=True)
                                    st.image(image_url, use_container_width=True)
                                else:
                                    # Локально открываем файл
                                    path_obj = Path(view_0_path)
                                    if path_obj.exists():
                                        image = Image.open(path_obj)
                                        st.image(image, use_container_width=True)
                                    else:
                                        st.warning(f"Изображение не найдено: {view_0_path}")
                            except Exception as e:
                                st.error(f"Ошибка при загрузке изображения: {e}")
                        break
            # Для базовой генерации
            elif hasattr(scene, 'image_prompt') and scene.image_prompt:
                st.info("🎨 Изображение доступно только в расширенном режиме генерации")
            
            # Информация о локации и настроении
            col1, col2 = st.columns(2)
            with col1:
                if scene_location:
                    st.info(f"📍 **Локация:** {scene_location}")
            with col2:
                if scene_mood:
                    st.info(f"💭 **Настроение:** {scene_mood}")
            
            # Текст сцены
            st.markdown("---")
            st.write(scene_text)
            st.markdown("---")
            
            # Варианты выбора
            if scene_choices:
                st.markdown("**Что вы будете делать?**")
                for j, choice in enumerate(scene_choices):
                    choice_text = getattr(choice, 'text', f'Выбор {j+1}')
                    next_scene = getattr(choice, 'next_scene', 'неизвестно')
                    
                    # Находим индекс следующей сцены
                    next_index = None
                    for idx, s in enumerate(scenes):
                        if getattr(s, 'scene_id', f'scene_{idx+1}') == next_scene:
                            next_index = idx
                            break
                    
                    if st.button(f"➤ {choice_text}", key=f"choice_{current_index}_{j}", use_container_width=True):
                        if next_index is not None:
                            st.session_state.current_scene_index = next_index
                            st.rerun()
                        else:
                            st.warning(f"Сцена '{next_scene}' не найдена")
            else:
                st.success("🎯 Квест завершен!")
                if st.button("🔄 Начать заново", use_container_width=True):
                    st.session_state.current_scene_index = 0
                    st.rerun()
        else:
            st.error("Ошибка: неверный индекс сцены")
            if st.button("🔄 Начать заново", use_container_width=True):
                st.session_state.current_scene_index = 0
                st.rerun()


def show_quest_graph(quest):
    """Визуализация графа квеста"""
    import networkx as nx
    
    # Создаем граф
    G = nx.DiGraph()
    
    # Добавляем узлы
    for scene in quest.scenes:
        G.add_node(scene.scene_id, 
                  label=f"{scene.scene_id}\n{scene.text[:30]}...")
    
    # Добавляем рёбра
    edge_labels = {}
    for scene in quest.scenes:
        for choice in scene.choices:
            if choice.next_scene:
                # Добавляем узел для next_scene, если его еще нет
                if choice.next_scene not in G.nodes():
                    # Специальные узлы (например, "end")
                    if choice.next_scene == "end":
                        G.add_node(choice.next_scene, label="Конец")
                    else:
                        G.add_node(choice.next_scene, label=choice.next_scene)
                
                G.add_edge(scene.scene_id, choice.next_scene)
                edge_labels[(scene.scene_id, choice.next_scene)] = choice.text[:20] + "..."
    
    # Визуализация с plotly
    pos = nx.spring_layout(G, k=2, iterations=50)
    
    # Создаем фигуру
    fig = go.Figure()
    
    # Добавляем рёбра
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        fig.add_trace(go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode='lines',
            line=dict(width=1, color='gray'),
            showlegend=False
        ))
    
    # Добавляем узлы
    node_x = []
    node_y = []
    node_text = []
    
    for node in G.nodes():
        if node in pos:  # Проверяем, что позиция существует
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            # Получаем label или используем ID узла как fallback
            node_label = G.nodes[node].get('label', node)
            node_text.append(node_label)
    
    fig.add_trace(go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers+text',
        marker=dict(
            size=30,
            color='#667eea',
            line=dict(width=2, color='white')
        ),
        text=node_text,
        textposition='top center',
        showlegend=False
    ))
    
    fig.update_layout(
        showlegend=False,
        hovermode='closest',
        margin=dict(b=0,l=0,r=0,t=0),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=600
    )
    
    # Используем уникальный ключ на основе ID квеста и времени
    import time
    quest_id = getattr(quest, 'title', 'unknown').replace(' ', '_').replace(':', '').replace('.', '')[:20]
    unique_id = f"{quest_id}_{id(quest)}_{int(time.time() * 1000000) % 1000000}"
    st.plotly_chart(fig, use_container_width=True, key=f"quest_graph_{unique_id}")


def show_json_view(quest):
    """Отображение JSON представления"""
    quest_dict = quest.model_dump()
    json_str = json.dumps(quest_dict, ensure_ascii=False, indent=2)
    
    # Ensure proper UTF-8 encoding for display
    st.code(json_str, language='json')
    
    # Кнопка копирования
    import time
    quest_title = getattr(quest, 'title', 'unknown').replace(' ', '_').replace(':', '').replace('.', '')[:20]
    unique_key = f"download_json_{quest_title}_{id(quest)}_{int(time.time() * 1000000) % 1000000}"
    st.download_button(
        label="📥 Скачать JSON",
        data=json_str,
        file_name=f"quest_{quest.title.replace(' ', '_')}.json",
        mime="application/json",
        key=unique_key
    )


def show_quest_statistics(quest):
    """Статистика квеста"""
    import time
    quest_title = getattr(quest, 'title', 'unknown').replace(' ', '_').replace(':', '').replace('.', '')[:20]
    base_key = f"{quest_title}_{id(quest)}_{int(time.time() * 1000000) % 1000000}"
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Статистика по сценам
        st.subheader("📊 Статистика сцен")
        
        # Количество выборов в сценах
        choices_data = pd.DataFrame({
            'Сцена': [s.scene_id for s in quest.scenes],
            'Выборов': [len(s.choices) for s in quest.scenes]
        })
        
        fig = px.bar(choices_data, x='Сцена', y='Выборов', 
                    title="Количество выборов по сценам")
        st.plotly_chart(fig, use_container_width=True, key=f"choices_bar_chart_{base_key}")
        
        # Длина текста сцен
        text_lengths = pd.DataFrame({
            'Сцена': [s.scene_id for s in quest.scenes],
            'Длина текста': [len(s.text) for s in quest.scenes]
        })
        
        fig2 = px.line(text_lengths, x='Сцена', y='Длина текста',
                      title="Длина текста сцен", markers=True)
        st.plotly_chart(fig2, use_container_width=True, key=f"text_length_line_chart_{base_key}")
    
    with col2:
        # Статистика путей
        st.subheader("🛤️ Анализ путей")
        
        if quest.paths:
            paths_data = pd.DataFrame({
                'Путь': [p.path_id for p in quest.paths],
                'Длина': [p.length for p in quest.paths],
                'Исход': [p.outcome or 'неизвестно' for p in quest.paths]
            })
            
            # График длин путей
            fig3 = px.bar(paths_data, x='Путь', y='Длина', color='Исход',
                         title="Длина различных путей")
            st.plotly_chart(fig3, use_container_width=True, key=f"paths_length_bar_chart_{base_key}")
            
            # Статистика исходов
            outcome_counts = paths_data['Исход'].value_counts()
            fig4 = px.pie(values=outcome_counts.values, names=outcome_counts.index,
                         title="Распределение исходов")
            st.plotly_chart(fig4, use_container_width=True, key=f"outcomes_pie_chart_{base_key}")


def show_enhanced_results(result):
    """Отображение результатов расширенной генерации"""
    quest = result.get('quest')
    if quest:
        # Основная информация о квесте
        with st.container():
            st.markdown(f"### {getattr(quest, 'title', 'Неизвестный квест')}")
            
            col_info1, col_info2, col_info3, col_info4 = st.columns(4)
            with col_info1:
                st.info(f"🎭 **Жанр:** {getattr(quest, 'genre', 'н/д')}")
            with col_info2:
                st.info(f"🧑 **Герой:** {getattr(quest, 'hero', 'н/д')}")
            with col_info3:
                st.info(f"🎯 **Цель:** {getattr(quest, 'goal', 'н/д')}")
            with col_info4:
                scenes = getattr(quest, 'scenes', [])
                st.info(f"🎬 **Сцен:** {len(scenes)}")
    
    # Проверяем наличие улучшений
    enhancements = result.get('enhancements', {})
    
    # Табы для разных улучшений
    tabs = ["📖 Квест"]
    if 'logic' in enhancements:
        tabs.append("🧠 Логика")
    if 'visualization' in enhancements:
        tabs.append("🎨 Визуализация")
    if 'generated_code' in enhancements:
        tabs.append("💻 Код")
    
    tabs_ui = st.tabs(tabs)
    
    # Базовый квест - используем квест из result
    with tabs_ui[0]:
        # Временно устанавливаем current_quest для show_quest_result
        temp_quest = st.session_state.current_quest
        st.session_state.current_quest = result.get('quest', temp_quest)
        show_quest_result()
        st.session_state.current_quest = temp_quest
    
    # Логика
    if '🧠 Логика' in tabs:
        with tabs_ui[tabs.index('🧠 Логика')]:
            if 'logic' in enhancements:
                show_logic_view(enhancements['logic'])
            else:
                st.info("Данные о логике недоступны")
    
    # Визуализация
    if '🎨 Визуализация' in tabs:
        with tabs_ui[tabs.index('🎨 Визуализация')]:
            if 'visualization' in enhancements:
                show_visualization_view(enhancements['visualization'])
            else:
                st.info("Данные о визуализации недоступны")
    
    # Код
    if '💻 Код' in tabs:
        with tabs_ui[tabs.index('💻 Код')]:
            if 'generated_code' in enhancements:
                show_code_view(enhancements['generated_code'])
            else:
                st.info("Сгенерированный код недоступен")


def show_logic_view(logic_data):
    """Отображение логики Story2Game"""
    st.subheader("🧠 Структурированная логика")
    
    # Мировое состояние
    with st.expander("🌍 Начальное состояние мира"):
        st.json(logic_data['world_state'])
    
    # Предусловия и эффекты
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Предусловия")
        for action_id, preconditions in list(logic_data['preconditions'].items())[:5]:
            if preconditions:
                st.write(f"**{action_id}:**")
                for precond in preconditions:
                    st.write(f"- {precond}")
    
    with col2:
        st.subheader("✨ Эффекты")
        for action_id, effects in list(logic_data['effects'].items())[:5]:
            if effects:
                st.write(f"**{action_id}:**")
                for effect in effects:
                    st.write(f"- {effect}")
    
    # Граф действий
    st.subheader("🔀 Граф доступности действий")
    action_graph_df = []
    for scene_id, actions in logic_data['action_graph'].items():
        for action in actions:
            action_graph_df.append({
                'Сцена': scene_id,
                'Действие': action['action_id'],
                'Доступно': '✅' if action['available'] else '❌',
                'Следующая сцена': action['next_scene']
            })
    
    if action_graph_df:
        df = pd.DataFrame(action_graph_df)
        st.dataframe(df, use_container_width=True)


def show_visualization_view(viz_data):
    """Отображение визуализации SceneCraft"""
    st.subheader("🎨 Визуализация сцен")
    
    st.info(f"Визуализировано сцен: {len(viz_data['scenes'])}")
    st.metric("Согласованность визуалов", 
              f"{viz_data['enhanced_features']['visual_consistency_score']:.0%}")
    
    # Показываем визуализации всех сцен
    for scene_viz in viz_data['scenes']:  # Все сцены
        with st.expander(f"Сцена {scene_viz['scene_id']}", expanded=False):
            # Приоритет изображений: view_0.png из image_paths > composite_path
            image_shown = False
            
            # Сначала пробуем view_0.png из image_paths (лучшее качество)
            if 'image_paths' in scene_viz and len(scene_viz['image_paths']) > 0:
                try:
                    # Берем первое изображение (view_0.png)
                    view_0_path = scene_viz['image_paths'][0]
                    
                    # Определяем, работаем в Streamlit Cloud или локально
                    is_cloud = os.environ.get('STREAMLIT_CLOUD', 'false').lower() == 'true'
                    
                    if is_cloud:
                        # В облаке используем GitHub URL
                        image_url = get_github_raw_url(view_0_path, use_github=True)
                        st.image(image_url, caption="Визуализация сцены", 
                                use_container_width=True)
                        image_shown = True
                    else:
                        # Локально открываем файл
                        path_obj = Path(view_0_path)
                        if path_obj.exists():
                            image = Image.open(path_obj)
                            st.image(image, caption="Визуализация сцены", 
                                    use_container_width=True)
                            image_shown = True
                        else:
                            st.warning(f"Изображение не найдено: {view_0_path}")
                except Exception as e:
                    st.error(f"Ошибка загрузки изображения: {e}")
            
            # Если не найдены view_0 варианты, пробуем композитное изображение
            if not image_shown and 'composite_path' in scene_viz:
                try:
                    composite_path = scene_viz['composite_path']
                    
                    # Определяем, работаем в Streamlit Cloud или локально
                    is_cloud = os.environ.get('STREAMLIT_CLOUD', 'false').lower() == 'true'
                    
                    if is_cloud:
                        # В облаке используем GitHub URL
                        image_url = get_github_raw_url(composite_path, use_github=True)
                        st.image(image_url, caption="Многоракурсная визуализация", 
                                use_container_width=True)
                        image_shown = True
                    else:
                        # Локально открываем файл
                        path_obj = Path(composite_path)
                        if path_obj.exists():
                            image = Image.open(path_obj)
                            st.image(image, caption="Многоракурсная визуализация", 
                                    use_container_width=True)
                            image_shown = True
                        else:
                            st.warning(f"Композитное изображение не найдено: {composite_path}")
                except Exception as e:
                    st.error(f"Ошибка при загрузке композитного изображения: {e}")
            
            # Если ничего не найдено
            if not image_shown:
                st.info("Изображение недоступно")
            
            # Макет сцены внизу в свернутом виде
            if 'layout_path' in scene_viz:
                with st.expander("🏗️ Макет сцены", expanded=False):
                    try:
                        with open(scene_viz['layout_path'], 'r', encoding='utf-8') as f:
                            layout = json.load(f)
                        st.json(layout)
                    except:
                        st.info("Макет недоступен")


def show_code_view(generated_code):
    """Отображение сгенерированного кода"""
    st.subheader("💻 Сгенерированный код")
    
    # Выбор языка
    lang = st.selectbox("Язык программирования", ["Python", "JavaScript"])
    
    # Показываем код
    st.code(generated_code, language=lang.lower())
    
    # Кнопка скачивания
    file_ext = "py" if lang == "Python" else "js"
    st.download_button(
        label=f"📥 Скачать {lang} код",
        data=generated_code,
        file_name=f"quest_logic.{file_ext}",
        mime="text/plain"
    )


def show_analytics_page():
    """Страница аналитики"""
    st.header("📊 Аналитика генерации")
    
    if not st.session_state.quest_history:
        st.info("Пока нет данных для анализа. Сгенерируйте несколько квестов!")
        return
    
    # Общая статистика
    st.subheader("📈 Общая статистика")
    
    metrics = st.columns(4)
    with metrics[0]:
        st.metric("Всего квестов", len(st.session_state.quest_history))
    with metrics[1]:
        total_scenes = 0
        valid_quests = 0
        for h in st.session_state.quest_history:
            scenes = getattr(h['quest'], 'scenes', [])
            if scenes:
                total_scenes += len(scenes)
                valid_quests += 1
        avg_scenes = total_scenes / valid_quests if valid_quests > 0 else 0
        st.metric("Среднее кол-во сцен", f"{avg_scenes:.1f}")
    with metrics[2]:
        basic_count = sum(1 for h in st.session_state.quest_history if h['type'] == 'basic')
        st.metric("Базовых генераций", basic_count)
    with metrics[3]:
        advanced_count = sum(1 for h in st.session_state.quest_history if h['type'] == 'advanced')
        st.metric("Расширенных генераций", advanced_count)
    
    # Графики
    col1, col2 = st.columns(2)
    
    with col1:
        # График по жанрам
        genres = []
        for h in st.session_state.quest_history:
            genre = getattr(h['quest'], 'genre', 'неизвестно')
            genres.append(genre)
        genre_counts = pd.Series(genres).value_counts()
        
        fig = px.pie(values=genre_counts.values, names=genre_counts.index,
                    title="Распределение по жанрам")
        import time
        analytics_key = f"analytics_genres_pie_{int(time.time() * 1000000) % 1000000}"
        st.plotly_chart(fig, use_container_width=True, key=analytics_key)
    
    with col2:
        # График по времени
        times = [h['timestamp'] for h in st.session_state.quest_history]
        times_df = pd.DataFrame({'timestamp': times, 'count': 1})
        times_df['date'] = times_df['timestamp'].dt.date
        daily_counts = times_df.groupby('date')['count'].sum().reset_index()
        
        fig = px.line(daily_counts, x='date', y='count',
                     title="Квесты по дням", markers=True)
        analytics_timeline_key = f"analytics_timeline_{int(time.time() * 1000000) % 1000000}"
        st.plotly_chart(fig, use_container_width=True, key=analytics_timeline_key)
    
    # Детальная аналитика
    st.subheader("🔍 Детальный анализ")
    
    # Таблица квестов
    quest_data = []
    for h in st.session_state.quest_history:
        quest = h['quest']
        scenes = getattr(quest, 'scenes', [])
        metadata = getattr(quest, 'metadata', {})
        quest_data.append({
            'Время': h['timestamp'].strftime('%Y-%m-%d %H:%M'),
            'Название': getattr(quest, 'title', 'Неизвестный квест'),
            'Жанр': getattr(quest, 'genre', 'неизвестно'),
            'Сцен': len(scenes) if scenes else 0,
            'Тип': h['type'],
            'Время генерации': f"{metadata.get('generation_time', 0):.1f}с"
        })
    
    df = pd.DataFrame(quest_data)
    st.dataframe(df, use_container_width=True)


def show_history_page():
    """Страница сцен"""
    st.header("🎬 Сцены квестов")
    
    if not st.session_state.quest_history:
        st.info("Нет сохраненных сцен. Сгенерируйте свой первый квест!")
        return
    
    # Статистика вверху страницы
    st.markdown("### 📊 Общая статистика")
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    
    with col_stat1:
        st.metric("Всего квестов", len(st.session_state.quest_history))
    
    with col_stat2:
        basic_count = len([h for h in st.session_state.quest_history if h['type'] == 'basic'])
        st.metric("Базовых", basic_count)
    
    with col_stat3:
        advanced_count = len([h for h in st.session_state.quest_history if h['type'] == 'advanced'])
        st.metric("Расширенных", advanced_count)
    
    with col_stat4:
        # Средняя длина квеста
        total_scenes = sum(len(getattr(h['quest'], 'scenes', [])) for h in st.session_state.quest_history)
        avg_scenes = total_scenes / len(st.session_state.quest_history) if st.session_state.quest_history else 0
        st.metric("Средняя длина", f"{avg_scenes:.1f} сцен")
    
    st.markdown("---")
    
    # Фильтры
    col1, col2, col3 = st.columns(3)
    with col1:
        # Безопасное получение жанров
        genres = set()
        for h in st.session_state.quest_history:
            try:
                genre = getattr(h['quest'], 'genre', 'неизвестно')
                if isinstance(genre, str):
                    genres.add(genre)
            except:
                genres.add('неизвестно')
        
        filter_genre = st.selectbox("Фильтр по жанру", 
                                   ["Все"] + list(genres))
    with col2:
        filter_type = st.selectbox("Тип генерации", ["Все", "basic", "advanced"])
    with col3:
        sort_by = st.selectbox("Сортировка", ["Новые первыми", "Старые первыми", "По названию"])
    
    # Применяем фильтры
    filtered_history = st.session_state.quest_history
    
    if filter_genre != "Все":
        filtered_history = [h for h in filtered_history if getattr(h['quest'], 'genre', 'неизвестно') == filter_genre]
    
    if filter_type != "Все":
        filtered_history = [h for h in filtered_history if h['type'] == filter_type]
    
    # Сортировка
    if sort_by == "Новые первыми":
        filtered_history = sorted(filtered_history, key=lambda x: x['timestamp'], reverse=True)
    elif sort_by == "Старые первыми":
        filtered_history = sorted(filtered_history, key=lambda x: x['timestamp'])
    else:
        filtered_history = sorted(filtered_history, key=lambda x: getattr(x['quest'], 'title', 'Неизвестный квест'))
    
    # Автоматически выбираем первый квест, если ничего не выбрано
    if filtered_history:
        # Проверяем, что индекс в пределах отфильтрованного списка
        if hasattr(st.session_state, 'viewing_quest_index'):
            if st.session_state.viewing_quest_index >= len(filtered_history):
                st.session_state.viewing_quest_index = 0
        
        # Если квест не выбран, выбираем первый
        if not st.session_state.current_quest or not hasattr(st.session_state, 'viewing_quest_index'):
            st.session_state.current_quest = filtered_history[0]['quest']
            st.session_state.viewing_quest_index = 0
            if 'enhancements' in filtered_history[0]:
                st.session_state.current_enhanced_result = {
                    'quest': filtered_history[0]['quest'],
                    'enhancements': filtered_history[0]['enhancements']
                }
    
    # Отображение квестов
    
    # Проверяем есть ли выбранный квест
    if st.session_state.current_quest and hasattr(st.session_state, 'viewing_quest_index'):
        # Двухколоночный вид
        col_list, col_view = st.columns([1, 2])
        
        # Левая колонка - список квестов (компактный)
        with col_list:
            st.markdown("### 📋 Список квестов")
            
            # Контейнер с прокруткой для списка
            with st.container(height=600):
                for i, history_item in enumerate(filtered_history):
                    quest = history_item['quest']
                    title = getattr(quest, 'title', 'Неизвестный квест')
                    
                    # Компактная карточка квеста
                    if i == st.session_state.viewing_quest_index:
                        # Выделяем текущий квест
                        st.success(f"▶ **{title}**")
                        st.caption(f"{history_item['timestamp'].strftime('%d.%m')}")
                    else:
                        col_title, col_actions = st.columns([3, 1])
                        with col_title:
                            if st.button(f"{title}", key=f"quick_view_{i}", use_container_width=True):
                                st.session_state.current_quest = quest
                                st.session_state.viewing_quest_index = i
                                if 'enhancements' in history_item:
                                    st.session_state.current_enhanced_result = {
                                        'quest': quest,
                                        'enhancements': history_item['enhancements']
                                    }
                                st.rerun()
                            st.caption(f"{history_item['timestamp'].strftime('%d.%m')}")
                        
                        with col_actions:
                            # Кнопка удаления - показываем только если не в режиме просмотра
                            view_only_mode = os.getenv('VIEW_ONLY_MODE', 'false').lower() == 'true'
                            if not view_only_mode:
                                if st.button("🗑️", key=f"quick_delete_{i}", help="Удалить"):
                                    st.session_state.quest_history.remove(history_item)
                                    save_persistent_data()
                                    if st.session_state.viewing_quest_index == i:
                                        st.session_state.current_quest = None
                                        del st.session_state.viewing_quest_index
                                    st.rerun()
        
        # Правая колонка - детальный просмотр
        with col_view:
            # Заголовок с кнопками действий
            col_header1, col_header2, col_header3 = st.columns([8, 1, 1])
            with col_header1:
                st.markdown("### 🎮 Просмотр квеста")
            with col_header2:
                if st.button("💾", key="export_view", help="Экспорт"):
                    export_quest(st.session_state.current_quest)
            with col_header3:
                if st.button("✖", key="close_view", help="Закрыть"):
                    st.session_state.current_quest = None
                    if hasattr(st.session_state, 'viewing_quest_index'):
                        del st.session_state.viewing_quest_index
                    if hasattr(st.session_state, 'current_enhanced_result'):
                        st.session_state.current_enhanced_result = None
                    st.rerun()
            
            # Отображение квеста
            is_enhanced = hasattr(st.session_state, 'current_enhanced_result') and st.session_state.current_enhanced_result
            
            if is_enhanced:
                show_enhanced_results(st.session_state.current_enhanced_result)
            else:
                # Организованный показ базового квеста
                quest = st.session_state.current_quest
                
                # Основная информация
                with st.container():
                    st.markdown(f"### {getattr(quest, 'title', 'Неизвестный квест')}")
                    
                    col_info1, col_info2, col_info3, col_info4 = st.columns(4)
                    with col_info1:
                        st.info(f"🎭 **Жанр:** {getattr(quest, 'genre', 'н/д')}")
                    with col_info2:
                        st.info(f"🧑 **Герой:** {getattr(quest, 'hero', 'н/д')}")
                    with col_info3:
                        st.info(f"🎯 **Цель:** {getattr(quest, 'goal', 'н/д')}")
                    with col_info4:
                        scenes = getattr(quest, 'scenes', [])
                        st.info(f"🎬 **Сцен:** {len(scenes)}")
                
                # Вкладки с разными представлениями
                tabs = st.tabs(["🎬 Сцены", "🗺️ Граф", "📄 JSON", "📊 Статистика"])
                
                with tabs[0]:
                    show_scenes_view(quest)
                
                with tabs[1]:
                    show_quest_graph(quest)
                
                with tabs[2]:
                    show_json_view(quest)
                
                with tabs[3]:
                    show_quest_statistics(quest)


def show_settings_page():
    """Страница настроек"""
    st.header("⚙️ Настройки")
    
    # Статус API ключей
    st.subheader("🔑 Статус API ключей")
    
    import os
    openai_status = "✅ Настроен" if os.getenv("OPENAI_API_KEY") else "❌ Не найден в .env"
    anthropic_status = "✅ Настроен" if os.getenv("ANTHROPIC_API_KEY") else "❌ Не найден в .env"
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**OpenAI API:** {openai_status}")
    with col2:
        st.info(f"**Anthropic API:** {anthropic_status}")
    
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        st.warning("⚠️ Настройте API ключи в файле `.env` для работы системы")
        st.code("""
# Добавьте в файл .env:
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
        """)
    
    # Режим отладки
    st.subheader("🐛 Режим отладки")
    
    if 'debug_mode' not in st.session_state:
        st.session_state.debug_mode = False
    
    debug_mode = st.checkbox("Включить режим отладки", value=st.session_state.debug_mode)
    st.session_state.debug_mode = debug_mode
    
    # Принудительное использование GitHub URLs
    if 'force_github_urls' not in st.session_state:
        st.session_state.force_github_urls = os.environ.get('FORCE_GITHUB_URLS', 'false').lower() == 'true'
    
    force_github = st.checkbox("Принудительно использовать GitHub URLs для изображений", 
                              value=st.session_state.force_github_urls,
                              help="Включите эту опцию, если работаете в Streamlit Cloud и изображения не отображаются")
    
    if force_github != st.session_state.force_github_urls:
        st.session_state.force_github_urls = force_github
        os.environ['FORCE_GITHUB_URLS'] = 'true' if force_github else 'false'
        os.environ['STREAMLIT_CLOUD'] = 'true' if force_github else os.environ.get('STREAMLIT_CLOUD', 'false')
        st.rerun()
    
    if debug_mode:
        st.info("Режим отладки включен. Информация о путях к изображениям будет отображаться в боковой панели.")
        
        # Отображаем информацию об окружении
        is_cloud = os.environ.get('STREAMLIT_CLOUD', 'false').lower() == 'true'
        st.write(f"**Окружение:** {'Streamlit Cloud (GitHub URLs активны)' if is_cloud else 'Локальное (локальные файлы)'}")
        
        # Проверяем переменные окружения для определения Streamlit Cloud
        cloud_vars = {
            'STREAMLIT_SHARING_MODE': os.environ.get('STREAMLIT_SHARING_MODE', 'Not set'),
            'STREAMLIT_SERVER_ADDRESS': os.environ.get('STREAMLIT_SERVER_ADDRESS', 'Not set'),
            'STREAMLIT_SERVER_HEADLESS': os.environ.get('STREAMLIT_SERVER_HEADLESS', 'Not set'),
            'STREAMLIT_CLOUD': os.environ.get('STREAMLIT_CLOUD', 'Not set'),
            'FORCE_GITHUB_URLS': os.environ.get('FORCE_GITHUB_URLS', 'Not set')
        }
        
        with st.expander("Переменные окружения"):
            for var, value in cloud_vars.items():
                st.write(f"**{var}:** {value}")
                
        # Тестовый пример преобразования пути
        with st.expander("Тест преобразования путей"):
            test_path = st.text_input("Введите путь для тестирования:", 
                                    value="saved_quests\\Покинуть_мфц_20250804_224312\\легенда_о_покинуть_мфц_20250804_224346\\scene_1\\view_0.png")
            if test_path:
                github_url = get_github_raw_url(test_path, use_github=is_cloud)
                st.code(github_url)
                
                # Проверяем, существует ли файл локально
                local_path = Path(test_path.replace('\\', '/'))
                if local_path.exists():
                    st.success(f"✅ Файл существует локально: {local_path}")
                else:
                    st.warning(f"⚠️ Файл не найден локально: {local_path}")
    
    # Настройки генерации
    st.subheader("🎯 Настройки генерации")
    
    current_model = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
    current_temp = float(os.getenv("DEFAULT_TEMPERATURE", "0.8"))
    current_tokens = int(os.getenv("DEFAULT_MAX_TOKENS", "2000"))
    
    st.info(f"**Текущая модель:** {current_model}")
    st.info(f"**Температура:** {current_temp}")
    st.info(f"**Макс. токенов:** {current_tokens}")
    
    st.markdown("💡 **Для изменения настроек отредактируйте файл `.env`:**")
    st.code(f"""
# Настройки генерации в .env:
DEFAULT_MODEL={current_model}
DEFAULT_TEMPERATURE={current_temp}
DEFAULT_MAX_TOKENS={current_tokens}
    """)
    
    # Информация о системе
    st.subheader("ℹ️ Информация о системе")
    
    log_level = os.getenv("LOG_LEVEL", "INFO")
    api_host = os.getenv("API_HOST", "0.0.0.0")
    api_port = os.getenv("API_PORT", "8000")
    
    st.info(f"**Уровень логирования:** {log_level}")
    st.info(f"**API сервер:** {api_host}:{api_port}")
    
    st.markdown("💡 **Дополнительные настройки в `.env`:**")
    st.code(f"""
# Системные настройки:
LOG_LEVEL={log_level}
API_HOST={api_host}
API_PORT={api_port}
CHROMA_PERSIST_DIRECTORY=./data/chroma
    """)
    
    # База знаний
    st.subheader("📚 База знаний")
    
    if st.button("🔄 Обновить базу знаний"):
        with st.spinner("Обновление базы знаний..."):
            # Переинициализация knowledge base
            st.session_state.generator.knowledge_base = KnowledgeBase()
            st.success("База знаний обновлена!")
    
    # Управление данными сессии
    st.subheader("💾 Управление данными")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Очистить историю", use_container_width=True):
            st.session_state.quest_history = []
            st.session_state.current_quest = None
            save_persistent_data()  # Сохраняем изменения
            st.success("История очищена!")
            st.rerun()
    
    with col2:
        if st.button("💾 Принудительное сохранение", use_container_width=True):
            save_persistent_data()
            st.success("Данные сохранены!")
    
    # Информация о сохраненных данных
    persistent_file = Path("saved_quests") / "session_data.json"
    if persistent_file.exists():
        file_size = persistent_file.stat().st_size
        st.info(f"📁 Файл сессии: {file_size} байт")
        st.info(f"📍 Путь: {persistent_file.absolute()}")
    else:
        st.info("📁 Файл сессии не найден")
    
    # Экспорт/Импорт
    st.subheader("💾 Экспорт/Импорт данных")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📤 Экспорт истории", use_container_width=True):
            # Экспорт истории в JSON
            history_data = []
            for h in st.session_state.quest_history:
                history_data.append({
                    'timestamp': h['timestamp'].isoformat(),
                    'quest': h['quest'].model_dump(),
                    'type': h['type']
                })
            
            json_str = json.dumps(history_data, ensure_ascii=False, indent=2)
            st.download_button(
                "💾 Скачать историю",
                data=json_str,
                file_name="quest_history.json",
                mime="application/json"
            )
    
    with col2:
        uploaded_history = st.file_uploader("📥 Импорт истории", type=['json'])
        if uploaded_history:
            # Импорт истории
            st.info("Функция импорта в разработке")


def show_help_page():
    """Страница справки"""
    st.header("📚 Справка")
    
    # Разделы справки
    help_sections = {
        "🚀 Быстрый старт": """
        1. Перейдите в раздел **Генератор**
        2. Выберите **жанр** вашего квеста
        3. Опишите **главного героя**
        4. Укажите **цель** квеста
        5. Нажмите **Сгенерировать квест**
        6. Дождитесь завершения генерации (30-60 секунд)
        """,
        
        "📝 Форматы входных данных": """
        **Текстовый файл** должен содержать:
        ```
        Жанр: [название жанра]
        Герой: [описание героя]
        Цель: [описание цели]
        ```
        
        **Поддерживаемые жанры:**
        - Киберпанк
        - Фэнтези
        - Детектив
        - Хоррор
        - Научная фантастика
        - Постапокалипсис
        - Стимпанк
        """,
        
        "🔧 Расширенная генерация": """
        **Story2Game логика** добавляет:
        - Предусловия для действий
        - Эффекты действий
        - Отслеживание состояния мира
        - Динамические реакции
        
        **Визуализация** создает:
        - Изображения сцен
        - Карты расположения объектов
        - Визуальную согласованность
        """,
        
        "💾 Форматы экспорта": """
        - **JSON** - структура квеста
        - **Python/JS** - исполняемый код
        - **Изображения** - визуализации сцен
        """,
        
        "❓ Часто задаваемые вопросы": """
        **Q: Сколько времени занимает генерация?**
        A: Базовая генерация - 30-60 секунд, расширенная - 2-5 минут
        
        **Q: Какие языки поддерживаются?**
        A: Русский и английский
        
        **Q: Можно ли редактировать сгенерированный квест?**
        A: Пока только через экспорт в JSON и ручное редактирование
        
        **Q: Нужен ли API ключ?**
        A: Да, требуется OpenAI или Anthropic API ключ
        """
    }
    
    for section, content in help_sections.items():
        with st.expander(section, expanded=(section == "🚀 Быстрый старт")):
            st.markdown(content)
    
    # Контакты и ссылки
    st.subheader("🔗 Полезные ссылки")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("📖 [Документация](https://github.com/yourusername/game-story-ai)")
    with col2:
        st.markdown("🐛 [Сообщить об ошибке](https://github.com/yourusername/game-story-ai/issues)")
    with col3:
        st.markdown("💬 [Сообщество](https://discord.gg/yourdiscord)")


def save_quest(quest):
    """Сохранение квеста"""
    try:
        # Создаем директорию для сохранения
        save_dir = Path("saved_quests")
        save_dir.mkdir(exist_ok=True)
        
        # Проверяем, что директория действительно создана
        if not save_dir.exists():
            st.error("❌ Не удалось создать директорию для сохранения")
            return
        
        # Генерируем имя файла (убираем недопустимые символы и обрабатываем Unicode)
        safe_title = ""
        if hasattr(quest, 'title') and quest.title:
            # Более агрессивная очистка символов для Windows
            import re
            safe_title = re.sub(r'[<>:"/\\|?*]', '', quest.title)  # Удаляем запрещенные символы Windows
            safe_title = "".join(c for c in safe_title if c.isprintable()).strip()  # Только печатные символы
            safe_title = safe_title.replace(' ', '_')[:50]  # Ограничиваем длину
        
        if not safe_title:
            safe_title = "quest"
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{safe_title}_{timestamp}.json"
        filepath = save_dir / filename
        
        # Отладочная информация
        st.info(f"📁 Сохраняем в: {filepath}")
        st.info(f"🏷️ Оригинальное название: {getattr(quest, 'title', 'Без названия')}")
        st.info(f"🔧 Безопасное имя файла: {filename}")
        
        # Создаем данные для сохранения
        quest_data = quest.model_dump() if hasattr(quest, 'model_dump') else quest.__dict__
        
        # Сохраняем с дополнительными проверками
        with open(filepath, 'w', encoding='utf-8', errors='ignore') as f:
            json.dump(quest_data, f, ensure_ascii=False, indent=2, default=str)
        
        # Проверяем, что файл действительно создан
        if filepath.exists():
            file_size = filepath.stat().st_size
            st.success(f"✅ Квест сохранен: {filename}")
            st.success(f"📦 Размер файла: {file_size} байт")
            
            # Показываем полный путь
            st.info(f"📍 Полный путь: {filepath.absolute()}")
            
            # Дополнительная проверка - пытаемся прочитать файл
            try:
                with open(filepath, 'r', encoding='utf-8') as test_f:
                    test_data = json.load(test_f)
                st.success("✅ Файл успешно сохранен и может быть прочитан")
            except Exception as read_error:
                st.warning(f"⚠️ Файл сохранен, но возможны проблемы с чтением: {read_error}")
        else:
            st.error("❌ Файл не был создан")
        
    except PermissionError as e:
        st.error(f"❌ Ошибка доступа: нет прав на запись в директорию")
        st.error(f"Детали: {e}")
        st.info("💡 Попробуйте запустить приложение от имени администратора")
    except UnicodeEncodeError as e:
        st.error(f"❌ Ошибка кодировки: {e}")
        st.info("💡 Проблема с символами в названии квеста")
    except Exception as e:
        st.error(f"❌ Ошибка сохранения: {type(e).__name__}: {e}")
        import traceback
        st.code(traceback.format_exc(), language="python")
        st.info("💡 Подробная информация об ошибке выше")


def export_quest(quest):
    """Экспорт квеста в различные форматы"""
    with st.expander("📤 Параметры экспорта", expanded=True):
        format_type = st.selectbox(
            "Формат экспорта",
            ["JSON", "Python Code", "JavaScript Code"]
        )
        
        include_metadata = st.checkbox("Включить метаданные", value=True)
        include_visuals = st.checkbox("Включить визуализации", value=False)
        
        if st.button("Экспортировать", use_container_width=True):
            st.info(f"Экспорт в формате {format_type} в разработке")


if __name__ == "__main__":
    main()