"""
Хранение пользовательских предпочтений для сборки ПК.
"""

from typing import Dict, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class UserPreferences:
    """Предпочтения пользователя для сборки ПК."""
    budget: int = 0
    usage: str = "gaming"  # gaming, work, universal
    cpu_brand: Optional[str] = None  # "intel", "amd", None
    gpu_brand: Optional[str] = None  # "nvidia", "radeon", None
    need_gpu: Optional[bool] = None  # True, False, None
    step: str = "budget"  # budget, usage, cpu_brand, gpu_brand, gpu_need, confirm
    
    def to_dict(self) -> Dict:
        """Конвертирует в словарь для AI."""
        return {
            "cpu_brand": self.cpu_brand.upper() if self.cpu_brand else None,
            "gpu_brand": self.gpu_brand.upper() if self.gpu_brand else None,
            "need_gpu": self.need_gpu
        }
    
    def reset(self):
        """Сбрасывает все настройки кроме бюджета."""
        self.usage = "gaming"
        self.cpu_brand = None
        self.gpu_brand = None
        self.need_gpu = None
        self.step = "budget"


# Глобальное хранилище предпочтений
_user_preferences: Dict[int, UserPreferences] = {}


def get_user_preferences(user_id: int) -> UserPreferences:
    """Получает предпочтения пользователя."""
    if user_id not in _user_preferences:
        _user_preferences[user_id] = UserPreferences()
    return _user_preferences[user_id]


def set_user_preferences(user_id: int, **kwargs):
    """Устанавливает предпочтения пользователя."""
    prefs = get_user_preferences(user_id)
    for key, value in kwargs.items():
        if hasattr(prefs, key):
            setattr(prefs, key, value)
        else:
            logger.warning(f"Неизвестное предпочтение: {key}")


def clear_user_preferences(user_id: int):
    """Очищает предпочтения пользователя."""
    if user_id in _user_preferences:
        del _user_preferences[user_id]


def get_usage_display(usage: str) -> str:
    """Возвращает красивое название назначения."""
    displays = {
        "gaming": "🎮 Игровой ПК",
        "work": "💻 Рабочая станция", 
        "universal": "⚡ Универсальный ПК"
    }
    return displays.get(usage, usage)


def get_cpu_brand_display(brand: Optional[str]) -> str:
    """Возвращает красивое название бренда CPU."""
    displays = {
        "intel": "🔵 Intel",
        "amd": "🔴 AMD",
        None: "🎲 Любой"
    }
    return displays.get(brand, brand)


def get_gpu_brand_display(brand: Optional[str]) -> str:
    """Возвращает красивое название бренда GPU."""
    displays = {
        "nvidia": "🟢 NVIDIA",
        "radeon": "🔴 AMD Radeon", 
        None: "🎲 Любой"
    }
    return displays.get(brand, brand)


def get_gpu_need_display(need_gpu: Optional[bool]) -> str:
    """Возвращает красивое описание необходимости видеокарты."""
    if need_gpu is True:
        return "🎮 Нужна дискретная видеокарта"
    elif need_gpu is False:
        return "💻 Достаточно встроенной графики"
    else:
        return "🎲 Не определено"


def format_preferences_summary(user_id: int) -> str:
    """Форматирует сводку предпочтений пользователя."""
    prefs = get_user_preferences(user_id)
    
    lines = [
        f"💰 **Бюджет:** {prefs.budget:,} ₸",
        f"🎯 **Назначение:** {get_usage_display(prefs.usage)}",
        f"🖥️ **Процессор:** {get_cpu_brand_display(prefs.cpu_brand)}",
    ]
    
    if prefs.need_gpu is not False:
        lines.append(f"🎮 **Видеокарта:** {get_gpu_brand_display(prefs.gpu_brand)}")
    else:
        lines.append(f"🎮 **Видеокарта:** {get_gpu_need_display(prefs.need_gpu)}")
    
    return "\n".join(lines)
