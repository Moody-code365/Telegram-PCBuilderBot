from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(F.text == "ℹ️ О боте")
@router.message(Command("about"))
async def cmd_about(message: Message) -> None:
    await message.answer(
        "ℹ️ *PC Builder Bot v2.0*\n\n"
        "Автоматический подбор комплектующих для ПК.\n"
        "Учитывает совместимость, бюджет и назначение.\n\n"
        "⚙️ Python · Aiogram 3",
        parse_mode="Markdown",
    )