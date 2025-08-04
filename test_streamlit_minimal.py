"""
Минимальная версия Streamlit для тестирования
"""

import streamlit as st

# Настройка страницы
st.set_page_config(
    page_title="AI Game Story Generator - Test",
    page_icon="🎮",
    layout="wide"
)

st.title("🎮 AI Game Story Generator - Test Mode")

# Тестируем инициализацию по частям
try:
    st.info("Загружаем core.models...")
    from src.core.models import ScenarioInput, GenerationConfig, Genre
    st.success("✅ core.models загружен")
    
    st.info("Загружаем parser...")
    from src.modules.parser import InputParser
    parser = InputParser()
    st.success("✅ parser инициализирован")
    
    st.info("Загружаем knowledge_base...")
    # Пропускаем knowledge_base для теста
    st.warning("⏭️ knowledge_base пропущен")
    
    st.info("Тестируем базовую функциональность...")
    
    # Простая форма
    st.subheader("Тестовая форма")
    genre = st.selectbox("Жанр", ["киберпанк", "фэнтези", "детектив"])
    hero = st.text_input("Герой", "тестовый герой")
    goal = st.text_area("Цель", "тестовая цель")
    
    if st.button("Тест"):
        scenario = ScenarioInput(
            genre=genre,
            hero=hero,
            goal=goal
        )
        st.json(scenario.dict())
        st.success("✅ Базовая функциональность работает!")
        
except Exception as e:
    st.error(f"❌ Ошибка: {e}")
    import traceback
    st.code(traceback.format_exc())