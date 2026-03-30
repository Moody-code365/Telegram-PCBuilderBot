from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from Bot.keyboards.main_kb import main_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 *Привет!* Я — бот для подбора комплектующих ПК.\n\n"
        "🔹 Укажи бюджет\n"
        "🔹 Выбери назначение\n"
        "🔹 Получи готовую сборку\n\n"
        "Нажми кнопку ниже, чтобы начать 👇",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )