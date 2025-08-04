import re
from typing import Dict, Optional, Union
from pathlib import Path
from loguru import logger

from src.core.models import ScenarioInput


class InputParser:
    """Модуль обработки входных данных для извлечения параметров сценария"""
    
    def __init__(self):
        self.patterns = {
            'genre': [
                r'[Жж]анр\s*[:：]\s*(.+?)(?=\n|$)',
                r'[Gg]enre\s*[:：]\s*(.+?)(?=\n|$)',
            ],
            'hero': [
                r'[Гг]ерой\s*[:：]\s*(.+?)(?=\n|$)',
                r'[Гг]лавный\s+герой\s*[:：]\s*(.+?)(?=\n|$)',
                r'[Пп]ротагонист\s*[:：]\s*(.+?)(?=\n|$)',
                r'[Hh]ero\s*[:：]\s*(.+?)(?=\n|$)',
                r'[Pp]rotagonist\s*[:：]\s*(.+?)(?=\n|$)',
            ],
            'goal': [
                r'[Цц]ель\s*[:：]\s*(.+?)(?=\n|$)',
                r'[Зз]адача\s*[:：]\s*(.+?)(?=\n|$)',
                r'[Мм]иссия\s*[:：]\s*(.+?)(?=\n|$)',
                r'[Gg]oal\s*[:：]\s*(.+?)(?=\n|$)',
                r'[Oo]bjective\s*[:：]\s*(.+?)(?=\n|$)',
                r'[Mm]ission\s*[:：]\s*(.+?)(?=\n|$)',
            ]
        }
        
        self.genre_mapping = {
            'cyberpunk': 'киберпанк',
            'fantasy': 'фэнтези',
            'sci-fi': 'научная фантастика',
            'scifi': 'научная фантастика',
            'detective': 'детектив',
            'horror': 'хоррор',
            'post-apocalyptic': 'постапокалипсис',
            'postapoc': 'постапокалипсис',
            'steampunk': 'стимпанк',
        }
    
    def parse_file(self, file_path: Union[str, Path]) -> ScenarioInput:
        """Парсинг файла со сценарием"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        if file_path.suffix.lower() != '.txt':
            raise ValueError(f"Неподдерживаемый формат файла: {file_path.suffix}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='cp1251') as f:
                content = f.read()
        
        return self.parse_text(content)
    
    def parse_text(self, text: str) -> ScenarioInput:
        """Парсинг текста сценария"""
        logger.info("Начинаем парсинг входного текста")
        
        extracted = {}
        
        for field, patterns in self.patterns.items():
            value = None
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip()
                    break
            
            if not value:
                raise ValueError(f"Не удалось извлечь поле '{field}' из текста")
            
            extracted[field] = value
            logger.debug(f"Извлечено {field}: {value}")
        
        extracted['genre'] = self._normalize_genre(extracted['genre'])
        
        language = self._detect_language(text)
        
        return ScenarioInput(
            genre=extracted['genre'],
            hero=extracted['hero'],
            goal=extracted['goal'],
            language=language
        )
    
    def parse_dict(self, data: Dict[str, str]) -> ScenarioInput:
        """Парсинг словаря с данными сценария"""
        required_fields = ['genre', 'hero', 'goal']
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
        
        data['genre'] = self._normalize_genre(data['genre'])
        
        return ScenarioInput(**data)
    
    def _normalize_genre(self, genre: str) -> str:
        """Нормализация названия жанра"""
        genre_lower = genre.lower().strip()
        
        if genre_lower in self.genre_mapping:
            return self.genre_mapping[genre_lower]
        
        genre_lower = re.sub(r'[^\w\s-]', '', genre_lower)
        genre_lower = re.sub(r'\s+', ' ', genre_lower)
        
        return genre_lower
    
    def _detect_language(self, text: str) -> str:
        """Определение языка текста"""
        cyrillic_count = len(re.findall(r'[а-яА-ЯёЁ]', text))
        latin_count = len(re.findall(r'[a-zA-Z]', text))
        
        if cyrillic_count > latin_count * 2:
            return 'ru'
        elif latin_count > cyrillic_count * 2:
            return 'en'
        else:
            return 'ru'
    
    def extract_additional_context(self, text: str) -> Dict[str, Optional[str]]:
        """Извлечение дополнительного контекста из текста"""
        context = {}
        
        setting_patterns = [
            r'[Мм]есто\s+действия\s*[:：]\s*(.+?)(?=\n|$)',
            r'[Сс]еттинг\s*[:：]\s*(.+?)(?=\n|$)',
            r'[Ss]etting\s*[:：]\s*(.+?)(?=\n|$)',
        ]
        for pattern in setting_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                context['setting'] = match.group(1).strip()
                break
        
        time_patterns = [
            r'[Вв]ремя\s+действия\s*[:：]\s*(.+?)(?=\n|$)',
            r'[Ээ]поха\s*[:：]\s*(.+?)(?=\n|$)',
            r'[Tt]ime\s*[:：]\s*(.+?)(?=\n|$)',
        ]
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                context['time_period'] = match.group(1).strip()
                break
        
        antagonist_patterns = [
            r'[Аа]нтагонист\s*[:：]\s*(.+?)(?=\n|$)',
            r'[Вв]раг\s*[:：]\s*(.+?)(?=\n|$)',
            r'[Пп]ротивник\s*[:：]\s*(.+?)(?=\n|$)',
            r'[Aa]ntagonist\s*[:：]\s*(.+?)(?=\n|$)',
        ]
        for pattern in antagonist_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                context['antagonist'] = match.group(1).strip()
                break
        
        return context