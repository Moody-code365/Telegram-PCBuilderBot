from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from Bot.states.build_state import BuildPC

router = Router()

@router.message(Command("build"))
async def cmd_build(message: Message, state: FSMContext):
    await message.answer("💰 Введи свой бюджет ₸ :")
    await state.set_state(BuildPC.budget)

@router.message(BuildPC.budget)
async def set_budget(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("🚫 Введи число, например: 300000")

    await state.update_data(budget=int(message.text))
    await state.set_state(BuildPC.purpose)

    await message.answer(
        "🖥 Для чего нужен ПК?\n"
        "1) Игры\n"
        "2) Работа/монтаж\n"
        "3) Универсальный"
    )

@router.message(BuildPC.purpose)
async def set_purpose(message: Message, state: FSMContext):
    purpose = message.text.lower()

    if purpose not in ["1", "2", "3", "игры", "работа", "универсальный"]:
        return await message.answer("Выбери 1, 2 или 3.")

    await state.update_data(purpose=purpose)
    await state.set_state(BuildPC.form_factor)

    await message.answer(
        "📦 Какой размер корпуса хочешь?\n"
        "ATX / Micro-ATX / Mini-ITX"
    )

@router.message(BuildPC.form_factor)
async def set_case(message: Message, state: FSMContext):
    ff = message.text.lower()
    variants = ["atx", "micro-atx", "m-atx", "matx", "mini-itx", "itx"]

    if ff not in variants:
        return await message.answer("Укажи ATX, Micro-ATX или Mini-ITX")

    await state.update_data(form_factor=ff)
    await state.set_state(BuildPC.preferences)

    await message.answer("✨ Есть предпочтения? Напиши или напиши 'нет'.")

@router.message(BuildPC.preferences)
async def finish(message: Message, state: FSMContext):
    await state.update_data(preferences=message.text)
    data = await state.get_data()

    budget = data["budget"]
    purpose = data["purpose"]
    form_factor = data["form_factor"]

    await message.answer(
        f"🧩 Отлично! Вот твоя конфигурация:\n"
        f"💸 Бюджет: {budget}\n"
        f"🎯 Назначение: {purpose}\n"
        f"📦 Корпус: {form_factor}\n"
        f"✨ Предпочтения: {data['preferences']}\n\n"
        f"⚙ Генерирую сборку... (позже добавим логику!)"
    )
    await state.clear()

def register_build_handlers(dp):
    dp.include_router(router)


