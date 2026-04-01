# ai_service.py
import json
import logging
import re
import time
from groq import Groq, APIConnectionError, APITimeoutError, RateLimitError
from config import GROQ_API
from Bot.config.ai_config import get_ai_config

logger = logging.getLogger(__name__)


class AIService:
    """Сервис для работы с Groq AI API."""

    def __init__(self):
        config = get_ai_config()

        if not GROQ_API:
            logger.warning("GROQ_API ключ не найден — AI сервис отключён")
            self.client = None
            return

        try:
            self.client      = Groq(api_key=GROQ_API)
            self.model       = config["model"]
            self.timeout     = config.get("timeout", 30)
            self.max_retries = config.get("max_retries", 3)
            self.temperature = config.get("temperature", 0.3)
            logger.info(f"AI сервис запущен | модель={self.model} | t={self.temperature} | retries={self.max_retries}")
        except Exception as e:
            logger.error(f"Ошибка инициализации AI сервиса: {e}")
            self.client = None

    # ── Публичный интерфейс ──────────────────────────────────────────────────

    def is_available(self) -> bool:
        return self.client is not None

    def get_completion(self, prompt: str, use_json_format: bool = True) -> str | None:
        """
        Отправляет запрос к Groq и возвращает текст ответа.
        При временных ошибках делает до max_retries попыток с паузой.
        Если use_json_format=True — извлекает и валидирует JSON из ответа.
        Возвращает None если все попытки неудачны.
        """
        if not self.is_available():
            logger.warning("AI сервис недоступен")
            return None

        messages = self._build_messages(prompt, use_json_format)
        
        # Используем новую систему логирования
        from Bot.config.ai_config import log_ai_request, log_ai_response
        import time
        
        start_time = time.time()
        log_ai_request(prompt, self.model)
        
        logger.debug(f"→ AI запрос | json={use_json_format} | {len(prompt)} симв.")

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model       = self.model,
                    messages    = messages,
                    temperature = self.temperature,
                    timeout     = self.timeout,
                )
                raw = response.choices[0].message.content or ""
                duration = time.time() - start_time
                
                logger.debug(f"← AI ответ | {len(raw)} симв.")
                log_ai_response(raw, duration)

                if use_json_format:
                    extracted = self._extract_json(raw)
                    if extracted is None:
                        logger.warning(f"JSON не найден в ответе (попытка {attempt})")
                        if attempt < self.max_retries:
                            time.sleep(1)
                        continue
                    return extracted

                return raw

            except RateLimitError:
                wait = 2 ** attempt  # 2, 4, 8 сек
                logger.warning(f"Rate limit — жду {wait}с (попытка {attempt}/{self.max_retries})")
                time.sleep(wait)

            except APITimeoutError:
                logger.warning(f"Таймаут {self.timeout}с (попытка {attempt}/{self.max_retries})")
                if attempt < self.max_retries:
                    time.sleep(1)

            except APIConnectionError as e:
                logger.error(f"Ошибка соединения с Groq: {e}")
                break  # сетевые ошибки — не ретраим

            except Exception as e:
                logger.error(f"Неожиданная ошибка Groq (попытка {attempt}): {e}")
                if attempt < self.max_retries:
                    time.sleep(1)

        logger.error(f"AI не ответил после {self.max_retries} попыток")
        return None

    # ── Вспомогательные методы ───────────────────────────────────────────────

    def _build_messages(self, prompt: str, use_json_format: bool) -> list:
        messages = []
        if use_json_format:
            system_content = "JSON only."  # МИНИМАЛЬНО
            
            messages.append({
                "role": "system",
                "content": system_content,
            })
        messages.append({"role": "user", "content": prompt})
        return messages

    @staticmethod
    def _extract_json(text: str) -> str | None:
        """
        Извлекает первый валидный JSON-объект из текста.
        Работает даже если модель обернула ответ в ```json ... ```.
        """
        # Убираем markdown-блоки
        text = re.sub(r"```(?:json)?", "", text).strip()

        # Ищем первый {...}
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None

        candidate = match.group(0)
        try:
            json.loads(candidate)  # проверяем валидность
            return candidate
        except json.JSONDecodeError:
            return None
