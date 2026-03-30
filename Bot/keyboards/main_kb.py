from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🖥 Собрать ПК")],
            [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="ℹ️ О боте")],
        ],
        resize_keyboard=True,
    )