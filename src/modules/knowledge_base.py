import json
import os
from typing import List, Dict, Optional, Any
from pathlib import Path
import numpy as np
from loguru import logger
# Опциональный импорт для избежания проблем с памятью
try:
    import chromadb
    from chromadb.config import Settings
    import tiktoken
    from sentence_transformers import SentenceTransformer
    FULL_FEATURES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Некоторые зависимости недоступны: {e}")
    FULL_FEATURES_AVAILABLE = False

from src.core.models import KnowledgeItem, Genre


class KnowledgeBase:
    """Модуль управления базой знаний и RAG (Retrieval-Augmented Generation)"""
    
    def __init__(self, persist_directory: str = "./data/chroma"):
        if not FULL_FEATURES_AVAILABLE:
            raise ImportError("KnowledgeBase requires chromadb and sentence-transformers. Use SimpleKnowledgeBase instead.")
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        try:
            self.encoder = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        except Exception as e:
            logger.warning(f"Failed to load SentenceTransformer: {e}. Using fallback encoder.")
            # Fallback: простой encoder для тестирования
            self.encoder = None
        
        try:
            # Проверяем, существует ли база данных
            db_path = self.persist_directory / "chroma.sqlite3"
            if db_path.exists():
                # Если база существует, пытаемся подключиться
                self.client = chromadb.PersistentClient(path=str(self.persist_directory))
            else:
                # Если базы нет, создаем новую
                self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        except Exception as e:
            logger.warning(f"Failed to create persistent client: {e}. Using in-memory client.")
            self.client = chromadb.Client()
        
        self.collections = {
            'genres': self.client.get_or_create_collection("genre_knowledge"),
            'templates': self.client.get_or_create_collection("story_templates"),
            'elements': self.client.get_or_create_collection("story_elements")
        }
        
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        self._load_default_knowledge()
    
    def _load_default_knowledge(self):
        """Загрузка базовых знаний из файлов"""
        knowledge_dir = Path("data/knowledge_base")
        
        genres_dir = knowledge_dir / "genres"
        if genres_dir.exists():
            for genre_file in genres_dir.glob("*.json"):
                try:
                    with open(genre_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._index_genre_knowledge(data)
                except Exception as e:
                    logger.error(f"Ошибка загрузки {genre_file}: {e}")
        
        templates_file = knowledge_dir / "templates/quest_templates.json"
        if templates_file.exists():
            try:
                with open(templates_file, 'r', encoding='utf-8') as f:
                    templates = json.load(f)
                    self._index_templates(templates)
            except Exception as e:
                logger.error(f"Ошибка загрузки шаблонов: {e}")
    
    def _index_genre_knowledge(self, genre_data: Dict[str, Any]):
        """Индексация знаний о жанре"""
        genre = genre_data.get('genre', '')
        
        if 'setting' in genre_data:
            self._add_to_collection(
                'genres',
                f"{genre}_setting",
                genre_data['setting'],
                {'genre': genre, 'type': 'setting'}
            )
        
        if 'atmosphere' in genre_data:
            for i, desc in enumerate(genre_data['atmosphere']):
                self._add_to_collection(
                    'genres',
                    f"{genre}_atmosphere_{i}",
                    desc,
                    {'genre': genre, 'type': 'atmosphere'}
                )
        
        if 'typical_elements' in genre_data:
            for element_type, elements in genre_data['typical_elements'].items():
                for i, element in enumerate(elements):
                    self._add_to_collection(
                        'genres',
                        f"{genre}_{element_type}_{i}",
                        element,
                        {'genre': genre, 'type': element_type}
                    )
    
    def _index_templates(self, templates: List[Dict[str, Any]]):
        """Индексация шаблонов квестов"""
        for i, template in enumerate(templates):
            self._add_to_collection(
                'templates',
                f"template_{i}",
                json.dumps(template, ensure_ascii=False),
                {
                    'goal_type': template.get('goal_type', ''),
                    'complexity': template.get('complexity', 'medium')
                }
            )
    
    def _add_to_collection(self, collection_name: str, doc_id: str, 
                          content: str, metadata: Dict[str, Any]):
        """Добавление документа в коллекцию"""
        try:
            if self.encoder is not None:
                embedding = self.encoder.encode([content])[0].tolist()
            else:
                # Fallback: простые случайные embeddings для тестирования
                embedding = np.random.normal(0, 1, 384).tolist()
            
            self.collections[collection_name].upsert(
                ids=[doc_id],
                documents=[content],
                embeddings=[embedding],
                metadatas=[metadata]
            )
        except Exception as e:
            logger.error(f"Ошибка добавления в коллекцию {collection_name}: {e}")
    
    def retrieve_genre_context(self, genre: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Извлечение контекста по жанру"""
        try:
            if self.encoder is not None:
                query_embedding = self.encoder.encode([query])[0].tolist()
            else:
                # Fallback: случайный query embedding
                query_embedding = np.random.normal(0, 1, 384).tolist()
            
            results = self.collections['genres'].query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where={"genre": genre.lower()}
            )
            
            contexts = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    contexts.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0
                    })
            
            return contexts
        except Exception as e:
            logger.error(f"Ошибка извлечения контекста жанра: {e}")
            return []
    
    def find_quest_template(self, goal: str) -> Optional[Dict[str, Any]]:
        """Поиск подходящего шаблона квеста"""
        try:
            if self.encoder is not None:
                query_embedding = self.encoder.encode([goal])[0].tolist()
            else:
                # Fallback: случайный query embedding
                query_embedding = np.random.normal(0, 1, 384).tolist()
            
            results = self.collections['templates'].query(
                query_embeddings=[query_embedding],
                n_results=3
            )
            
            if results['documents'] and results['documents'][0]:
                best_match = json.loads(results['documents'][0][0])
                return best_match
            
            return None
        except Exception as e:
            logger.error(f"Ошибка поиска шаблона: {e}")
            return None
    
    def get_story_elements(self, element_type: str, genre: str, 
                          count: int = 5) -> List[str]:
        """Получение элементов истории (локации, предметы, персонажи)"""
        try:
            results = self.collections['elements'].query(
                query_texts=[f"{element_type} {genre}"],
                n_results=count,
                where={"type": element_type}
            )
            
            if results['documents'] and results['documents'][0]:
                return results['documents'][0]
            
            return []
        except Exception as e:
            logger.error(f"Ошибка получения элементов: {e}")
            return []
    
    def add_custom_knowledge(self, content: str, metadata: Dict[str, Any]):
        """Добавление пользовательских знаний"""
        collection = metadata.get('collection', 'genres')
        doc_id = f"custom_{hash(content)}"
        
        self._add_to_collection(collection, doc_id, content, metadata)
    
    def build_rag_context(self, scenario_data: Dict[str, str], 
                         max_tokens: int = 1500) -> str:
        """Построение контекста для RAG"""
        contexts = []
        
        genre_contexts = self.retrieve_genre_context(
            scenario_data['genre'],
            f"{scenario_data['hero']} {scenario_data['goal']}",
            top_k=3
        )
        
        for ctx in genre_contexts:
            contexts.append(f"[{ctx['metadata'].get('type', 'info')}]: {ctx['content']}")
        
        template = self.find_quest_template(scenario_data['goal'])
        if template:
            contexts.append(f"[шаблон квеста]: {json.dumps(template, ensure_ascii=False)}")
        
        full_context = "\n\n".join(contexts)
        
        tokens = self.tokenizer.encode(full_context)
        if len(tokens) > max_tokens:
            decoded = self.tokenizer.decode(tokens[:max_tokens])
            return decoded
        
        return full_context


class GenreKnowledgeManager:
    """Менеджер знаний о жанрах"""
    
    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
        self.genre_specifics = self._load_genre_specifics()
    
    def _load_genre_specifics(self) -> Dict[str, Dict[str, Any]]:
        """Загрузка специфичных для жанра деталей"""
        return {
            'киберпанк': {
                'locations': ['неоновые улицы', 'корпоративные небоскребы', 'хакерские притоны', 
                             'черный рынок имплантов', 'виртуальное пространство'],
                'items': ['нейроимплант', 'кибердека', 'вирусный чип', 'голографический проектор',
                         'энергетическое оружие'],
                'characters': ['корпоративный агент', 'уличный самурай', 'нетраннер', 
                              'техномедик', 'информационный брокер'],
                'atmosphere_words': ['неон', 'хром', 'дождь', 'смог', 'голограммы', 'импланты']
            },
            'фэнтези': {
                'locations': ['древний лес', 'заброшенная башня мага', 'подземелье', 
                             'эльфийский город', 'драконье логово'],
                'items': ['магический артефакт', 'зачарованный меч', 'свиток заклинания',
                         'эликсир исцеления', 'амулет защиты'],
                'characters': ['маг-отшельник', 'эльфийский следопыт', 'гномий кузнец',
                              'темный культист', 'странствующий бард'],
                'atmosphere_words': ['магия', 'древний', 'мистический', 'зачарованный', 'легендарный']
            },
            'детектив': {
                'locations': ['кабинет детектива', 'место преступления', 'полицейский участок',
                             'темный переулок', 'элитный клуб'],
                'items': ['улика', 'револьвер', 'записная книжка', 'фотография', 'досье'],
                'characters': ['подозреваемый', 'свидетель', 'информатор', 'коррумпированный коп',
                              'таинственный клиент'],
                'atmosphere_words': ['туман', 'тайна', 'подозрение', 'ночь', 'дождь', 'сигарета']
            },
            'фантастика': {
                'setting': 'Далекие миры и космические приключения',
                'mood': ['adventurous', 'mysterious', 'wonder'],
                'locations': ['космический корабль', 'неизвестная планета', 'космическая станция',
                             'инопланетный город', 'астероидное поле'],
                'items': ['бластер', 'сканер', 'скафандр', 'энергетический кристалл', 'универсальный переводчик'],
                'characters': ['инопланетянин', 'космический пилот', 'ученый', 'торговец', 'разведчик'],
                'atmosphere_words': ['звезды', 'неизвестность', 'технологии', 'исследование', 'чудеса']
            }
        }
    
    def get_genre_elements(self, genre: str) -> Dict[str, Any]:
        """Получение элементов для конкретного жанра"""
        genre_lower = genre.lower()
        if genre_lower in self.genre_specifics:
            return self.genre_specifics[genre_lower]
        
        # Fallback для неизвестных жанров
        generic_elements = self.kb.get_story_elements('generic', genre)
        
        # Возвращаем в правильном формате Dictionary
        return {
            'setting': f'Приключение в жанре {genre}',
            'atmosphere': generic_elements[:3] if isinstance(generic_elements, list) else [],
            'locations': generic_elements[3:6] if isinstance(generic_elements, list) and len(generic_elements) > 3 else ['таинственное место'],
            'items': generic_elements[6:9] if isinstance(generic_elements, list) and len(generic_elements) > 6 else ['предмет'],
            'characters': ['герой', 'союзник', 'противник'],
            'atmosphere_words': ['приключение', 'тайна', 'действие']
        }