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


# ────────────────────────── НАЗНАЧЕНИЕ + СБОРКА ──────────────────────────

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

    budget_val: int = data["budget"]
    preset: str = matched
    label: str = data.get("budget_label", str(budget_val))

    usage_nice = {"gaming": "🎮 Игры", "work": "💼 Работа", "universal": "🔄 Универсальный"}

    # Уведомление о начале сборки
    await message.answer(
        f"🤖 *Анализирую ваши требования...*\n\n"
        f"💰 Бюджет: *{label}*\n"
        f"🎯 Назначение: *{usage_nice.get(preset, preset)}*\n\n"
        f"⚡ *ИИ подбирает оптимальные компоненты...*",
        parse_mode="Markdown",
    )

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

    # ── Сообщение о процессе сборки ──
    await message.answer(
        "🔍 *Анализирую совместимость компонентов...*\n\n"
        "🧠 *ИИ проверяет оптимальные конфигурации...*\n\n"
        "⚙️ *Формирую финальную сборку...*",
        parse_mode="Markdown",
    )

    # ── Собираем ПК ──
    try:
        result, used_ai, ai_explanation = build_pc_with_ai(budget_val, preset, all_parts, enable_ai=True)
    except Exception as e:
        logger.error("Ошибка сборки: %s", e, exc_info=True)
        await state.clear()
        return await message.answer(
            "❌ Не удалось подобрать сборку. Попробуй другой бюджет.",
            reply_markup=main_keyboard(),
        )

    # ── Экранируем Markdown в именах ──
    for item in result.values():
        if item and isinstance(item, dict) and "name" in item:
            item["name"] = escape_md(item["name"])

    # ── Форматируем и отправляем ──
    message_text = format_enhanced_ai_build_message(
        result,
        budget=budget_val,
        usage=preset,
        used_ai=used_ai,
        ai_explanation=ai_explanation
    )

    # ── Сообщение о завершении сборки ──
    completion_message = get_ai_completion_message(used_ai)
    await message.answer(completion_message, parse_mode="Markdown")

    await message.answer(message_text, parse_mode="Markdown", reply_markup=main_keyboard())
    logger.info("Сборка отправлена: user=%s budget=%s preset=%s", message.from_user.id, budget_val, preset)
    await state.clear()