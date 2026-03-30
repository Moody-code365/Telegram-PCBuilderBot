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
LOG_AI_REQUESTS = os.getenv("LOG_AI_REQUESTS", "false").lower() == "true"


def get_ai_config() -> dict:
    """Возвращает текущую конфигурацию AI."""
    return {
        "enabled": ENABLE_AI,
        "timeout": AI_TIMEOUT,
        "max_retries": AI_MAX_RETRIES,
        "model": AI_MODEL,
        "temperature": AI_TEMPERATURE,
        "fallback_on_error": FALLBACK_ON_ERROR,
        "log_requests": LOG_AI_REQUESTS
    }


def is_ai_enabled() -> bool:
    """Проверяет включен ли AI."""
    return ENABLE_AI and bool(os.getenv("GROQ_API"))


def get_ai_status_message() -> str:
    """Возвращает сообщение о статусе AI."""
    if is_ai_enabled():
        return "🤖 AI ассистент активен"
    return "⚙️ Используется стандартный алгоритм"
