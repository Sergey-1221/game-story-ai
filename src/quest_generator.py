import asyncio
import time
from typing import Dict, Union, Optional
from pathlib import Path
from loguru import logger
import os
from dotenv import load_dotenv

from src.core.models import (
    ScenarioInput, GenerationConfig, Quest, 
    GenerationRequest, GenerationResponse
)
from src.modules.parser import InputParser
from src.modules.knowledge_base import KnowledgeBase
from src.modules.story_planner import StoryPlanner
from src.modules.scene_generator import SceneGenerator
from src.modules.branch_manager import BranchManager
from src.modules.output_formatter import OutputFormatter


class QuestGenerator:
    """Главный класс для генерации квестов"""
    
    def __init__(self, config: Optional[GenerationConfig] = None):
        # Загружаем переменные окружения
        load_dotenv()
        
        # Конфигурация
        self.config = config or GenerationConfig()
        
        # Инициализация модулей
        logger.info("Инициализация системы генерации квестов")
        
        self.parser = InputParser()
        self.knowledge_base = KnowledgeBase(
            persist_directory=os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chroma")
        )
        self.story_planner = StoryPlanner(self.knowledge_base)
        self.scene_generator = SceneGenerator(self.knowledge_base, self.config)
        self.branch_manager = BranchManager()
        self.output_formatter = OutputFormatter()
        
        logger.info("Система инициализирована")
    
    def generate(self, scenario: Union[str, Dict[str, str], ScenarioInput]) -> Quest:
        """Синхронный метод генерации квеста"""
        return asyncio.run(self.generate_async(scenario))
    
    async def generate_async(
        self, 
        scenario: Union[str, Dict[str, str], ScenarioInput]
    ) -> Quest:
        """Асинхронная генерация квеста"""
        start_time = time.time()
        
        try:
            # 1. Парсинг входных данных
            logger.info("Этап 1: Парсинг входных данных")
            scenario_input = self._parse_scenario(scenario)
            
            # 2. Построение RAG контекста
            logger.info("Этап 2: Подготовка базы знаний")
            scenario_dict = scenario_input.dict()
            rag_context = self.knowledge_base.build_rag_context(scenario_dict)
            
            # 3. Планирование структуры квеста
            logger.info("Этап 3: Планирование структуры квеста")
            story_graph = self.story_planner.plan_quest(scenario_input)
            
            logger.info(f"Запланировано сцен: {len(story_graph.scenes)}")
            
            # 4. Генерация детализированных сцен
            logger.info("Этап 4: Генерация сцен с помощью LLM")
            scenes = await self.scene_generator.generate_all_scenes(
                story_graph, scenario_input
            )
            
            # 5. Консолидация и проверка
            logger.info("Этап 5: Консолидация и проверка целостности")
            quest = self.branch_manager.consolidate_quest(
                scenes, 
                story_graph, 
                scenario_dict,
                quest_title=self._generate_title(scenario_input)
            )
            
            # 6. Финальная проверка
            narrative_issues = self.branch_manager.check_narrative_consistency(quest)
            if narrative_issues:
                logger.warning(f"Проблемы с повествованием: {narrative_issues}")
            
            generation_time = time.time() - start_time
            logger.info(f"Квест сгенерирован за {generation_time:.2f} секунд")
            
            # Добавляем статистику генерации
            quest.metadata['generation_time'] = generation_time
            quest.metadata['tokens_used'] = self.scene_generator.total_tokens
            
            return quest
            
        except Exception as e:
            logger.error(f"Ошибка генерации квеста: {e}")
            raise
    
    def _parse_scenario(
        self, 
        scenario: Union[str, Dict[str, str], ScenarioInput]
    ) -> ScenarioInput:
        """Парсинг различных форматов входных данных"""
        if isinstance(scenario, ScenarioInput):
            return scenario
        elif isinstance(scenario, dict):
            return self.parser.parse_dict(scenario)
        elif isinstance(scenario, str):
            # Проверяем, является ли это путём к файлу
            if os.path.exists(scenario):
                return self.parser.parse_file(scenario)
            else:
                # Считаем, что это текст сценария
                return self.parser.parse_text(scenario)
        else:
            raise ValueError(f"Неподдерживаемый тип входных данных: {type(scenario)}")
    
    def _generate_title(self, scenario: ScenarioInput) -> str:
        """Генерация названия квеста"""
        # Простая генерация на основе цели
        goal_words = scenario.goal.split()[:5]
        title = " ".join(goal_words).capitalize()
        
        # Добавляем жанровый префикс
        genre_prefixes = {
            "киберпанк": "Хроники теней:",
            "фэнтези": "Легенда о",
            "детектив": "Дело о",
            "хоррор": "Кошмар:",
            "постапокалипсис": "После конца:",
            "стимпанк": "Механическая загадка:"
        }
        
        prefix = genre_prefixes.get(scenario.genre.lower(), "Квест:")
        
        return f"{prefix} {title}"
    
    def save_quest(self, quest: Quest, file_path: str,
                  include_metadata: bool = False,
                  include_paths: bool = False) -> Path:
        """Сохранение квеста в файл"""
        return self.output_formatter.save_to_file(
            quest, file_path, include_metadata, include_paths
        )
    
    def save_minimal(self, quest: Quest, file_path: str) -> Path:
        """Сохранение в минимальном формате"""
        return self.output_formatter.save_minimal_format(quest, file_path)
    
    def export_visualization(self, quest: Quest) -> Dict:
        """Экспорт для визуализации"""
        return self.output_formatter.export_for_visualization(quest)
    
    def process_request(self, request: GenerationRequest) -> GenerationResponse:
        """Обработка запроса на генерацию (для API)"""
        try:
            start_time = time.time()
            
            # Обновляем конфигурацию если передана
            if request.config:
                self.config = request.config
                self.scene_generator = SceneGenerator(
                    self.knowledge_base, self.config
                )
            
            # Генерируем квест
            quest = self.generate(request.scenario)
            
            generation_time = time.time() - start_time
            
            return GenerationResponse(
                quest=quest,
                generation_time=generation_time,
                tokens_used=self.scene_generator.total_tokens,
                status="success"
            )
            
        except Exception as e:
            logger.error(f"Ошибка обработки запроса: {e}")
            return GenerationResponse(
                quest=None,
                generation_time=0,
                tokens_used=0,
                status="error",
                error=str(e)
            )


def main():
    """Пример использования генератора"""
    # Инициализация
    generator = QuestGenerator()
    
    # Пример сценария
    scenario = {
        "genre": "киберпанк",
        "hero": "хакер-одиночка",
        "goal": "взломать замок на двери, найти и забрать чип с вирусом"
    }
    
    # Генерация
    print("Начинаем генерацию квеста...")
    quest = generator.generate(scenario)
    
    # Сохранение
    output_path = generator.save_quest(quest, "output/quest.json", include_metadata=True)
    print(f"Квест сохранён в: {output_path}")
    
    # Статистика
    print(f"\nСтатистика:")
    print(f"- Сцен: {len(quest.scenes)}")
    print(f"- Путей: {len(quest.paths)}")
    print(f"- Время генерации: {quest.metadata.get('generation_time', 0):.2f} сек")
    print(f"- Использовано токенов: {quest.metadata.get('tokens_used', 0)}")


if __name__ == "__main__":
    main()