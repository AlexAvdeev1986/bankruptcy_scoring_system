import os

class Config:
    # Настройки базы данных
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/scoring.db")
    
    # Настройки внешних сервисов
    FSSP_API_URL = "https://fssp.gov.ru/api/v1/search"
    FEDRESURS_API_URL = "https://api.fedresurs.ru/v1.0/bankruptcy"
    ROSREESTR_API_URL = "https://rosreestr.gov.ru/api/online/fir_objects"
    COURT_API_URL = "https://sudrf.ru/api/v1/cases"
    FNS_API_URL = "https://service.nalog.ru/inn-proc.do"
    
    # Настройки прокси
    PROXY_FILE = "proxies.txt"
    PROXY_ENABLED = True
    PROXY_TIMEOUT = 10
    
    # API ключи
    CAPTCHA_API_KEY = os.getenv("CAPTCHA_API_KEY", "your_anti_captcha_key")
    FEDRESURS_API_KEY = os.getenv("FEDRESURS_API_KEY", "your_fedresurs_key")
    
    # Настройки запросов
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    
    # Лимиты
    MAX_LEADS_PER_RUN = 10000
    MAX_ERRORS_BEFORE_FAIL = 100
    
    # Настройки логов
    LOG_DIR = "logs"
    LOG_FILE = "app.log"
    
    # Пути к данным
    DATA_DIR = "data"
    EXPORT_DIR = "exports"
    
    @classmethod
    def ensure_directories(cls):
        """Создание необходимых директорий"""
        os.makedirs(cls.LOG_DIR, exist_ok=True)
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.EXPORT_DIR, exist_ok=True)
        