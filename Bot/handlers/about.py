from aiogram import Router, Dispatcher, F
from aiogram.filters import Command, command
from aiogram.types import Message

router = Router()

@router.message(F.text == "About")
@router.message(Command('about'))
async def cmd_about(message: Message):
    await message.answer(
        "🤖 Бот создан для автоматического подбора ПК.\n"
        "Работает на Python + Aiogram.\n"
    )

def register_about_handlers(dp: Dispatcher):
    dp.include_router(router)