from aiogram import Router, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()

@router.message(CommandStart())
async def hello(message: Message):
    await message.answer("👋 Привет! Я бот для подбора комплектующих ПК.\n"
        "Введите /build чтобы начать сборку.")


def register_start_handlers(dp):
    dp.include_router(router)