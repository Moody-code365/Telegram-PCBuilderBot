from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(F.text == "ℹ️ О боте")
@router.message(Command("about"))
async def cmd_about(message: Message) -> None:
    await message.answer(
        "🤖 *PC Builder Bot*\n\n"
        "Автоматический подбор комплектующих для ПК.\n"
        "Учитывает совместимость, бюджет и назначение.\n\n"
        "⚙️ Python · Aiogram 3\n"
        "📦 Версия: 2.0",
        parse_mode="Markdown",
    )