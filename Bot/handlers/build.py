from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from Bot.states.build_state import BuildPC
from Bot.keyboards.build_kb import get_start_keyboard
from Bot.keyboards.FSM_kb import budget_keyboard, usage_keyboard, preferences_keyboard
from Bot.utils.text_cleaner import remove_emoji, normalize
from Bot.services.pc_builder import build_pc
from Bot.data.options import BUDGET_OPTIONS,USAGE_OPTIONS
from Bot.utils.formatter import format_build_message


router = Router()


# ---------------------- СТАРТ ----------------------
@router.message(F.text == "🚀 Начать подбор")
@router.message(Command("build"))
async def cmd_build(message: Message, state: FSMContext):
    await message.answer(
        "💰 Введи свой бюджет ₸ :",
        reply_markup=budget_keyboard()
    )
    await state.set_state(BuildPC.budget)



# ---------------------- БЮДЖЕТ ----------------------
@router.message(BuildPC.budget)
async def set_budget(message: Message, state: FSMContext):

    # --- Кнопка Назад ---
    if message.text == "⬅️ Назад":
        await state.clear()
        return await message.answer(
            "🔙 Возврат в главное меню",
            reply_markup=get_start_keyboard()
        )

    text = message.text.strip()

    # --- Пользователь выбрал готовый вариант ---
    if text in BUDGET_OPTIONS:
        await state.update_data(budget=text)
        await state.set_state(BuildPC.usage)
        return await message.answer(
            "🎯 Отлично! Для чего нужен ПК?",
            reply_markup=usage_keyboard()
        )

    # --- Пользователь ввел число ---
    if text.isdigit():
        await state.update_data(budget=int(text))
        await state.set_state(BuildPC.usage)
        return await message.answer(
            "🎯 Отлично! Для чего нужен ПК?",
            reply_markup=usage_keyboard()
        )

    # --- Ошибка ---
    return await message.answer(
        "🚫 Введи число (например: 300000) или выбери вариант на клавиатуре."
    )



# ---------------------- НАЗНАЧЕНИЕ ----------------------
@router.message(BuildPC.usage)
async def set_usage(message: Message, state: FSMContext):
    text = message.text

    # --- Назад ---
    if text == "⬅️ Назад":
        await state.set_state(BuildPC.budget)
        return await message.answer(
            "🔙 Вернулся к выбору бюджета",
            reply_markup=budget_keyboard()
        )

    cleaned = normalize(message.text)

    matched = None
    for key, variants in USAGE_OPTIONS.items():
        if cleaned in variants:
            matched = key
            break

    if not matched:
        return await message.answer("Выбери вариант в меню или напиши...")

    await state.update_data(usage=matched)


    await state.set_state(BuildPC.preferences)

    await message.answer(
        "✨ Есть предпочтения? Напиши или укажи кнопкой.",
        reply_markup=preferences_keyboard()
    )



# ---------------------- ПРЕДПОЧТЕНИЯ ----------------------
@router.message(BuildPC.preferences)
async def set_preferences(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.set_state(BuildPC.usage)
        return await message.answer("🔙 Вернулся к выбору назначения", reply_markup=usage_keyboard())

    await state.update_data(preferences=message.text)
    data = await state.get_data()

    # result может быть в любом формате — formatter приведёт к нужному виду
    result = build_pc(data)

    # подготовим текст (formatter сам вычислит total если нужно)
    message_text = format_build_message(
        result,
        budget=data.get("budget"),
        usage=data.get("usage"),
        prefs=data.get("preferences"),
    )

    await message.answer(message_text, parse_mode="Markdown", reply_markup=get_start_keyboard())
    await state.clear()



def register_build_handlers(dp):
    dp.include_router(router)
