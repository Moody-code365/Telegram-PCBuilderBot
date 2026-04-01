"""
Обработчик опроса предпочтений пользователя.
"""

import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from Bot.states.preferences_state import PreferencesState
from Bot.states.build_state import BuildPC
from Bot.keyboards.preferences_kb import (
    get_cpu_brand_keyboard,
    get_gpu_brand_keyboard,
    get_gpu_need_keyboard,
    get_preferences_summary_keyboard
)
# from Bot.handlers.build import set_usage_with_preferences  # Убираем циклический импорт
from Bot.keyboards.main_kb import main_keyboard
from Bot.services.component_loader import load_components
from Bot.services.ai_pc_builder import build_pc_with_ai
from Bot.utils.enhanced_formatter import format_enhanced_ai_build_message

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("pref_cpu_"))
async def process_cpu_brand(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора бренда процессора."""
    cpu_brand = callback.data.replace("pref_cpu_", "")
    
    # Преобразуем в понятный формат
    brand_map = {
        "intel": "Intel",
        "amd": "AMD", 
        "any": "Любой"
    }
    
    brand_display = brand_map.get(cpu_brand, cpu_brand)
    await callback.answer(f"Выбран процессор: {brand_display}")
    
    # Сохраняем предпочтение
    await state.update_data(cpu_brand=brand_display)
    
    # Получаем данные о назначении
    data = await state.get_data()
    preset = data.get("usage", "")
    budget_label = data.get("budget_label", "")
    
    # Если рабочий ПК, спрашиваем нужна ли видеокарта
    if preset == "work":
        await state.set_state(PreferencesState.choosing_gpu_need)
        await callback.message.answer(
            "💼 **Нужна ли видеокарта для работы?**\n\n"
            "Для офисных задач, программирования, работы с документами — "
            "встроенной графики процессора достаточно.\n"
            "Для графики, дизайна, 3D моделирования — нужна дискретная видеокарта.\n\n"
            f"💰 Бюджет: **{budget_label}**",
            reply_markup=get_gpu_need_keyboard()
        )
    else:
        # Для игровых сразу спрашиваем бренд видеокарты
        await state.set_state(PreferencesState.choosing_gpu_brand)
        await callback.message.answer(
            "🎮 **Какую видеокарту предпочитаете?**\n\n"
            "NVIDIA — лучшая производительность в играх, поддержка DLSS\n"
            "AMD Radeon — отличное соотношение цена/производительность\n\n"
            f"💰 Бюджет: **{budget_label}**",
            reply_markup=get_gpu_brand_keyboard()
        )


@router.callback_query(F.data.startswith("pref_gpu_brand_"))
async def process_gpu_brand(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора бренда видеокарты."""
    gpu_brand = callback.data.replace("pref_gpu_brand_", "")
    
    # Преобразуем в понятный формат
    brand_map = {
        "nvidia": "NVIDIA",
        "radeon": "AMD Radeon",
        "any": "Любая"
    }
    
    await callback.answer(f"Выбрана видеокарта: {brand_map.get(gpu_brand, gpu_brand)}")
    
    # Сохраняем предпочтение
    await state.update_data(gpu_brand=brand_map.get(gpu_brand, ""))
    
    await show_preferences_summary(callback, state)


@router.callback_query(F.data.startswith("pref_gpu_need_"))
async def process_gpu_need(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора нужна ли видеокарта."""
    gpu_need = callback.data.replace("pref_gpu_need_", "")
    
    need_gpu = gpu_need == "yes"
    await callback.answer(f"Видеокарта {'нужна' if need_gpu else 'не нужна'}")
    
    # Сохраняем предпочтение
    await state.update_data(need_gpu=need_gpu)
    
    # Если видеокарта не нужна, сбрасываем бренд на "Любая"
    if not need_gpu:
        await state.update_data(gpu_brand="Любая")
        await show_preferences_summary(callback, state)
    else:
        # Если видеокарта нужна, спрашиваем бренд
        await state.set_state(PreferencesState.choosing_gpu_brand)
        await callback.message.answer(
            "🎮 **Какую видеокарту предпочитаете?**",
            reply_markup=get_gpu_brand_keyboard()
        )


async def show_preferences_summary(callback: CallbackQuery, state: FSMContext):
    """Показывает сводку предпочтений."""
    data = await state.get_data()
    
    cpu_brand = data.get("cpu_brand", "Любой")
    gpu_brand = data.get("gpu_brand", "Любая")
    need_gpu = data.get("need_gpu", True)
    budget_label = data.get("budget_label", "")
    usage = data.get("usage", "")
    
    usage_display = {"gaming": "🎮 Игровой ПК", "work": "💻 Рабочая станция", "universal": "⚡ Универсальный"}
    
    summary = (
        f"📋 **Ваши предпочтения для сборки:**\n\n"
        f"💰 Бюджет: **{budget_label}**\n"
        f"🎯 Назначение: **{usage_display.get(usage, usage)}**\n"
        f"🖥️ Процессор: **{cpu_brand}**\n"
    )
    
    if need_gpu is False:
        summary += f"🎮 Видеокарта: **Не нужна (встроенной хватит)**\n"
    else:
        summary += f"🎮 Видеокарта: **{gpu_brand}**\n"
    
    summary += "\n✨ **Все верно? Начинаю подбор компонентов!**"
    
    await state.set_state(PreferencesState.confirming_preferences)
    await callback.message.answer(
        summary,
        reply_markup=get_preferences_summary_keyboard()
    )


@router.callback_query(F.data == "pref_confirm")
async def confirm_preferences(callback: CallbackQuery, state: FSMContext):
    """Подтверждение предпочтений и переход к сборке."""
    await callback.answer("Предпочтения сохранены!")
    
    # Переходим к сборке
    await state.set_state(BuildPC.usage)
    
    # Получаем данные и вызываем сборку
    data = await state.get_data()
    budget = data.get("budget")
    preset = data.get("usage")
    budget_label = data.get("budget_label", str(budget))
    
    usage_nice = {"gaming": "🎮 Игры", "work": "💼 Работа", "universal": "🔄 Универсальный"}
    
    from Bot.config.ai_config import get_ai_success_message, get_ai_fallback_message
    from Bot.utils.enhanced_formatter import get_ai_process_messages
    
    await callback.message.answer(
        f"🎯 **Начинаю сборку ПК...**\n\n"
        f"💰 Бюджет: **{budget_label}**\n"
        f"🎯 Назначение: **{usage_nice.get(preset, preset)}**\n\n"
        f"🤖 *ИИ подбирает оптимальные компоненты...*"
    )
    
    # Отправляем сообщения о процессе
    process_messages = get_ai_process_messages()
    for msg in process_messages:
        await callback.message.answer(msg, parse_mode="Markdown")
    
    # Вызываем сборку с предпочтениями
    await set_usage_with_preferences(callback.message, state)


async def set_usage_with_preferences(message: Message, state: FSMContext):
    """Сборка ПК с учетом предпочтений."""
    # ── Собираем ПК ──
    try:
        # Получаем все данные включая предпочтения
        data = await state.get_data()
        budget_val = data["budget"]
        preset = data["usage"]
        
        # Формируем предпочтения для AI
        preferences = {}
        if data.get("cpu_brand") and data.get("cpu_brand") != "Любой":
            preferences["cpu_brand"] = data["cpu_brand"].upper()  # В верхний регистр для фильтрации
        if data.get("gpu_brand") and data.get("gpu_brand") != "Любая":
            # Преобразуем "AMD Radeon" в "RADEON" для фильтрации
            gpu_brand = data["gpu_brand"].upper()
            if "RADEON" in gpu_brand:
                gpu_brand = "RADEON"
            elif "NVIDIA" in gpu_brand:
                gpu_brand = "NVIDIA"
            preferences["gpu_brand"] = gpu_brand
        if data.get("need_gpu") is not None:
            preferences["need_gpu"] = data["need_gpu"]
        
        # Загружаем компоненты
        all_parts = load_components()
        
        # Вызываем AI сборку с предпочтениями
        result, used_ai, ai_explanation = build_pc_with_ai(
            budget_val, 
            preset, 
            all_parts, 
            preferences=preferences,
            enable_ai=True
        )
        
        if not result:
            await state.clear()
            return await message.answer(
                "❌ Не удалось собрать ПК. Попробуйте позже.",
                reply_markup=main_keyboard()
            )
        
        # Форматируем красивое сообщение
        formatted_message = format_enhanced_ai_build_message(
            build=result,
            budget=budget_val,
            usage=preset,
            used_ai=used_ai,
            ai_explanation=ai_explanation
        )
        
        # Отправляем результат
        await message.answer(
            formatted_message,
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )
        
        # Очищаем состояние
        await state.clear()
        
        logger.info(
            "Сборка отправлена: user=%s budget=%s preset=%s preferences=%s",
            message.from_user.id,
            budget_val,
            preset,
            preferences
        )
        
    except Exception as e:
        logger.error("Ошибка сборки: %s", e, exc_info=True)
        await state.clear()
        return await message.answer(
            "❌ Ошибка при сборке ПК. Попробуйте позже.",
            reply_markup=main_keyboard(),
        )


@router.callback_query(F.data == "pref_change")
async def change_preferences(callback: CallbackQuery, state: FSMContext):
    """Изменение предпочтений - возвращаем к началу."""
    await callback.answer("Изменяем предпочтения...")
    
    # Очищаем предпочтения но оставляем бюджет и назначение
    data = await state.get_data()
    budget = data.get("budget")
    preset = data.get("usage")
    budget_label = data.get("budget_label", str(budget))
    
    await state.clear()
    await state.update_data(budget=budget, usage=preset, budget_label=budget_label)
    
    # Начинаем опрос заново
    await state.set_state(PreferencesState.choosing_cpu_brand)
    
    await callback.message.answer(
        "🖥️ **Какой процессор предпочитаете?**\n\n"
        f"💰 Бюджет: **{budget_label}**\n"
        f"🎯 Назначение: **{preset}**",
        reply_markup=get_cpu_brand_keyboard()
    )
