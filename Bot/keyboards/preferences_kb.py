"""
Клавиатуры для опроса предпочтений пользователя.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_cpu_brand_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора бренда процессора."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔵 Intel", callback_data="pref_cpu_intel"),
            InlineKeyboardButton(text="🔴 AMD", callback_data="pref_cpu_amd"),
        ],
        [
            InlineKeyboardButton(text="🎲 Неважно", callback_data="pref_cpu_any"),
        ]
    ])
    return keyboard


def get_gpu_brand_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора бренда видеокарты."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 NVIDIA", callback_data="pref_gpu_brand_nvidia"),
            InlineKeyboardButton(text="🔴 AMD Radeon", callback_data="pref_gpu_brand_radeon"),
        ],
        [
            InlineKeyboardButton(text="🎲 Неважно", callback_data="pref_gpu_brand_any"),
        ]
    ])
    return keyboard


def get_gpu_need_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора нужна ли видеокарта (для рабочих ПК)."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎮 Да, нужна (для игр/графики)", callback_data="pref_gpu_need_yes"),
            InlineKeyboardButton(text="💻 Нет, встроенной хватит (офис/работа)", callback_data="pref_gpu_need_no"),
        ]
    ])
    return keyboard


def get_preferences_summary_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения или изменения предпочтений."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Все верно", callback_data="pref_confirm"),
            InlineKeyboardButton(text="🔄 Изменить", callback_data="pref_change"),
        ]
    ])
    return keyboard
