from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
import tempfile
import shutil
from pathlib import Path
import uuid
from loguru import logger

from src.core.models import GenerationRequest, GenerationResponse, ScenarioInput
from src.quest_generator import QuestGenerator


app = FastAPI(
    title="AI Quest Generator API",
    description="API для генерации интерактивных квестов с помощью AI",
    version="1.0.0"
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация генератора
generator = QuestGenerator()

# Директория для временных файлов
TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)

# Директория для сохранения результатов
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "AI Quest Generator API",
        "version": "1.0.0",
        "endpoints": {
            "POST /generate": "Генерация квеста из JSON",
            "POST /generate/file": "Генерация квеста из текстового файла",
            "GET /quest/{quest_id}": "Получение сгенерированного квеста",
            "GET /health": "Проверка состояния сервиса"
        }
    }


@app.get("/health")
async def health_check():
    """Проверка состояния сервиса"""
    return {"status": "healthy", "service": "AI Quest Generator"}


@app.post("/generate", response_model=GenerationResponse)
async def generate_quest(request: GenerationRequest):
    """Генерация квеста из структурированного запроса"""
    try:
        logger.info(f"Получен запрос на генерацию: {request.scenario.genre}")
        
        response = generator.process_request(request)
        
        if response.status == "error":
            raise HTTPException(status_code=500, detail=response.error)
        
        # Сохраняем результат
        quest_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"{quest_id}.json"
        generator.save_quest(response.quest, str(output_path), include_metadata=True)
        
        # Добавляем ID в ответ
        response_dict = response.dict()
        response_dict["quest_id"] = quest_id
        response_dict["download_url"] = f"/quest/{quest_id}"
        
        return response_dict
        
    except Exception as e:
        logger.error(f"Ошибка генерации: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/file")
async def generate_quest_from_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Генерация квеста из текстового файла"""
    if not file.filename.endswith('.txt'):
        raise HTTPException(
            status_code=400,
            detail="Поддерживаются только .txt файлы"
        )
    
    # Сохраняем временный файл
    temp_path = TEMP_DIR / f"{uuid.uuid4()}_{file.filename}"
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Генерируем квест
        logger.info(f"Обработка файла: {file.filename}")
        quest = generator.generate(str(temp_path))
        
        # Сохраняем результат
        quest_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"{quest_id}.json"
        generator.save_quest(quest, str(output_path), include_metadata=True)
        
        # Планируем удаление временного файла
        background_tasks.add_task(os.unlink, temp_path)
        
        return {
            "status": "success",
            "quest_id": quest_id,
            "download_url": f"/quest/{quest_id}",
            "quest_title": quest.title,
            "scenes_count": len(quest.scenes),
            "paths_count": len(quest.paths)
        }
        
    except Exception as e:
        logger.error(f"Ошибка обработки файла: {e}")
        if temp_path.exists():
            os.unlink(temp_path)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/quest/{quest_id}")
async def get_quest(quest_id: str, format: Optional[str] = "json"):
    """Получение сгенерированного квеста"""
    file_path = OUTPUT_DIR / f"{quest_id}.json"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Квест не найден")
    
    if format == "download":
        return FileResponse(
            path=file_path,
            filename=f"quest_{quest_id}.json",
            media_type="application/json"
        )
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            import json
            return json.load(f)


@app.post("/generate/quick")
async def quick_generate(
    genre: str,
    hero: str,
    goal: str,
    language: str = "ru"
):
    """Быстрая генерация квеста из отдельных параметров"""
    try:
        scenario = ScenarioInput(
            genre=genre,
            hero=hero,
            goal=goal,
            language=language
        )
        
        request = GenerationRequest(scenario=scenario)
        response = generator.process_request(request)
        
        if response.status == "error":
            raise HTTPException(status_code=500, detail=response.error)
        
        # Возвращаем квест напрямую
        return {
            "status": "success",
            "quest": response.quest.dict()
        }
        
    except Exception as e:
        logger.error(f"Ошибка быстрой генерации: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/examples")
async def get_examples():
    """Получение примеров сценариев"""
    examples = []
    example_dir = Path("examples")
    
    if example_dir.exists():
        for file_path in example_dir.glob("scenario_*.txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                examples.append({
                    "filename": file_path.name,
                    "content": content
                })
    
    return {"examples": examples}


@app.delete("/quest/{quest_id}")
async def delete_quest(quest_id: str):
    """Удаление сгенерированного квеста"""
    file_path = OUTPUT_DIR / f"{quest_id}.json"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Квест не найден")
    
    try:
        os.unlink(file_path)
        return {"status": "success", "message": "Квест удален"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )