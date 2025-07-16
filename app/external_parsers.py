import aiohttp
import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Optional
from bs4 import BeautifulSoup
import time
import re

from .config import Config
from .proxy_manager import ProxyManager
from .captcha_solver import CaptchaSolver

logger = logging.getLogger(__name__)

class ExternalParsers:
    def __init__(self):
        self.session = None
        self.proxy_manager = ProxyManager()
        self.captcha_solver = CaptchaSolver()
        self.proxies = []
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.proxy_manager.load_proxies()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_fssp_data(self, lead: Dict) -> Dict:
        """Получение данных из ФССП с обработкой капчи"""
        try:
            # Получаем случайный прокси
            proxy = self.proxy_manager.get_random_proxy()
            proxy_url = f"http://{proxy}" if proxy else None
            
            # Заголовки для имитации браузера
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
                "Connection": "keep-alive",
            }
            
            # Шаг 1: Получение страницы с капчей
            async with self.session.get(
                "https://fssp.gov.ru/iss/ip/",
                headers=headers,
                proxy=proxy_url,
                timeout=Config.PROXY_TIMEOUT
            ) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Поиск URL капчи
                captcha_img = soup.find('img', {'class': 'captcha-img'})
                if not captcha_img:
                    logger.error("Captcha image not found")
                    raise Exception("Captcha image not found")
                    
                captcha_url = captcha_img['src']
                captcha_token = soup.find('input', {'name': 'captcha_token'})['value']
            
            # Шаг 2: Решение капчи
            captcha_text = self.captcha_solver.solve_captcha(captcha_url)
            if not captcha_text:
                logger.error("Failed to solve captcha")
                raise Exception("Failed to solve captcha")
            
            # Шаг 3: Формирование данных для запроса
            fio_parts = lead['fio'].split()
            last_name = fio_parts[0] if len(fio_parts) > 0 else ""
            first_name = fio_parts[1] if len(fio_parts) > 1 else ""
            middle_name = fio_parts[2] if len(fio_parts) > 2 else ""
            
            form_data = {
                'is': 'Взыскатель',
                'region': '-1',
                'firstname': first_name,
                'lastname': last_name,
                'patronymic': middle_name,
                'bd': lead.get('dob', ''),
                'captcha': captcha_text,
                'captcha_token': captcha_token
            }
            
            # Шаг 4: Отправка запроса с решенной капчей
            async with self.session.post(
                "https://fssp.gov.ru/iss/ip/",
                data=form_data,
                headers=headers,
                proxy=proxy_url,
                timeout=Config.PROXY_TIMEOUT
            ) as response:
                result_html = await response.text()
                result_soup = BeautifulSoup(result_html, 'html.parser')
                
                # Обработка результатов
                debts = []
                for row in result_soup.select('.search-result-item'):
                    try:
                        amount = float(row.select_one('.amount').text.strip().replace(' ', '').replace(',', '.'))
                        creditor = row.select_one('.creditor').text.strip()
                        debt_type = row.select_one('.type').text.strip()
                        
                        debts.append({
                            'amount': amount,
                            'creditor': creditor,
                            'type': debt_type
                        })
                    except:
                        continue
                
                total_debt = sum(d['amount'] for d in debts)
                main_type = max(set([d['type'] for d in debts]), key=[d['type'] for d in debts].count) if debts else 'unknown'
                
                return {
                    'fssp_debt_amount': total_debt,
                    'fssp_debt_type': main_type,
                    'fssp_creditor': debts[0]['creditor'] if debts else '',
                    'fssp_status': 'active' if total_debt > 0 else 'none',
                    'fssp_updated': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting FSSP data for {lead.get('fio')}: {e}")
            return {
                'fssp_debt_amount': 0,
                'fssp_debt_type': 'unknown',
                'fssp_creditor': '',
                'fssp_status': 'error',
                'fssp_updated': datetime.now().isoformat()
            }
    
    async def get_fedresurs_data(self, lead: Dict) -> Dict:
        """Проверка банкротства через Федресурс"""
        try:
            if not lead.get('inn'):
                return {
                    'fedresurs_is_bankrupt': False,
                    'fedresurs_procedure': 'no_inn',
                    'fedresurs_updated': datetime.now().isoformat()
                }
            
            # API Федресурса
            url = f"{Config.FEDRESURS_API_URL}/Search"
            params = {
                "inn": lead['inn'],
                "token": Config.FEDRESURS_API_KEY
            }
            
            async with self.session.get(
                url, 
                params=params, 
                timeout=Config.REQUEST_TIMEOUT
            ) as response:
                data = await response.json()
            
            # Проверяем наличие активных процедур банкротства
            active_procedures = [p for p in data.get('procedures', []) if p.get('status') == 'ACTIVE']
            
            return {
                'fedresurs_is_bankrupt': len(active_procedures) > 0,
                'fedresurs_procedure': active_procedures[0]['type'] if active_procedures else 'none',
                'fedresurs_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting Fedresurs data for {lead.get('fio')}: {e}")
            return {
                'fedresurs_is_bankrupt': False,
                'fedresurs_procedure': 'error',
                'fedresurs_updated': datetime.now().isoformat()
            }
    
    async def get_rosreestr_data(self, lead: Dict) -> Dict:
        """Проверка недвижимости через Росреестр"""
        try:
            if not lead.get('inn'):
                return {
                    'rosreestr_has_property': False,
                    'rosreestr_property_count': 0,
                    'rosreestr_updated': datetime.now().isoformat()
                }
            
            # API Росреестра
            url = Config.ROSREESTR_API_URL
            payload = {
                "filter": {
                    "text": lead['inn'],
                    "objectType": ["real_estate"]
                }
            }
            
            async with self.session.post(
                url, 
                json=payload, 
                timeout=Config.REQUEST_TIMEOUT
            ) as response:
                data = await response.json()
            
            properties = data.get('results', [])
            
            return {
                'rosreestr_has_property': len(properties) > 0,
                'rosreestr_property_count': len(properties),
                'rosreestr_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting Rosreestr data for {lead.get('fio')}: {e}")
            return {
                'rosreestr_has_property': False,
                'rosreestr_property_count': 0,
                'rosreestr_updated': datetime.now().isoformat()
            }
    
    async def get_court_data(self, lead: Dict) -> Dict:
        """Поиск судебных приказов в ГАС Правосудие"""
        try:
            # Формируем запрос
            url = "https://sudrf.ru/index.php"
            params = {
                "id": "300",
                "act": "ajax_search",
                "searchform": lead['fio'],
                "court_subj": "0"
            }
            
            # Используем синхронный запрос для простоты
            response = requests.get(url, params=params, timeout=Config.REQUEST_TIMEOUT)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем приказы за последние 3 месяца
            has_recent_order = False
            current_date = datetime.now()
            order_date = None
            
            for item in soup.select('.resultItem'):
                date_str = item.select_one('.date').text.strip()
                try:
                    order_date = datetime.strptime(date_str, "%d.%m.%Y")
                    if (current_date - order_date).days <= 90:
                        has_recent_order = True
                        break
                except:
                    continue
            
            return {
                'court_has_order': has_recent_order,
                'court_order_date': order_date.isoformat() if has_recent_order and order_date else None,
                'court_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting court data for {lead.get('fio')}: {e}")
            return {
                'court_has_order': False,
                'court_order_date': None,
                'court_updated': datetime.now().isoformat()
            }
    
    async def check_inn_status(self, inn: str) -> Dict:
        """Проверка статуса ИНН в ФНС"""
        try:
            # API ФНС
            url = Config.FNS_API_URL
            payload = {
                "c": "find",
                "inn": inn,
                "captcha": "",
                "captchaToken": ""
            }
            
            async with self.session.post(
                url, 
                data=payload, 
                timeout=Config.REQUEST_TIMEOUT
            ) as response:
                data = await response.json()
            
            # Проверяем статус ответа
            if data.get('code') == 0:
                return {
                    'inn_active': True,
                    'inn_status': 'active',
                    'inn_updated': datetime.now().isoformat()
                }
            else:
                return {
                    'inn_active': False,
                    'inn_status': data.get('message', 'inactive'),
                    'inn_updated': datetime.now().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Error checking INN {inn}: {e}")
            return {
                'inn_active': False,
                'inn_status': 'error',
                'inn_updated': datetime.now().isoformat()
            }
            