from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_start_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Начать подбор")],
            [KeyboardButton(text="Помощ")],
            [KeyboardButton(text="About")],
        ],
        resize_keyboard=True
    )
    return keyboard
