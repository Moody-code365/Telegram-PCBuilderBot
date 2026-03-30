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
        # Добавляем красивый AI заголовок
        ai_header = "🤖 **✨ Сборка создана искусственным интеллектом**\n\n"
        
        # Добавляем объяснение если есть
        if ai_explanation:
            ai_content = f"💡 **Рекомендация ИИ:**\n{ai_explanation}\n\n"
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
        # Стандартное сообщение без ИИ
        standard_footer = "\n\n---\n\n⚙️ *Сборка выполнена по стандартному алгоритму*"
        enhanced_message = base_message + standard_footer
    
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


def get_ai_completion_message(used_ai: bool) -> str:
    """Возвращает сообщение о завершении сборки."""
    if used_ai:
        return (
            "✨ *Готово! ИИ завершил анализ...*\n\n"
            "🎯 *Оптимальная сборка сформирована!*\n\n"
            "📋 *Вот ваша идеальная конфигурация:*"
        )
    else:
        return (
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
