"""
Конфигурация AI функциональности.
"""

import os
from typing import Optional

# Настройки из environment variables
ENABLE_AI = os.getenv("ENABLE_AI", "true").lower() == "true"
AI_TIMEOUT = int(os.getenv("AI_TIMEOUT", "10"))  # секунд
AI_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "2"))

# Настройки модели
AI_MODEL = os.getenv("AI_MODEL", "openai/gpt-oss-120b")
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.3"))

# Fallback настройки
FALLBACK_ON_ERROR = os.getenv("FALLBACK_ON_ERROR", "true").lower() == "true"
AI_FALLBACK_MESSAGE = "🔄 Переключаюсь на стандартный алгоритм сборки..."

# Логирование
LOG_AI_REQUESTS = os.getenv("LOG_AI_REQUESTS", "true").lower() == "true"  # Включаем по умолчанию
LOG_AI_RESPONSES = os.getenv("LOG_AI_RESPONSES", "true").lower() == "true"  # Логировать ответы
LOG_AI_PERFORMANCE = os.getenv("LOG_AI_PERFORMANCE", "true").lower() == "true"  # Время ответа

# AI сообщения
AI_SUCCESS_MESSAGES = [
    "🤖 **ИИ подобрал оптимальные компоненты!**",
    "🧠 **Умная сборка с помощью искусственного интеллекта**",
    "⚡ **AI проанализировал тысячи вариантов и выбрал лучший**"
]
AI_FALLBACK_MESSAGES = [
    "🔄 **Переключаюсь на стандартный алгоритм сборки...**",
    "⚙️ **Использую проверенный метод подбора компонентов**",
    "🔧 **Сборка по стандартному алгоритму**"
]


def get_ai_config() -> dict:
    """Возвращает текущую конфигурацию AI."""
    try:
        return {
            "enabled": ENABLE_AI,
            "timeout": AI_TIMEOUT,
            "max_retries": AI_MAX_RETRIES,
            "model": AI_MODEL,
            "temperature": AI_TEMPERATURE,
            "fallback_on_error": FALLBACK_ON_ERROR,
            "log_requests": LOG_AI_REQUESTS,
            "log_responses": LOG_AI_RESPONSES,
            "log_performance": LOG_AI_PERFORMANCE
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка получения AI конфигурации: {e}")
        return {
            "enabled": False,
            "timeout": 10,
            "max_retries": 2,
            "model": "openai/gpt-oss-120b",
            "temperature": 0.3,
            "fallback_on_error": True,
            "log_requests": False,
            "log_responses": False,
            "log_performance": False
        }


def is_ai_enabled() -> bool:
    """Проверяет включен ли AI."""
    return ENABLE_AI and bool(os.getenv("GROQ_API"))


def get_ai_status_message() -> str:
    """Возвращает сообщение о статусе AI."""
    if is_ai_enabled():
        return "🤖 AI ассистент активен"
    return "⚙️ Используется стандартный алгоритм"


def get_ai_success_message() -> str:
    """Возвращает случайное сообщение об успешной AI сборке."""
    import random
    return random.choice(AI_SUCCESS_MESSAGES)


def get_ai_fallback_message() -> str:
    """Возвращает случайное сообщение о fallback."""
    import random
    return random.choice(AI_FALLBACK_MESSAGES)


def log_ai_request(prompt: str, model: str):
    """Логирует AI запрос."""
    if LOG_AI_REQUESTS:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔤 ===== AI ЗАПРОС =====")
        logger.info(f"📝 Модель: {model}")
        logger.info(f"📤 Промпт: {prompt[:200]}...")  # Первые 200 символов
        logger.info(f"🔤 =================")


def log_ai_response(response: str, duration: float = None):
    """Логирует AI ответ."""
    import logging
    logger = logging.getLogger(__name__)
    
    if LOG_AI_RESPONSES:
        logger.info(f"🔤 ===== AI ОТВЕТ =====")
        logger.info(f"📝 Длина: {len(response)} символов")
        logger.info(f"📥 Ответ: {response[:300]}...")  # Первые 300 символов
        logger.info(f"🔤 =================")
    
    if LOG_AI_PERFORMANCE and duration:
        logger.info(f"⏱️ Время ответа AI: {duration:.2f} сек")
