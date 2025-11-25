from aiogram import Router, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.answer(
        "🛠 Доступные команды:\n"
        "/start — запуск бота\n"
        "/help — список команд\n"
        "/about — о боте\n"
        "/build — собрать ПК\n"
    )

def register_help_handlers(dp: Dispatcher):
    dp.include_router(router)
