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
        
        # Инициализация модулей (ленивая инициализация)
        logger.info("Инициализация системы генерации квестов")
        
        self.parser = None
        self.knowledge_base = None
        self.story_planner = None
        self.scene_generator = None
        self.branch_manager = None
        self.output_formatter = None
        
        # Флаг инициализации
        self._initialized = False
        
        logger.info("Система создана (модули будут загружены при первом использовании)")
    
    def _ensure_initialized(self):
        """Ленивая инициализация модулей"""
        if self._initialized:
            return
            
        try:
            logger.info("Загрузка модулей...")
            
            # Шаг 1: Простые модули
            logger.info("Загружаем базовые модули...")
            self.parser = InputParser()
            self.branch_manager = BranchManager()
            self.output_formatter = OutputFormatter()
            
            # Шаг 2: База знаний (может быть проблемной)
            logger.info("Загружаем базу знаний...")
            try:
                # Пробуем загрузить упрощенную версию
                from src.modules.simple_knowledge_base import SimpleKnowledgeBase
                self.knowledge_base = SimpleKnowledgeBase(
                    persist_directory=os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chroma")
                )
                logger.info("Загружена упрощенная база знаний")
            except Exception as e:
                logger.warning(f"Ошибка загрузки SimpleKnowledgeBase: {e}")
                try:
                    # Fallback на полную версию
                    self.knowledge_base = KnowledgeBase(
                        persist_directory=os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chroma")
                    )
                except Exception as e2:
                    logger.warning(f"Ошибка загрузки KnowledgeBase: {e2}")
                    # Создаем mock версию для тестирования
                    self.knowledge_base = self._create_mock_knowledge_base()
            
            # Шаг 3: Планировщик
            logger.info("Загружаем планировщик...")
            self.story_planner = StoryPlanner(self.knowledge_base)
            
            # Шаг 4: Генератор сцен (самый тяжелый)
            logger.info("Загружаем генератор сцен...")
            try:
                # Проверяем наличие API ключа
                if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
                    logger.warning("API ключи не найдены, используем mock генератор")
                    self.scene_generator = self._create_mock_scene_generator()
                else:
                    # Используем настоящий генератор сцен
                    logger.info("Используем полноценный генератор сцен")
                    from src.modules.scene_generator import SceneGenerator
                    self.scene_generator = SceneGenerator(self.knowledge_base, self.config)
            except Exception as e:
                logger.warning(f"Ошибка загрузки SceneGenerator: {e}")
                # Создаем mock версию
                self.scene_generator = self._create_mock_scene_generator()
            
            self._initialized = True
            logger.info("Все модули загружены успешно")
            
        except Exception as e:
            logger.error(f"Критическая ошибка инициализации модулей: {e}")
            # Создаем минимальную рабочую версию
            self._create_fallback_modules()
            self._initialized = True
            logger.info("Загружена fallback версия модулей")
    
    def _create_mock_knowledge_base(self):
        """Создает mock версию базы знаний"""
        class MockKnowledgeBase:
            def build_rag_context(self, scenario_dict):
                return "Mock RAG context for testing"
            
            def retrieve_genre_context(self, genre, query, top_k=5):
                return []
            
            def find_quest_template(self, goal):
                return {
                    "structure": [
                        {"stage": "Начало", "description": "Начало приключения", "branching_point": False},
                        {"stage": "Развитие", "description": "Развитие событий", "branching_point": True},
                        {"stage": "Финал", "description": "Завершение истории", "branching_point": False}
                    ]
                }
            
            def get_genre_elements(self, genre):
                return {
                    "locations": ["локация1", "локация2"],
                    "atmosphere_words": ["атмосфера1", "атмосфера2"],
                    "items": ["предмет1", "предмет2"]
                }
        
        return MockKnowledgeBase()
    
    def _create_mock_scene_generator(self):
        """Создает mock версию генератора сцен"""
        from src.core.models import Scene, Choice
        
        class MockSceneGenerator:
            def __init__(self):
                self.total_tokens = 0
            
            def generate_scenes(self, story_graph, scenario, rag_context):
                # Создаем простые тестовые сцены
                scenes = {}
                planned_scenes = list(story_graph.scenes.values())
                
                for i, planned_scene in enumerate(planned_scenes):
                    # Определяем следующую сцену
                    if i < len(planned_scenes) - 1:
                        next_scene_id = planned_scenes[i + 1].scene_id
                    else:
                        next_scene_id = "end"  # Финальная сцена ведет к концу
                    
                    # Создаем список выборов
                    choices = []
                    
                    # Основной выбор
                    if i < len(planned_scenes) - 1:
                        choices.append(
                            Choice(
                                text=f"Продолжить приключение",
                                next_scene=next_scene_id
                            )
                        )
                    else:
                        # Для последней сцены добавляем выбор завершения
                        choices.append(
                            Choice(
                                text=f"Завершить квест",
                                next_scene="end"
                            )
                        )
                    
                    # Создаем сцену с готовыми выборами
                    scene = Scene(
                        scene_id=planned_scene.scene_id,
                        text=f"[ТЕСТ] {planned_scene.stage_name}: {planned_scene.description}. Это демонстрационная сцена для тестирования системы.",
                        mood="тестовое",
                        location=f"Локация {i+1}",
                        choices=choices
                    )
                    
                    # Для ветвящихся сцен добавляем дополнительный выбор
                    if planned_scene.is_branching and i < len(planned_scenes) - 2:
                        scene.choices.append(
                            Choice(
                                text=f"Выбрать альтернативный путь",
                                next_scene=planned_scenes[i + 2].scene_id if i + 2 < len(planned_scenes) else "end"
                            )
                        )
                    
                    scenes[scene.scene_id] = scene
                
                return scenes
            
            async def generate_all_scenes(self, story_graph, scenario):
                # Асинхронная версия для совместимости
                return self.generate_scenes(story_graph, scenario, "")
        
        return MockSceneGenerator()
    
    def _create_fallback_modules(self):
        """Создает fallback версии всех модулей"""
        if self.parser is None:
            self.parser = InputParser()
        if self.branch_manager is None:
            self.branch_manager = BranchManager()
        if self.output_formatter is None:
            self.output_formatter = OutputFormatter()
        if self.knowledge_base is None:
            self.knowledge_base = self._create_mock_knowledge_base()
        if self.story_planner is None:
            self.story_planner = StoryPlanner(self.knowledge_base)
        if self.scene_generator is None:
            # Пытаемся создать настоящий генератор, если есть API ключи
            if os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"):
                try:
                    from src.modules.scene_generator import SceneGenerator
                    self.scene_generator = SceneGenerator(self.knowledge_base, self.config)
                except Exception as e:
                    logger.warning(f"Не удалось создать SceneGenerator: {e}")
                    self.scene_generator = self._create_mock_scene_generator()
            else:
                self.scene_generator = self._create_mock_scene_generator()
    
    def generate(self, scenario: Union[str, Dict[str, str], ScenarioInput]) -> Quest:
        """Синхронный метод генерации квеста"""
        self._ensure_initialized()
        return asyncio.run(self.generate_async(scenario))
    
    async def generate_async(
        self, 
        scenario: Union[str, Dict[str, str], ScenarioInput]
    ) -> Quest:
        """Асинхронная генерация квеста"""
        self._ensure_initialized()
        start_time = time.time()
        
        try:
            # 1. Парсинг входных данных
            logger.info("Этап 1: Парсинг входных данных")
            scenario_input = self._parse_scenario(scenario)
            
            # 2. Построение RAG контекста
            logger.info("Этап 2: Подготовка базы знаний")
            scenario_dict = scenario_input.model_dump()
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