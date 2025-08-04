"""
Облегченная версия API без тяжелых зависимостей
Использует упрощенные модули для избежания проблем с памятью
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional, List, Any
import json
import asyncio
from pathlib import Path
from datetime import datetime
import uuid
from loguru import logger

# Используем упрощенные версии модулей
from src.core.models import ScenarioInput, GenerationConfig, Quest
from src.modules.mock_quest_generator import MockQuestGenerator
from src.modules.simple_knowledge_base import SimpleKnowledgeBase

app = FastAPI(
    title="AI Game Story Generator API (Lite)",
    description="Облегченная версия API для генерации игровых историй",
    version="1.0.0-lite"
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хранилище для результатов генерации
quest_storage = {}

# Инициализация генератора при старте
generator = None
knowledge_base = None

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    global generator, knowledge_base
    
    logger.info("Запуск облегченного API сервера")
    
    # Используем упрощенные версии
    knowledge_base = SimpleKnowledgeBase()
    generator = MockQuestGenerator()
    
    logger.info("Генератор инициализирован в облегченном режиме")


class GenerateRequest(BaseModel):
    """Запрос на генерацию квеста"""
    scenario: Dict[str, Any]
    config: Optional[Dict[str, Any]] = None


class GenerateQuickRequest(BaseModel):
    """Быстрая генерация с параметрами"""
    genre: str
    hero: str
    goal: str
    language: str = "ru"
    use_rag: bool = True


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "AI Game Story Generator API (Lite Version)",
        "version": "1.0.0-lite",
        "endpoints": {
            "/generate": "Генерация квеста из JSON",
            "/generate/quick": "Быстрая генерация с параметрами",
            "/generate/file": "Генерация из файла",
            "/quest/{quest_id}": "Получить сгенерированный квест",
            "/examples": "Примеры сценариев",
            "/health": "Проверка состояния"
        }
    }


@app.get("/health")
async def health_check():
    """Проверка состояния сервиса"""
    return {
        "status": "healthy",
        "mode": "lite",
        "generator_ready": generator is not None,
        "knowledge_base_ready": knowledge_base is not None
    }


@app.post("/generate")
async def generate_quest(request: GenerateRequest, background_tasks: BackgroundTasks):
    """Генерация квеста из JSON"""
    try:
        quest_id = str(uuid.uuid4())
        
        # Создаем объекты из словарей
        scenario = ScenarioInput(**request.scenario)
        config = GenerationConfig(**request.config) if request.config else GenerationConfig()
        
        # Используем упрощенную синхронную генерацию
        quest = generator.generate(scenario)
        
        # Сохраняем результат
        quest_storage[quest_id] = {
            "quest": quest.model_dump(),
            "timestamp": datetime.now().isoformat(),
            "status": "completed"
        }
        
        return {
            "quest_id": quest_id,
            "status": "completed",
            "message": "Квест успешно сгенерирован",
            "quest": quest.model_dump()
        }
        
    except Exception as e:
        logger.error(f"Ошибка генерации: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/quick")
async def generate_quick(request: GenerateQuickRequest):
    """Быстрая генерация квеста"""
    try:
        scenario = ScenarioInput(
            genre=request.genre,
            hero=request.hero,
            goal=request.goal,
            language=request.language
        )
        
        config = GenerationConfig(
            use_rag=request.use_rag,
            temperature=0.8
        )
        
        quest_id = str(uuid.uuid4())
        
        # Генерируем квест
        quest = generator.generate(scenario)
        
        # Сохраняем результат
        quest_storage[quest_id] = {
            "quest": quest.model_dump(),
            "timestamp": datetime.now().isoformat(),
            "status": "completed"
        }
        
        return {
            "quest_id": quest_id,
            "quest": quest.model_dump(),
            "message": "Квест успешно сгенерирован"
        }
        
    except Exception as e:
        logger.error(f"Ошибка быстрой генерации: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/file")
async def generate_from_file(file: UploadFile = File(...)):
    """Генерация квеста из текстового файла"""
    try:
        content = await file.read()
        text = content.decode('utf-8')
        
        # Парсим текст для извлечения параметров
        lines = text.strip().split('\n')
        params = {}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                params[key.strip().lower()] = value.strip()
        
        # Создаем сценарий
        scenario = ScenarioInput(
            genre=params.get('жанр', 'фэнтези'),
            hero=params.get('герой', 'безымянный герой'),
            goal=params.get('цель', 'спасти мир'),
            language=params.get('язык', 'ru')
        )
        
        quest_id = str(uuid.uuid4())
        
        # Генерируем квест
        quest = generator.generate(scenario)
        
        # Сохраняем результат
        quest_storage[quest_id] = {
            "quest": quest.model_dump(),
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "source": "file"
        }
        
        return {
            "quest_id": quest_id,
            "quest": quest.model_dump(),
            "message": f"Квест сгенерирован из файла {file.filename}"
        }
        
    except Exception as e:
        logger.error(f"Ошибка обработки файла: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/quest/{quest_id}")
async def get_quest(quest_id: str):
    """Получить сгенерированный квест"""
    if quest_id not in quest_storage:
        raise HTTPException(status_code=404, detail="Квест не найден")
    
    return quest_storage[quest_id]


@app.get("/examples")
async def get_examples():
    """Получить примеры сценариев"""
    return {
        "examples": [
            {
                "title": "Киберпанк хакер",
                "scenario": {
                    "genre": "киберпанк",
                    "hero": "хакер-одиночка по имени Зеро",
                    "goal": "взломать главный сервер мегакорпорации и раскрыть правду",
                    "language": "ru"
                }
            },
            {
                "title": "Фэнтези маг",
                "scenario": {
                    "genre": "фэнтези",
                    "hero": "молодой маг-ученик",
                    "goal": "найти древний артефакт и спасти королевство от тьмы",
                    "language": "ru"
                }
            },
            {
                "title": "Детектив нуар",
                "scenario": {
                    "genre": "детектив",
                    "hero": "частный детектив Сэм Спейд",
                    "goal": "раскрыть убийство в закрытом особняке",
                    "language": "ru"
                }
            }
        ]
    }


@app.delete("/quest/{quest_id}")
async def delete_quest(quest_id: str):
    """Удалить квест из хранилища"""
    if quest_id not in quest_storage:
        raise HTTPException(status_code=404, detail="Квест не найден")
    
    del quest_storage[quest_id]
    return {"message": "Квест удален"}


@app.get("/stats")
async def get_stats():
    """Получить статистику сервера"""
    return {
        "total_quests": len(quest_storage),
        "mode": "lite",
        "available_genres": [
            "киберпанк", "фэнтези", "детектив", "хоррор", 
            "научная фантастика", "постапокалипсис", "стимпанк"
        ],
        "memory_safe": True
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)