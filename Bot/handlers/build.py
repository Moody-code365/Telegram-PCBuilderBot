import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from Bot.states.build_state import BuildPC
from Bot.keyboards.main_kb import main_keyboard
from Bot.keyboards.build_kb import usage_keyboard
from Bot.services.component_loader import load_components
from Bot.services.ai_pc_builder import build_pc_with_ai
from Bot.services.pc_builder import escape_md
from Bot.utils.enhanced_formatter import (
    format_enhanced_ai_build_message, 
    get_ai_welcome_message, 
    get_ai_process_messages,
    get_ai_completion_message,
    get_build_status_emoji
)
from Bot.utils.text_cleaner import normalize

from Bot.data.options import USAGE_OPTIONS

logger = logging.getLogger(__name__)


router = Router()

@router.message(F.text == "🖥 Собрать ПК")
@router.message(Command("build"))
async def cmd_build(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "💰 *Введи бюджет на сборку в тенге*\n\n"
        "Просто напиши число, например: `350000`\n\n"
        "Бот подберёт комплектующие *строго в пределах* этой суммы — "
        "итоговая сборка будет стоить ровно столько или дешевле.",
        parse_mode="Markdown",
    )
    await state.set_state(BuildPC.budget)


# ────────────────────────── БЮДЖЕТ ──────────────────────────

@router.message(BuildPC.budget)
async def set_budget(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()

    if text == "⬅️ Отмена":
        await state.clear()
        return await message.answer("🏠 Главное меню", reply_markup=main_keyboard())

    # Извлекаем цифры из текста
    digits = "".join(c for c in text if c.isdigit())

    if not digits or len(digits) < 5:
        return await message.answer(
            "⚠️ Введи сумму числом, минимум 100 000 ₸.\n"
            "Например: `400000`",
            parse_mode="Markdown",
        )

    numeric = int(digits)

    if numeric < 100_000:
        return await message.answer(
            "⚠️ Минимальный бюджет — *100 000 ₸*.\n"
            "С меньшей суммой невозможно собрать рабочий ПК.",
            parse_mode="Markdown",
        )

    if numeric > 5_000_000:
        return await message.answer(
            "⚠️ Максимальный бюджет — *5 000 000 ₸*.\n"
            "Введи реальную сумму.",
            parse_mode="Markdown",
        )

    label = f"{numeric:,} ₸".replace(",", " ")

    await state.update_data(budget=numeric, budget_label=label)
    await state.set_state(BuildPC.usage)
    await message.answer(
        f"✅ Бюджет: *{label}*\n\n"
        "Для чего нужен ПК?",
        parse_mode="Markdown",
        reply_markup=usage_keyboard(),
    )


# ────────────────────────── НАЗНАЧЕНИЕ + ПРЕДПОЧТЕНИЯ ──────────────────────────

@router.message(BuildPC.usage)
async def set_usage(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()

    if text == "⬅️ Отмена":
        await state.clear()
        return await message.answer("🏠 Главное меню", reply_markup=main_keyboard())

    cleaned = normalize(text)

    matched = None
    for key, variants in USAGE_OPTIONS.items():
        if cleaned in variants:
            matched = key
            break

    if not matched:
        return await message.answer(
            "⚠️ Выбери вариант из меню:\n"
            "🎮 Игры · 💼 Работа · 🔄 Универсальный"
        )

    await state.update_data(usage=matched)
    data = await state.get_data()
    label = data.get("budget_label", "")
    
    usage_nice = {"gaming": "🎮 Игры", "work": "💼 Работа", "universal": "🔄 Универсальный"}
    
    # Начинаем опрос предпочтений
    from Bot.states.preferences_state import PreferencesState
    from Bot.keyboards.preferences_kb import get_cpu_brand_keyboard
    
    await state.set_state(PreferencesState.choosing_cpu_brand)
    
    await message.answer(
        f"🖥️ **Какой процессор предпочитаете?**\n\n"
        f"💰 Бюджет: **{label}**\n"
        f"🎯 Назначение: **{usage_nice.get(matched, matched)}**\n\n"
        "Intel — стабильность и производительность\n"
        "AMD — отличное соотношение цена/качество",
        parse_mode="Markdown",
        reply_markup=get_cpu_brand_keyboard()
    )


# ────────────────────────── СБОРКА БЕЗ ПРЕДПОЧТЕНИЙ (СТАРЫЙ МЕТОД) ──────────────────────────
