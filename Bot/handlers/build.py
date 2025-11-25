from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from Bot.states.build_state import BuildPC

router = Router()

@router.message(F.text == "🚀 Начать подбор")
@router.message(Command("build"))
async def cmd_build(message: Message, state: FSMContext):
    await message.answer("💰 Введи свой бюджет ₸ :")
    await state.set_state(BuildPC.budget)

@router.message(BuildPC.budget)
async def set_budget(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("🚫 Введи число, например: 300000")

    await state.update_data(budget=int(message.text))
    await state.set_state(BuildPC.usage)

    await message.answer(
        "🖥 Для чего нужен ПК?\n"
        "1) Игры\n"
        "2) Работа\n"
        "3) Универсальный"
    )

@router.message(BuildPC.usage)
async def set_purpose(message: Message, state: FSMContext):
    usage = message.text.lower()

    if usage not in ["1", "2", "3", "игры", "работа", "универсальный"]:
        return await message.answer("Выбери 1, 2 или 3.")

    await state.update_data(usage=usage)
    await state.set_state(BuildPC.preferences)

    await message.answer(
        "✨ Есть предпочтения? Напиши или напиши 'нет'."
    )


@router.message(BuildPC.preferences)
async def finish(message: Message, state: FSMContext):
    await state.update_data(preferences=message.text)
    data = await state.get_data()

    budget = data["budget"]
    usage = data["usage"]


    await message.answer(
        f"🧩 Отлично! Вот твоя конфигурация:\n"
        f"💸 Бюджет: {budget}\n"
        f"🎯 Назначение: {usage}\n"
        f"✨ Предпочтения: {data['preferences']}\n\n"
        f"⚙ Генерирую сборку... (позже добавим логику!)"
    )
    await state.clear()

def register_build_handlers(dp):
    dp.include_router(router)


