import logging
import requests
from .config import Config

logger = logging.getLogger(__name__)

class CaptchaSolver:
    def __init__(self):
        self.api_key = Config.CAPTCHA_API_KEY
    
    def solve_captcha(self, image_url: str) -> str:
        """Решение капчи через сервис Anti-Captcha"""
        if not self.api_key:
            logger.warning("CAPTCHA_API_KEY not set, captcha solving disabled")
            return ""
            
        try:
            # 1. Загрузка капчи
            response = requests.get(image_url)
            if response.status_code != 200:
                return ""
                
            # 2. Отправка на распознавание
            task_url = "https://api.anti-captcha.com/createTask"
            task_payload = {
                "clientKey": self.api_key,
                "task": {
                    "type": "ImageToTextTask",
                    "body": response.content.hex(),
                    "phrase": False,
                    "case": False,
                    "numeric": 0,
                    "math": False,
                    "minLength": 0,
                    "maxLength": 0
                }
            }
            
            task_response = requests.post(task_url, json=task_payload).json()
            task_id = task_response.get("taskId")
            if not task_id:
                return ""
            
            # 3. Получение результата
            result_url = "https://api.anti-captcha.com/getTaskResult"
            result_payload = {"clientKey": self.api_key, "taskId": task_id}
            
            for _ in range(10):  # 10 попыток с интервалом 5 секунд
                result_response = requests.post(result_url, json=result_payload).json()
                status = result_response.get("status")
                
                if status == "ready":
                    return result_response["solution"]["text"]
                elif status == "processing":
                    time.sleep(5)
                else:
                    break
            
            return ""
        except Exception as e:
            logger.error(f"Error solving captcha: {e}")
            return ""
        