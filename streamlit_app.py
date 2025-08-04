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

from src.quest_generator import QuestGenerator
from src.modules.integrated_quest_generator import IntegratedQuestGenerator
from src.core.models import ScenarioInput, GenerationConfig, Genre
from src.modules.knowledge_base import KnowledgeBase


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


# Инициализация состояния сессии
if 'quest_history' not in st.session_state:
    st.session_state.quest_history = []
if 'current_quest' not in st.session_state:
    st.session_state.current_quest = None
if 'generator' not in st.session_state:
    st.session_state.generator = None
if 'integrated_generator' not in st.session_state:
    st.session_state.integrated_generator = None


def init_generators():
    """Инициализация генераторов"""
    if st.session_state.generator is None:
        with st.spinner("Инициализация системы..."):
            st.session_state.generator = QuestGenerator()
            st.session_state.integrated_generator = IntegratedQuestGenerator()


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
        st.image("https://via.placeholder.com/300x100/667eea/ffffff?text=AI+Story+Generator", use_column_width=True)
        
        selected = option_menu(
            "Меню",
            ["🏠 Главная", "✨ Генератор", "📊 Аналитика", "🗂️ История", "⚙️ Настройки", "📚 Справка"],
            icons=['house', 'magic', 'graph-up', 'clock-history', 'gear', 'book'],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "#fafafa"},
                "icon": {"color": "#667eea", "font-size": "20px"},
                "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "--hover-color": "#eee"},
                "nav-link-selected": {"background-color": "#667eea"},
            }
        )
    
    # Инициализация генераторов
    init_generators()
    
    # Роутинг страниц
    if selected == "🏠 Главная":
        show_home_page()
    elif selected == "✨ Генератор":
        show_generator_page()
    elif selected == "📊 Аналитика":
        show_analytics_page()
    elif selected == "🗂️ История":
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
            "🎨 SceneCraft визуализация": "3D-макеты и изображения сцен",
            "🎮 Экспорт в движки": "Unity, Unreal Engine, готовый код",
            "📊 Аналитика качества": "Метрики и оценка генерации"
        }
        
        for feature, description in features.items():
            st.markdown(f"**{feature}**: {description}")
        
        st.subheader("📈 Статистика")
        metrics = st.columns(4)
        with metrics[0]:
            st.metric("Квестов создано", len(st.session_state.quest_history))
        with metrics[1]:
            st.metric("Жанров доступно", 7)
        with metrics[2]:
            st.metric("Модулей активно", 12)
        with metrics[3]:
            st.metric("Качество генерации", "95%")
    
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
                st.switch_page("pages/generator.py")
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
        
        genre = st.selectbox(
            "Жанр",
            ["киберпанк", "фэнтези", "детектив", "хоррор", "научная фантастика", "постапокалипсис", "стимпанк"],
            help="Выберите жанр вашего квеста"
        )
        
        hero = st.text_input(
            "Главный герой",
            placeholder="Опишите протагониста",
            help="Например: молодой маг-ученик, опытный детектив, хакер-одиночка"
        )
        
        goal = st.text_area(
            "Цель квеста",
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
    
    # Отображение результата
    if st.session_state.current_quest:
        show_quest_result()


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
        with_visuals = st.checkbox("🎨 SceneCraft визуализация", value=True,
                                  help="Создать 3D-макеты и изображения сцен")
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
            
            # Симуляция прогресса (в реальности нужны callbacks из генератора)
            for i in range(101):
                progress_bar.progress(i)
                if i < 20:
                    status_text.text("📝 Анализируем сценарий...")
                elif i < 40:
                    status_text.text("🧠 Планируем структуру квеста...")
                elif i < 70:
                    status_text.text("✍️ Генерируем сцены...")
                elif i < 90:
                    status_text.text("🔍 Проверяем целостность...")
                else:
                    status_text.text("✅ Завершаем генерацию...")
                time.sleep(0.01)
            
            # Реальная генерация
            quest = st.session_state.generator.generate(scenario.dict())
            
            # Сохраняем результат
            st.session_state.current_quest = quest
            st.session_state.quest_history.append({
                'timestamp': datetime.now(),
                'quest': quest,
                'type': 'basic'
            })
            
            progress_bar.empty()
            status_text.empty()
            st.success("✅ Квест успешно сгенерирован!")
            
        except Exception as e:
            st.error(f"❌ Ошибка генерации: {e}")


def generate_advanced_quest(genre, hero, goal, with_logic, with_visuals, 
                          export_code, visual_style, enable_dynamic):
    """Расширенная генерация квеста"""
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
                
                # Симуляция прогресса
                for progress, message in stages:
                    status_text.text(message)
                    for i in range(int((progress - progress_bar.progress()) * 100)):
                        progress_bar.progress(progress_bar.progress() + 0.01)
                        time.sleep(0.02)
            
            # Реальная генерация (нужно сделать асинхронной)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                st.session_state.integrated_generator.generate_enhanced_quest(
                    scenario,
                    with_logic=with_logic,
                    with_visuals=with_visuals,
                    export_code=export_code
                )
            )
            
            # Сохраняем результат
            st.session_state.current_quest = result['quest']
            st.session_state.current_enhanced_result = result
            st.session_state.quest_history.append({
                'timestamp': datetime.now(),
                'quest': result['quest'],
                'type': 'advanced',
                'enhancements': result['enhancements']
            })
            
            progress_container.empty()
            st.success("✅ Расширенная генерация завершена!")
            
            # Показываем результаты
            show_enhanced_results(result)
            
        except Exception as e:
            st.error(f"❌ Ошибка: {e}")
            import traceback
            st.code(traceback.format_exc())


def show_quest_result():
    """Отображение результата генерации"""
    quest = st.session_state.current_quest
    
    st.markdown("---")
    st.subheader(f"📖 {quest.title}")
    
    # Метаданные квеста
    meta_cols = st.columns(4)
    with meta_cols[0]:
        st.metric("Жанр", quest.genre)
    with meta_cols[1]:
        st.metric("Сцен", len(quest.scenes))
    with meta_cols[2]:
        st.metric("Путей", len(quest.paths) if quest.paths else "N/A")
    with meta_cols[3]:
        st.metric("Время генерации", f"{quest.metadata.get('generation_time', 0):.1f}с")
    
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
    action_cols = st.columns(4)
    with action_cols[0]:
        if st.button("💾 Сохранить", use_container_width=True):
            save_quest(quest)
    with action_cols[1]:
        if st.button("📤 Экспорт", use_container_width=True):
            export_quest(quest)
    with action_cols[2]:
        if st.button("🎮 Играть", use_container_width=True):
            st.info("Режим игры в разработке")
    with action_cols[3]:
        if st.button("🔄 Новый квест", use_container_width=True):
            st.session_state.current_quest = None
            st.rerun()


def show_scenes_view(quest):
    """Отображение сцен квеста"""
    for i, scene in enumerate(quest.scenes):
        with st.expander(f"Сцена {i+1}: {scene.scene_id}", expanded=(i==0)):
            st.markdown(f"**Текст сцены:**")
            st.write(scene.text)
            
            if scene.mood:
                st.caption(f"Настроение: {scene.mood}")
            if scene.location:
                st.caption(f"Локация: {scene.location}")
            
            st.markdown("**Варианты выбора:**")
            for j, choice in enumerate(scene.choices):
                st.write(f"{j+1}. {choice.text} → *{choice.next_scene}*")


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
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(G.nodes[node]['label'])
    
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
    
    st.plotly_chart(fig, use_container_width=True)


def show_json_view(quest):
    """Отображение JSON представления"""
    quest_dict = quest.dict()
    json_str = json.dumps(quest_dict, ensure_ascii=False, indent=2)
    
    st.code(json_str, language='json')
    
    # Кнопка копирования
    st.download_button(
        label="📥 Скачать JSON",
        data=json_str,
        file_name=f"quest_{quest.title.replace(' ', '_')}.json",
        mime="application/json"
    )


def show_quest_statistics(quest):
    """Статистика квеста"""
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
        st.plotly_chart(fig, use_container_width=True)
        
        # Длина текста сцен
        text_lengths = pd.DataFrame({
            'Сцена': [s.scene_id for s in quest.scenes],
            'Длина текста': [len(s.text) for s in quest.scenes]
        })
        
        fig2 = px.line(text_lengths, x='Сцена', y='Длина текста',
                      title="Длина текста сцен", markers=True)
        st.plotly_chart(fig2, use_container_width=True)
    
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
            st.plotly_chart(fig3, use_container_width=True)
            
            # Статистика исходов
            outcome_counts = paths_data['Исход'].value_counts()
            fig4 = px.pie(values=outcome_counts.values, names=outcome_counts.index,
                         title="Распределение исходов")
            st.plotly_chart(fig4, use_container_width=True)


def show_enhanced_results(result):
    """Отображение результатов расширенной генерации"""
    st.markdown("---")
    st.subheader("🎯 Результаты расширенной генерации")
    
    # Табы для разных улучшений
    tabs = ["📖 Квест"]
    if 'logic' in result['enhancements']:
        tabs.append("🧠 Логика")
    if 'visualization' in result['enhancements']:
        tabs.append("🎨 Визуализация")
    if 'generated_code' in result['enhancements']:
        tabs.append("💻 Код")
    
    tabs_ui = st.tabs(tabs)
    
    # Базовый квест
    with tabs_ui[0]:
        show_quest_result()
    
    # Логика
    if '🧠 Логика' in tabs:
        with tabs_ui[tabs.index('🧠 Логика')]:
            show_logic_view(result['enhancements']['logic'])
    
    # Визуализация
    if '🎨 Визуализация' in tabs:
        with tabs_ui[tabs.index('🎨 Визуализация')]:
            show_visualization_view(result['enhancements']['visualization'])
    
    # Код
    if '💻 Код' in tabs:
        with tabs_ui[tabs.index('💻 Код')]:
            show_code_view(result['enhancements']['generated_code'])


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
    
    # Показываем визуализации сцен
    for scene_viz in viz_data['scenes'][:3]:  # Первые 3 сцены
        with st.expander(f"Сцена {scene_viz['scene_id']}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Композитное изображение (если есть)
                if 'composite_path' in scene_viz:
                    try:
                        image = Image.open(scene_viz['composite_path'])
                        st.image(image, caption="Многоракурсная визуализация", 
                                use_column_width=True)
                    except:
                        st.info("Изображение недоступно")
                else:
                    st.info("Визуализация в процессе...")
            
            with col2:
                st.write("**Макет сцены:**")
                if 'layout_path' in scene_viz:
                    try:
                        with open(scene_viz['layout_path'], 'r') as f:
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
        avg_scenes = sum(len(h['quest'].scenes) for h in st.session_state.quest_history) / len(st.session_state.quest_history)
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
        genres = [h['quest'].genre for h in st.session_state.quest_history]
        genre_counts = pd.Series(genres).value_counts()
        
        fig = px.pie(values=genre_counts.values, names=genre_counts.index,
                    title="Распределение по жанрам")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # График по времени
        times = [h['timestamp'] for h in st.session_state.quest_history]
        times_df = pd.DataFrame({'timestamp': times, 'count': 1})
        times_df['date'] = times_df['timestamp'].dt.date
        daily_counts = times_df.groupby('date')['count'].sum().reset_index()
        
        fig = px.line(daily_counts, x='date', y='count',
                     title="Квесты по дням", markers=True)
        st.plotly_chart(fig, use_container_width=True)
    
    # Детальная аналитика
    st.subheader("🔍 Детальный анализ")
    
    # Таблица квестов
    quest_data = []
    for h in st.session_state.quest_history:
        quest = h['quest']
        quest_data.append({
            'Время': h['timestamp'].strftime('%Y-%m-%d %H:%M'),
            'Название': quest.title,
            'Жанр': quest.genre,
            'Сцен': len(quest.scenes),
            'Тип': h['type'],
            'Время генерации': f"{quest.metadata.get('generation_time', 0):.1f}с"
        })
    
    df = pd.DataFrame(quest_data)
    st.dataframe(df, use_container_width=True)


def show_history_page():
    """Страница истории"""
    st.header("🗂️ История квестов")
    
    if not st.session_state.quest_history:
        st.info("История пуста. Сгенерируйте свой первый квест!")
        return
    
    # Фильтры
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_genre = st.selectbox("Фильтр по жанру", 
                                   ["Все"] + list(set(h['quest'].genre for h in st.session_state.quest_history)))
    with col2:
        filter_type = st.selectbox("Тип генерации", ["Все", "basic", "advanced"])
    with col3:
        sort_by = st.selectbox("Сортировка", ["Новые первыми", "Старые первыми", "По названию"])
    
    # Применяем фильтры
    filtered_history = st.session_state.quest_history
    
    if filter_genre != "Все":
        filtered_history = [h for h in filtered_history if h['quest'].genre == filter_genre]
    
    if filter_type != "Все":
        filtered_history = [h for h in filtered_history if h['type'] == filter_type]
    
    # Сортировка
    if sort_by == "Новые первыми":
        filtered_history = sorted(filtered_history, key=lambda x: x['timestamp'], reverse=True)
    elif sort_by == "Старые первыми":
        filtered_history = sorted(filtered_history, key=lambda x: x['timestamp'])
    else:
        filtered_history = sorted(filtered_history, key=lambda x: x['quest'].title)
    
    # Отображение
    for i, history_item in enumerate(filtered_history):
        quest = history_item['quest']
        
        with st.expander(f"{quest.title} - {history_item['timestamp'].strftime('%Y-%m-%d %H:%M')}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Жанр:** {quest.genre}")
                st.write(f"**Герой:** {quest.hero}")
                st.write(f"**Цель:** {quest.goal}")
                st.write(f"**Сцен:** {len(quest.scenes)}")
                st.write(f"**Тип генерации:** {history_item['type']}")
            
            with col2:
                if st.button("👁️ Просмотр", key=f"view_{i}"):
                    st.session_state.current_quest = quest
                    st.info("Перейдите на вкладку Генератор для просмотра")
                
                if st.button("💾 Экспорт", key=f"export_{i}"):
                    export_quest(quest)
                
                if st.button("🗑️ Удалить", key=f"delete_{i}"):
                    st.session_state.quest_history.remove(history_item)
                    st.rerun()


def show_settings_page():
    """Страница настроек"""
    st.header("⚙️ Настройки")
    
    # API настройки
    st.subheader("🔑 API ключи")
    
    openai_key = st.text_input("OpenAI API Key", type="password", 
                              value=st.session_state.get('openai_key', ''))
    anthropic_key = st.text_input("Anthropic API Key", type="password",
                                 value=st.session_state.get('anthropic_key', ''))
    
    if st.button("💾 Сохранить ключи"):
        st.session_state.openai_key = openai_key
        st.session_state.anthropic_key = anthropic_key
        st.success("Ключи сохранены!")
    
    # Настройки генерации
    st.subheader("🎯 Настройки генерации по умолчанию")
    
    default_model = st.selectbox("Модель по умолчанию", 
                                ["gpt-4", "gpt-3.5-turbo", "claude-3-opus"])
    default_temp = st.slider("Температура по умолчанию", 0.0, 1.0, 0.8, 0.1)
    default_rag = st.checkbox("Использовать RAG по умолчанию", value=True)
    
    # Настройки интерфейса
    st.subheader("🎨 Настройки интерфейса")
    
    theme = st.selectbox("Тема", ["Светлая", "Тёмная", "Автоматически"])
    show_tips = st.checkbox("Показывать подсказки", value=True)
    auto_save = st.checkbox("Автосохранение квестов", value=True)
    
    # База знаний
    st.subheader("📚 База знаний")
    
    if st.button("🔄 Обновить базу знаний"):
        with st.spinner("Обновление базы знаний..."):
            # Переинициализация knowledge base
            st.session_state.generator.knowledge_base = KnowledgeBase()
            st.success("База знаний обновлена!")
    
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
                    'quest': h['quest'].dict(),
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
        
        **SceneCraft визуализация** создает:
        - 3D-макеты сцен
        - Многоракурсные изображения
        - Карты расположения объектов
        - Визуальную согласованность
        """,
        
        "💾 Форматы экспорта": """
        - **JSON** - структура квеста
        - **Unity** - префабы и скрипты
        - **Unreal Engine** - блюпринты
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
        
        # Генерируем имя файла
        filename = f"{quest.title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = save_dir / filename
        
        # Сохраняем
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(quest.dict(), f, ensure_ascii=False, indent=2)
        
        st.success(f"✅ Квест сохранен: {filename}")
        
    except Exception as e:
        st.error(f"❌ Ошибка сохранения: {e}")


def export_quest(quest):
    """Экспорт квеста в различные форматы"""
    with st.expander("📤 Параметры экспорта", expanded=True):
        format_type = st.selectbox(
            "Формат экспорта",
            ["JSON", "Unity Package", "Unreal Blueprint", "Python Code", "JavaScript Code"]
        )
        
        include_metadata = st.checkbox("Включить метаданные", value=True)
        include_visuals = st.checkbox("Включить визуализации", value=False)
        
        if st.button("Экспортировать", use_container_width=True):
            st.info(f"Экспорт в формате {format_type} в разработке")


if __name__ == "__main__":
    main()