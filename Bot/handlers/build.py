from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from Bot.services.component_loader import load_components
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
    print("▶ STEP 1: enter set_preferences")

    if message.text == "⬅️ Назад":
        print("◀ BACK triggered")
        await state.set_state(BuildPC.usage)
        return await message.answer("🔙 Вернулся к выбору назначения", reply_markup=usage_keyboard())

    await state.update_data(preferences=message.text)
    data = await state.get_data()
    print("▶ STEP 2: data:", data)

    budget_val = data.get("budget")

    if isinstance(budget_val, str) and budget_val.isdigit():
        budget_val = int(budget_val)

    preset = data.get("usage") or "universal"
    print("▶ STEP 3: preset =", preset, "budget =", budget_val)

    # Загружаем все детали
    all_parts = load_components()
    print("▶ STEP 4: loaded parts:", {k: len(v) for k,v in all_parts.items()})

    # --- Основной вызов сборщика ---
    result = build_pc(
        budget_val,
        preset,
        all_parts
    )
    print("▶ STEP 5: build result:", result)

    message_text = format_build_message(
        result,
        budget=data.get("budget"),
        usage=data.get("usage"),
        prefs=data.get("preferences"),
    )
    print("▶ STEP 6: formatted text ok")

    await message.answer(message_text, parse_mode="Markdown", reply_markup=get_start_keyboard())
    print("▶ STEP 7: sent message")

    await state.clear()




def register_build_handlers(dp):
    dp.include_router(router)
