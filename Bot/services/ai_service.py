# ai_service.py
import logging
from groq import Groq
from config import GROQ_API
from Bot.config.ai_config import get_ai_config

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        config = get_ai_config()
        
        if not GROQ_API:
            logger.warning("GROQ_API ключ не найден")
            self.client = None
            return
            
        try:
            self.client = Groq(api_key=GROQ_API)
            self.model = config["model"]
            self.timeout = config["timeout"]
            self.max_retries = config["max_retries"]
            self.temperature = config["temperature"]
            logger.info(f"AI сервис инициализирован с моделью {self.model}")
        except Exception as e:
            logger.error(f"Ошибка инициализации AI сервиса: {e}")
            self.client = None

    def is_available(self) -> bool:
        """Проверяет доступен ли AI сервис."""
        return self.client is not None

    def get_completion(self, prompt: str, use_json_format: bool = True):
        """Получает ответ от AI с обработкой ошибок."""
        if not self.is_available():
            logger.warning("AI сервис недоступен")
            return None
            
        try:
            messages = [{"role": "user", "content": prompt}]
            
            # Добавляем system prompt для лучшего форматирования
            if use_json_format:
                messages.insert(0, {
                    "role": "system", 
                    "content": "Отвечай только валидным JSON. Никакого текста вне JSON."
                })
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"} if use_json_format else None,
                temperature=self.temperature,
                timeout=self.timeout
            )
            
            result = response.choices[0].message.content
            logger.debug(f"AI ответ получен: {len(result)} символов")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка запроса к AI: {e}")
            return None
