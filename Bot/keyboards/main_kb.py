from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню бота."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🖥 Собрать ПК")],
            [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="ℹ️ О боте")],
        ],
        resize_keyboard=True,
    )