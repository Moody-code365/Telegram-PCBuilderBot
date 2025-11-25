from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def budget_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="до 150 000 ₸")],
            [KeyboardButton(text="150–200 000 ₸")],
            [KeyboardButton(text="250–300 000 ₸")],
            [KeyboardButton(text="400–600 000 ₸")],
            [KeyboardButton(text="600 000 ₸+")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True
    )

def usage_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Игры")],
            [KeyboardButton(text="🧪 Работа")],
            [KeyboardButton(text="🎯 Универсальный")],
        ],
        resize_keyboard=True
    )

def preferences_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔇 Тихий")],
            [KeyboardButton(text="🌈 RGB")],
            [KeyboardButton(text="📦 Мини-ПК")],
            [KeyboardButton(text="Нет")],
        ],
        resize_keyboard=True
    )
