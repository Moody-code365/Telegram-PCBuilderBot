"""
Расширенный форматтер с красивыми AI сообщениями.
"""

from typing import Dict, Optional
from Bot.utils.formatter import format_build_message


def format_enhanced_ai_build_message(
    build: Dict[str, Optional[Dict]], 
    budget: int, 
    usage: str, 
    used_ai: bool = False,
    ai_explanation: str = ""
) -> str:
    """
    Форматирует красивое сообщение о сборке ПК с AI элементами.
    """
    
    # Базовое сообщение о сборке
    base_message = format_build_message(build, budget, usage)
    
    if used_ai:
        from Bot.config.ai_config import get_ai_success_message
        
        # Добавляем красивый AI заголовок
        ai_header = f"{get_ai_success_message()}\n\n"
        
        # Добавляем объяснение если есть
        if ai_explanation:
            ai_content = f"💬 **Комментарий ИИ:**\n{ai_explanation}\n\n"
        else:
            ai_content = ""
        
        # Добавляем статистику
        component_count = len([c for c in build.values() if c])
        ai_stats = f"🧠 *ИИ проанализировал {component_count} компонентов и подобрал оптимальную конфигурацию*\n\n"
        
        # Добавляем футер
        ai_footer = "---\n\n🤖 *Умная сборка powered by AI*\n⚡ *Оптимизировано для максимальной производительности*"
        
        # Комбинируем все
        enhanced_message = base_message + "\n\n" + ai_header + ai_content + ai_stats + ai_footer
        
    else:
        from Bot.config.ai_config import get_ai_fallback_message
        
        # Стандартное сообщение без ИИ
        fallback_header = f"{get_ai_fallback_message()}\n\n"
        standard_footer = "\n\n---\n\n⚙️ *Сборка по стандартному алгоритму*"
        enhanced_message = base_message + "\n\n" + fallback_header + standard_footer
    
    return enhanced_message


def get_ai_welcome_message(budget: str, usage: str) -> str:
    """Возвращает красивое приветственное сообщение для AI сборки."""
    return (
        f"🤖 *Анализирую ваши требования...*\n\n"
        f"💰 Бюджет: *{budget}*\n"
        f"🎯 Назначение: *{usage}*\n\n"
        f"⚡ *ИИ подбирает оптимальные компоненты...*"
    )


def get_ai_process_messages() -> list:
    """Возвращает список сообщений о процессе AI сборки."""
    return [
        "🔍 *Анализирую совместимость компонентов...*\n\n"
        "🧠 *ИИ проверяет оптимальные конфигурации...*\n\n"
        "⚙️ *Формирую финальную сборку...*"
    ]


def get_ai_completion_message(used_ai: bool, ai_explanation: str = "") -> str:
    """Возвращает сообщение о завершении сборки."""
    if used_ai:
        from Bot.config.ai_config import get_ai_success_message
        
        message_parts = [
            f"{get_ai_success_message()}\n\n",
            "🎯 *Оптимальная сборка сформирована!*\n\n"
        ]
        
        if ai_explanation:
            message_parts.append(f"💬 *Комментарий ИИ:* {ai_explanation}\n\n")
            
        message_parts.append("📋 *Вот ваша идеальная конфигурация:*")
        
        return "".join(message_parts)
    else:
        from Bot.config.ai_config import get_ai_fallback_message
        
        return (
            f"{get_ai_fallback_message()}\n\n"
            "✅ *Готово! Сборка завершена...*\n\n"
            "📋 *Вот ваша конфигурация:*"
        )


def get_build_status_emoji(used_ai: bool) -> str:
    """Возвращает эмодзи статуса сборки."""
    return "🤖" if used_ai else "⚙️"


def format_price_with_emoji(price: int) -> str:
    """Форматирует цену с эмодзи."""
    return f"💰 {price:,} ₸"


def format_component_with_emoji(component_name: str, price: int) -> str:
    """Форматирует компонент с эмодзи."""
    return f"🔧 {component_name} ({format_price_with_emoji(price)})"
