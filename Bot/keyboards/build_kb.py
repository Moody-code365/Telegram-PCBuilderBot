from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def usage_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Игры")],
            [KeyboardButton(text="💼 Работа")],
            [KeyboardButton(text="🔄 Универсальный")],
            [KeyboardButton(text="⬅️ Отмена")],
        ],
        resize_keyboard=True,
    )