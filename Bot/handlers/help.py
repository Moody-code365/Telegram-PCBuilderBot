from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(F.text == "❓ Помощь")
@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📖 *Как пользоваться ботом:*\n\n"
        "1️⃣ Нажми «🖥 Собрать ПК»\n"
        "2️⃣ Введи бюджет числом (например: 400000)\n"
        "3️⃣ Выбери назначение (игры / работа / универсальный)\n"
        "4️⃣ Получи результат!\n\n"
        "📌 Бот подберёт комплектующие *строго в пределах* бюджета.\n"
        "📌 Любой компонент можно заменить — спроси у менеджера.\n\n"
        "Команды: /start · /build · /help · /about",
        parse_mode="Markdown",
    )