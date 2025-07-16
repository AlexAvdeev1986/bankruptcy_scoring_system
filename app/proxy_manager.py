import logging
import random
import time

logger = logging.getLogger(__name__)

class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.last_loaded = 0
        self.load_interval = 3600  # 1 hour
    
    async def load_proxies(self, file_path: str = "proxies.txt"):
        """Загрузка списка прокси из файла с учетом интервала"""
        current_time = time.time()
        if current_time - self.last_loaded < self.load_interval and self.proxies:
            return
            
        try:
            with open(file_path, 'r') as f:
                self.proxies = [line.strip() for line in f if line.strip()]
            self.last_loaded = current_time
            logger.info(f"Loaded {len(self.proxies)} proxies")
        except FileNotFoundError:
            logger.warning("Proxy file not found, using empty list")
            self.proxies = []
    
    def get_random_proxy(self) -> str:
        """Получение случайного прокси"""
        if not self.proxies:
            return ""
        return random.choice(self.proxies)
    
    def mark_bad_proxy(self, proxy: str):
        """Пометить прокси как нерабочий"""
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            logger.info(f"Removed bad proxy: {proxy}")
            