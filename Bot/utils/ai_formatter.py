"""
Утилиты для форматирования сообщений с AI объяснениями.
"""

from typing import Dict, Optional
from Bot.utils.formatter import format_build_message


def format_ai_build_message(
    build: Dict[str, Optional[Dict]], 
    budget: int, 
    usage: str, 
    used_ai: bool = False,
    ai_explanation: str = ""
) -> str:
    """
    Форматирует сообщение о сборке ПК с учетом AI объяснений.
    
    Параметры:
    - build: словарь с компонентами
    - budget: бюджет
    - usage: назначение
    - used_ai: использовался ли ИИ
    - ai_explanation: объяснение от ИИ
    """
    
    # Базовое сообщение о сборке
    base_message = format_build_message(build, budget, usage)
    
    # Добавляем AI информацию если есть
    if used_ai and ai_explanation:
        ai_section = f"\n\n---\n\n🤖 **✨ Сборка создана искусственным интеллектом**\n\n💡 **Рекомендация ИИ:**\n{ai_explanation}\n\n🧠 *ИИ проанализировал {len([c for c in build.values() if c])} компонентов и подобрал оптимальную конфигурацию*"
        base_message += ai_section
    elif used_ai:
        ai_section = f"\n\n---\n\n🤖 **✨ Сборка создана искусственным интеллектом**\n\n🧠 *ИИ проанализировал {len([c for c in build.values() if c])} компонентов и подобрал оптимальную конфигурацию*"
        base_message += ai_section
    
    return base_message


def get_build_status_emoji(used_ai: bool) -> str:
    """Возвращает эмодзи статуса сборки."""
    return "🤖" if used_ai else "⚙️"


def add_ai_footer(message: str, used_ai: bool) -> str:
    """Добавляет футер с информацией об использовании ИИ."""
    if used_ai:
        return f"{message}\n\n---\n\n🤖 *Умная сборка powered by AI*\n⚡ *Оптимизировано для максимальной производительности*"
    return message
