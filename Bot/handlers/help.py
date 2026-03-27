from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(F.text == "❓ Помощь")
@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "🛠 *Доступные команды:*\n\n"
        "/start — запуск бота\n"
        "/build — собрать ПК\n"
        "/help — список команд\n"
        "/about — о боте\n\n"
        "💡 *Как пользоваться:*\n"
        "1. Нажми «🖥 Собрать ПК»\n"
        "2. Укажи бюджет\n"
        "3. Выбери назначение\n"
        "4. Получи готовую сборку!",
        parse_mode="Markdown",
    )