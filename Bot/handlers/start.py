from aiogram import Router, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from Bot.keyboards.build_kb import get_start_keyboard

router = Router()

@router.message(CommandStart())
async def hello(message: Message):
    await message.answer("👋 Привет! Я бот для подбора комплектующих ПК.\n"
        "Нажмите кнопку ниже, чтобы начать!",
        reply_markup=get_start_keyboard())


def register_start_handlers(dp):
    dp.include_router(router)