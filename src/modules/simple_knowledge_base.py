"""
Упрощенная версия базы знаний для стабильной работы
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from loguru import logger

from src.core.models import Genre


class SimpleKnowledgeBase:
    """Упрощенная база знаний без внешних зависимостей"""
    
    def __init__(self, persist_directory: str = "./data/chroma"):
        logger.info("Инициализация упрощенной базы знаний")
        self.persist_directory = Path(persist_directory)
        self.genre_data = self._load_genre_data()
        logger.info("База знаний инициализирована")
    
    def _load_genre_data(self) -> Dict[str, Dict[str, Any]]:
        """Загрузка базовых данных по жанрам"""
        return {
            "киберпанк": {
                "setting": "Мрачное будущее с высокими технологиями и низким уровнем жизни",
                "atmosphere": ["неоновые огни", "дождливые улицы", "корпоративный контроль"],
                "locations": ["хакерское логово", "корпоративная башня", "черный рынок"],
                "items": ["нейроимплант", "голографический проектор", "хакерская дека"]
            },
            "фэнтези": {
                "setting": "Магический мир с драконами, эльфами и древними тайнами",
                "atmosphere": ["волшебные леса", "древние руины", "мистические туманы"],
                "locations": ["таверна", "башня мага", "эльфийский лес"],
                "items": ["магический посох", "зелье исцеления", "древний артефакт"]
            },
            "детектив": {
                "setting": "Городские улицы, полные тайн и преступлений",
                "atmosphere": ["туманные улицы", "темные переулки", "напряженная атмосфера"],
                "locations": ["офис детектива", "место преступления", "полицейский участок"],
                "items": ["увеличительное стекло", "записная книжка", "револьвер"]
            }
        }
    
    def build_rag_context(self, scenario_dict: Dict[str, Any]) -> str:
        """Построение контекста для генерации"""
        genre = scenario_dict.get('genre', 'фэнтези').lower()
        genre_info = self.genre_data.get(genre, self.genre_data['фэнтези'])
        
        context = f"""
Жанровый контекст для {genre}:
- Сеттинг: {genre_info['setting']}
- Атмосфера: {', '.join(genre_info['atmosphere'])}
- Типичные локации: {', '.join(genre_info['locations'])}
- Предметы: {', '.join(genre_info['items'])}
"""
        return context
    
    def retrieve_genre_context(self, genre: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Извлечение контекста по жанру"""
        genre_info = self.genre_data.get(genre.lower(), {})
        
        contexts = []
        if genre_info:
            contexts.append({
                'content': genre_info.get('setting', ''),
                'metadata': {'type': 'setting'},
                'distance': 0.1
            })
            
            for atm in genre_info.get('atmosphere', [])[:top_k]:
                contexts.append({
                    'content': atm,
                    'metadata': {'type': 'atmosphere'},
                    'distance': 0.2
                })
        
        return contexts
    
    def find_quest_template(self, goal: str) -> Optional[Dict[str, Any]]:
        """Поиск шаблона квеста"""
        # Простой шаблон для любой цели
        return {
            "structure": [
                {"stage": "Начало", "description": "Герой получает задание", "branching_point": False},
                {"stage": "Развитие", "description": "Герой сталкивается с препятствиями", "branching_point": True},
                {"stage": "Кульминация", "description": "Решающее столкновение", "branching_point": False},
                {"stage": "Развязка", "description": "Завершение истории", "branching_point": False}
            ],
            "complexity": "medium"
        }
    
    def get_genre_elements(self, genre: str) -> Dict[str, List[str]]:
        """Получение элементов жанра"""
        genre_info = self.genre_data.get(genre.lower(), self.genre_data['фэнтези'])
        return {
            "locations": genre_info.get('locations', []),
            "atmosphere_words": genre_info.get('atmosphere', []),
            "items": genre_info.get('items', [])
        }