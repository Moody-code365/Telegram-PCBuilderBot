from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from Bot.keyboards.main_kb import main_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 Привет! Я — бот-сборщик ПК.\n\n"
        "Подберу оптимальные комплектующие под твой бюджет.\n"
        "Нажми кнопку ниже, чтобы начать!",
        reply_markup=main_keyboard(),
    )