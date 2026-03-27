from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def budget_keyboard() -> ReplyKeyboardMarkup:
    """Выбор бюджета."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 до 150 000 ₸")],
            [KeyboardButton(text="💰 150–250 000 ₸")],
            [KeyboardButton(text="💰 250–400 000 ₸")],
            [KeyboardButton(text="💰 400–600 000 ₸")],
            [KeyboardButton(text="💰 600–900 000 ₸")],
            [KeyboardButton(text="💰 900 000 ₸+")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )


def usage_keyboard() -> ReplyKeyboardMarkup:
    """Выбор назначения ПК."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Игры")],
            [KeyboardButton(text="🧪 Работа")],
            [KeyboardButton(text="🎯 Универсальный")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )


def preferences_keyboard() -> ReplyKeyboardMarkup:
    """Предпочтения пользователя."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔇 Тихий"), KeyboardButton(text="🌈 RGB")],
            [KeyboardButton(text="📦 Компактный"), KeyboardButton(text="⚡ Максимум мощности")],
            [KeyboardButton(text="🚫 Без предпочтений")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )