# Быстрый запуск AI Game Story Generator

## Простые способы запуска

### Вариант 1: Отдельные компоненты (Рекомендуется)

1. **Запуск API сервера:**
   - Дважды кликните `start_api.bat`
   - Или в терминале: `venv\Scripts\python.exe -m uvicorn src.api.main:app --port 8000`
   - Сервер будет доступен на http://localhost:8000

2. **Запуск Streamlit UI:**
   - Дважды кликните `start_ui.bat` 
   - Или в терминале: `venv\Scripts\python.exe -m streamlit run streamlit_app.py`
   - UI будет доступен на http://localhost:8501

### Вариант 2: Автоматический запуск

```bash
python run_all_safe.py
```

### Вариант 3: Только тестирование

```bash
python test_generation.py
```

## Полезные ссылки

- **Streamlit UI**: http://localhost:8501 - Основной интерфейс
- **API Сервер**: http://localhost:8000 - REST API  
- **API Документация**: http://localhost:8000/docs - Swagger UI

## Решение проблем

### Если приложение зависает:
1. Остановите все процессы: `Ctrl+C`
2. Убейте Python процессы: `taskkill /F /IM python.exe`
3. Запустите заново

### Если порты заняты:
- Порт 8000: API сервер уже запущен
- Порт 8501: Streamlit уже запущен
- Убейте процессы и запустите заново

### Медленная инициализация:
- Первый запуск занимает ~5-10 секунд (загрузка моделей)
- Последующие запуски быстрее

## Структура проекта

- `streamlit_app.py` - Главный UI
- `src/api/main.py` - API сервер
- `src/quest_generator.py` - Основной генератор
- `test_generation.py` - Тестирование

## Требования

- Python 3.11+
- Virtual environment в папке `venv/`
- Настроенный `.env` файл с API ключами