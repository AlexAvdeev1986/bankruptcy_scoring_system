import pandas as pd
import os
import re
import logging
from datetime import datetime
from typing import List, Dict
from .config import Config

logger = logging.getLogger(__name__)

class DataNormalizer:
    def __init__(self):
        self.phone_pattern = re.compile(r'[^\d]')
        self.inn_pattern = re.compile(r'^\d{10,12}$')
    
    async def load_csv_files(self, data_dir: str = Config.DATA_DIR) -> List[Dict]:
        """Загрузка всех CSV файлов из директории"""
        all_data = []
        
        if not os.path.exists(data_dir):
            logger.warning(f"Directory {data_dir} does not exist")
            return self._generate_test_data()
        
        for file in os.listdir(data_dir):
            if file.endswith('.csv'):
                file_path = os.path.join(data_dir, file)
                try:
                    df = pd.read_csv(file_path)
                    # Добавляем источник
                    df['source'] = file.replace('.csv', '')
                    all_data.extend(df.to_dict('records'))
                    logger.info(f"Loaded {len(df)} records from {file}")
                except Exception as e:
                    logger.error(f"Error loading {file}: {e}")
        return all_data
    
    def _generate_test_data(self) -> List[Dict]:
        """Генерация тестовых данных"""
        test_data = []
        
        names = [
            "Иванов Иван Иванович", "Петров Петр Петрович", "Сидоров Сидор Сидорович",
            "Козлов Алексей Владимирович", "Смирнов Дмитрий Александрович",
            "Попов Сергей Николаевич", "Васильев Андрей Михайлович",
            "Морозов Владимир Игоревич", "Новиков Роман Сергеевич",
            "Федоров Максим Дмитриевич"
        ]
        
        regions = {
            'moscow': 'Москва',
            'tatarstan': 'Казань',
            'saratov': 'Саратов',
            'kaluga': 'Калуга',
            'spb': 'Санкт-Петербург',
            'nsk': 'Новосибирск'
        }
        
        sources = ['fns', 'gosuslugi', 'food_delivery', 'leads']
        
        for i in range(1000):
            region_key = list(regions.keys())[i % len(regions)]
            test_data.append({
                'lead_id': f"lead_{i:06d}",
                'fio': names[i % len(names)],
                'phone': f"+7{9000000000 + i:010d}",
                'inn': f"{1000000000 + i:010d}",
                'dob': f"1980-01-{(i % 28) + 1:02d}",
                'address': f"{regions[region_key]}, ул. Тестовая, д. {i % 100}",
                'source': sources[i % len(sources)],
                'tags': f"tag_{i % 5}",
                'email': f"test{i}@example.com" if i % 3 == 0 else None,
                'region': region_key
            })
        
        logger.info(f"Generated {len(test_data)} test records")
        return test_data
    
    async def normalize_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Нормализация данных"""
        normalized_data = []
        seen_keys = set()
        
        for record in raw_data:
            try:
                # Нормализация ФИО
                fio = self._normalize_fio(record.get('fio', ''))
                
                # Нормализация телефона
                phone = self._normalize_phone(record.get('phone', ''))
                
                # Нормализация ИНН
                inn = self._normalize_inn(record.get('inn', ''))
                
                # Создание уникального ключа
                unique_key = f"{fio}_{record.get('dob', '')}" if record.get('dob') else f"{inn}"
                
                # Проверка на дубли
                if unique_key in seen_keys:
                    continue
                
                seen_keys.add(unique_key)
                
                normalized_record = {
                    'lead_id': record.get('lead_id', f"lead_{len(normalized_data):06d}"),
                    'fio': fio,
                    'phone': phone,
                    'inn': inn,
                    'dob': record.get('dob', ''),
                    'address': record.get('address', ''),
                    'source': record.get('source', 'unknown'),
                    'tags': record.get('tags', ''),
                    'email': record.get('email', ''),
                    'region': record.get('region', self._extract_region(record.get('address', ''))),
                    'created_at': datetime.now().isoformat()
                }
                
                normalized_data.append(normalized_record)
                
            except Exception as e:
                logger.error(f"Error normalizing record: {e}")
                continue
        
        logger.info(f"Normalized {len(normalized_data)} records, removed {len(raw_data) - len(normalized_data)} duplicates")
        return normalized_data
    
    def _normalize_fio(self, fio: str) -> str:
        """Нормализация ФИО"""
        if not fio:
            return ""
        
        # Очистка от лишних символов
        fio = re.sub(r'[^\w\s]', '', fio)
        
        # Разделение на части и приведение к правильному регистру
        parts = fio.split()
        normalized_parts = []
        
        for part in parts:
            if part:
                normalized_parts.append(part.capitalize())
        
        return ' '.join(normalized_parts)
    
    def _normalize_phone(self, phone: str) -> str:
        """Нормализация телефона"""
        if not phone:
            return ""
        
        # Удаление всех символов кроме цифр
        digits = self.phone_pattern.sub('', phone)
        
        # Приведение к формату +7XXXXXXXXXX
        if len(digits) == 11 and digits.startswith('8'):
            return f"+7{digits[1:]}"
        elif len(digits) == 10:
            return f"+7{digits}"
        elif len(digits) == 11 and digits.startswith('7'):
            return f"+{digits}"
        
        return phone  # Возвращаем как есть, если не удалось нормализовать
    
    def _normalize_inn(self, inn: str) -> str:
        """Нормализация ИНН"""
        if not inn:
            return ""
        
        # Удаление всех символов кроме цифр
        digits = re.sub(r'[^\d]', '', inn)
        
        # Проверка на валидность
        if self.inn_pattern.match(digits):
            return digits
        
        return ""
    
    def _extract_region(self, address: str) -> str:
        """Извлечение региона из адреса"""
        if not address:
            return "unknown"
        
        address_lower = address.lower()
        
        region_mapping = {
            'москва': 'moscow',
            'московская': 'moscow',
            'татарстан': 'tatarstan',
            'казань': 'tatarstan',
            'саратов': 'saratov',
            'калуга': 'kaluga',
            'санкт-петербург': 'spb',
            'петербург': 'spb',
            'новосибирск': 'nsk'
        }
        
        for region_name, region_code in region_mapping.items():
            if region_name in address_lower:
                return region_code
        
        return "unknown"
    
    async def filter_by_regions(self, data: List[Dict], regions: List[str]) -> List[Dict]:
        """Фильтрация данных по регионам"""
        if not regions:
            return data
        
        filtered_data = [record for record in data if record.get('region') in regions]
        
        logger.info(f"Filtered {len(filtered_data)} records by regions: {', '.join(regions)}")
        return filtered_data
    