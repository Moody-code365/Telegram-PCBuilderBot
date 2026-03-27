import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from Bot.states.build_state import BuildPC
from Bot.keyboards.main_kb import main_keyboard
from Bot.keyboards.build_kb import budget_keyboard, usage_keyboard, preferences_keyboard
from Bot.services.component_loader import load_components
from Bot.services.pc_builder import build_pc, escape_md
from Bot.utils.formatter import format_build_message
from Bot.utils.text_cleaner import normalize
from Bot.data.options import BUDGET_OPTIONS, USAGE_OPTIONS

logger = logging.getLogger(__name__)

router = Router()

# ── Маппинг кнопок бюджета → число (верхняя граница) ────
BUDGET_MAP: dict[str, int] = {
    "💰 до 150 000 ₸":    150_000,
    "💰 150–250 000 ₸":   250_000,
    "💰 250–400 000 ₸":   400_000,
    "💰 400–600 000 ₸":   600_000,
    "💰 600–900 000 ₸":   900_000,
    "💰 900 000 ₸+":      1_200_000,
}


# ────────────────────────── СТАРТ СБОРКИ ──────────────────────────

@router.message(F.text == "🖥 Собрать ПК")
@router.message(Command("build"))
async def cmd_build(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "💰 Укажи бюджет на сборку (₸):\n\n"
        "Выбери вариант или введи число вручную.",
        reply_markup=budget_keyboard(),
    )
    await state.set_state(BuildPC.budget)


# ────────────────────────── БЮДЖЕТ ──────────────────────────

@router.message(BuildPC.budget)
async def set_budget(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()

    # Кнопка «Назад»
    if text == "⬅️ Назад":
        await state.clear()
        return await message.answer("🔙 Главное меню", reply_markup=main_keyboard())

    # Пользователь выбрал готовый вариант
    if text in BUDGET_MAP:
        numeric = BUDGET_MAP[text]
        await state.update_data(budget=numeric, budget_label=text)
        await state.set_state(BuildPC.usage)
        return await message.answer(
            "🎯 Для чего нужен ПК?",
            reply_markup=usage_keyboard(),
        )

    # Пользователь также мог нажать старые кнопки из BUDGET_OPTIONS
    if text in BUDGET_OPTIONS:
        # Пытаемся найти в BUDGET_MAP по частичному совпадению
        numeric = 300_000  # fallback
        for key, val in BUDGET_MAP.items():
            if any(part in key for part in text.split()):
                numeric = val
                break
        await state.update_data(budget=numeric, budget_label=text)
        await state.set_state(BuildPC.usage)
        return await message.answer(
            "🎯 Для чего нужен ПК?",
            reply_markup=usage_keyboard(),
        )

    # Пользователь ввёл число
    digits = "".join(c for c in text if c.isdigit())
    if digits and len(digits) >= 4:
        numeric = int(digits)
        label = f"{numeric:,} ₸".replace(",", " ")
        await state.update_data(budget=numeric, budget_label=label)
        await state.set_state(BuildPC.usage)
        return await message.answer(
            "🎯 Для чего нужен ПК?",
            reply_markup=usage_keyboard(),
        )

    return await message.answer(
        "⚠️ Введи число (например: 300000) или выбери вариант на клавиатуре."
    )


# ────────────────────────── НАЗНАЧЕНИЕ ──────────────────────────

@router.message(BuildPC.usage)
async def set_usage(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()

    if text == "⬅️ Назад":
        await state.set_state(BuildPC.budget)
        return await message.answer("🔙 Выбери бюджет:", reply_markup=budget_keyboard())

    cleaned = normalize(text)

    matched = None
    for key, variants in USAGE_OPTIONS.items():
        if cleaned in variants:
            matched = key
            break

    if not matched:
        return await message.answer("⚠️ Выбери вариант из меню или напиши: игры / работа / универсальный")

    await state.update_data(usage=matched)
    await state.set_state(BuildPC.preferences)
    await message.answer(
        "✨ Есть предпочтения?\n"
        "Выбери или напиши своё.",
        reply_markup=preferences_keyboard(),
    )


# ────────────────────────── ПРЕДПОЧТЕНИЯ + СБОРКА ──────────────────────────

@router.message(BuildPC.preferences)
async def set_preferences(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()

    if text == "⬅️ Назад":
        await state.set_state(BuildPC.usage)
        return await message.answer("🔙 Выбери назначение:", reply_markup=usage_keyboard())

    await state.update_data(preferences=text)
    data = await state.get_data()

    # ── Парсим бюджет (гарантируем int) ──
    budget_val = data.get("budget", 300_000)
    if isinstance(budget_val, str):
        digits = "".join(c for c in budget_val if c.isdigit())
        budget_val = int(digits) if digits else 300_000
    budget_val = int(budget_val)

    preset = data.get("usage") or "universal"

    logger.info("Сборка: budget=%s, preset=%s, prefs=%s", budget_val, preset, text)

    # ── Загружаем компоненты ──
    try:
        all_parts = load_components()
    except Exception as e:
        logger.error("Ошибка загрузки компонентов: %s", e)
        await state.clear()
        return await message.answer(
            "❌ Ошибка загрузки данных. Попробуй позже.",
            reply_markup=main_keyboard(),
        )

    # ── Собираем ПК ──
    try:
        result = build_pc(budget_val, preset, all_parts)
    except Exception as e:
        logger.error("Ошибка сборки: %s", e)
        await state.clear()
        return await message.answer(
            "❌ Ошибка при подборе. Попробуй другой бюджет.",
            reply_markup=main_keyboard(),
        )

    # ── Экранируем Markdown в именах ──
    for cat, item in result.items():
        if item and isinstance(item, dict) and "name" in item:
            item["name"] = escape_md(item["name"])

    # ── Форматируем и отправляем ──
    message_text = format_build_message(
        result,
        budget=data.get("budget_label", budget_val),
        usage=data.get("usage"),
        prefs=data.get("preferences"),
    )

    await message.answer(message_text, parse_mode="Markdown", reply_markup=main_keyboard())
    logger.info("Сборка отправлена пользователю %s", message.from_user.id)
    await state.clear()