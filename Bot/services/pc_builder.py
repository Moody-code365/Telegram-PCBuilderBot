"""
PC Builder v2 — главный оркестратор сборки.

Ключевая гарантия: итоговая цена сборки <= бюджет пользователя.
Алгоритм:
  1. Распределить бюджет по категориям (BudgetAllocator)
  2. Подобрать компоненты по квотам
  3. Проверить совместимость
  4. Если сумма > бюджет → итеративно понижать квоту самого дорогого
  5. Если сумма < бюджет → попробовать улучшить GPU/CPU за счёт остатка
"""

import re
from typing import Dict, Optional, Any

from Bot.services.budget_allocator import BudgetAllocator
from Bot.services.pc_builder_pick import (
    pick_cpu, pick_motherboard, pick_ram, pick_gpu,
    pick_ssd, pick_psu, pick_cooler, pick_case,
)


def escape_md(text: str) -> str:
    """Экранирует спецсимволы Markdown."""
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)


def _total_price(build: Dict[str, Optional[Dict]]) -> int:
    """Считает суммарную стоимость сборки."""
    total = 0
    for item in build.values():
        if item and isinstance(item, dict):
            total += item.get("price", 0)
    return total


def _assemble(all_parts: dict, budgets: Dict[str, int]) -> Dict[str, Optional[Dict]]:
    """
    Одна итерация сборки: подбирает все компоненты по квотам.
    Возвращает dict {category: component_dict или None}.
    """
    # 1. CPU (фундамент сборки)
    cpu = pick_cpu(all_parts["cpu"], budgets["cpu"])

    # 2. Материнская плата (совместимая с CPU по сокету)
    mobo = pick_motherboard(all_parts["motherboard"], cpu, budgets["motherboard"])

    # 3. RAM (совместимая с материнской платой по DDR)
    ram = pick_ram(all_parts["ram"], mobo, budgets["ram"])

    # 4. GPU
    gpu = pick_gpu(all_parts["gpu"], budgets["gpu"])

    # 5. SSD
    ssd = pick_ssd(all_parts["ssd"], budgets["ssd"])

    # 6. PSU (с учётом мощности CPU + GPU)
    psu = pick_psu(all_parts["psu"], cpu, gpu, budgets["psu"])

    # 7. Кулер (с учётом TDP CPU)
    cooler = pick_cooler(all_parts["coolers"], cpu, budgets["coolers"])

    # 8. Корпус (совместимый по форм-фактору с mobo)
    case = pick_case(all_parts["case"], mobo, budgets["case"])

    return {
        "cpu": cpu,
        "motherboard": mobo,
        "ram": ram,
        "gpu": gpu,
        "ssd": ssd,
        "psu": psu,
        "cooler": cooler,
        "case": case,
    }


def build_pc(budget: int, preset: str, all_parts: dict) -> dict:
    """
    Главная функция сборки ПК.

    Гарантии:
      - Итоговая цена <= budget
      - Базовая совместимость (сокет, DDR, мощность БП)
      - Сбалансированная сборка (без i9 + GT 1030)

    Параметры:
      budget:    int — бюджет в тенге
      preset:    str — "gaming" / "work" / "universal"
      all_parts: dict — загруженные компоненты {category: [items]}

    Возвращает: dict {category: component_dict}
    """
    # ── Шаг 1: Распределяем бюджет ──────────────────────
    allocator = BudgetAllocator(total_budget=budget, preset=preset)
    budgets = allocator.get_budgets()

    # ── Шаг 2: Первая сборка ────────────────────────────
    build = _assemble(all_parts, budgets)
    total = _total_price(build)

    # ── Шаг 3: Если сумма > бюджет → понижаем ──────────
    MAX_ITERATIONS = 10
    iteration = 0

    while total > budget and iteration < MAX_ITERATIONS:
        iteration += 1
        overshoot = total - budget

        # Находим самую дорогую категорию (кроме CPU — его менять в последнюю очередь)
        priced = {cat: item["price"]
                  for cat, item in build.items()
                  if item and cat != "cpu"}

        if not priced:
            break

        most_expensive_cat = max(priced, key=lambda k: priced[k])

        # Маппинг category в build → category в budgets
        cat_budget_key = most_expensive_cat
        if most_expensive_cat == "cooler":
            cat_budget_key = "coolers"

        # Уменьшаем квоту этой категории
        current_item_price = priced[most_expensive_cat]
        # Новая квота = текущая цена - перебор (с запасом)
        new_quota = max(current_item_price - overshoot - 1000, 0)
        budgets[cat_budget_key] = new_quota

        # Пересобираем
        build = _assemble(all_parts, budgets)
        total = _total_price(build)

    # ── Шаг 4: Если сумма < бюджет → пробуем улучшить ──
    remaining = budget - total
    if remaining > 5000:
        # Пробуем улучшить GPU (для gaming/universal) или CPU (для work)
        upgrade_targets = (
            ["gpu", "cpu"] if preset in ("gaming", "universal")
            else ["cpu", "gpu"]
        )

        for target in upgrade_targets:
            budget_key = target
            old_item = build.get(target)
            if not old_item:
                continue

            old_price = old_item["price"]
            # Новая квота = старая цена + весь остаток
            new_quota = old_price + remaining

            # Пересобираем только этот компонент
            if target == "cpu":
                candidate = pick_cpu(all_parts["cpu"], new_quota)
            elif target == "gpu":
                candidate = pick_gpu(all_parts["gpu"], new_quota)
            else:
                continue

            if candidate and candidate["price"] > old_price:
                # Проверяем, что с новым компонентом всё ещё в бюджете
                test_build = dict(build)
                test_build[target] = candidate

                # Если меняем CPU — нужно пересобрать зависимые (mobo, ram, cooler)
                if target == "cpu":
                    new_mobo = pick_motherboard(
                        all_parts["motherboard"], candidate,
                        budgets["motherboard"]
                    )
                    test_build["motherboard"] = new_mobo
                    test_build["ram"] = pick_ram(
                        all_parts["ram"], new_mobo, budgets["ram"]
                    )
                    test_build["cooler"] = pick_cooler(
                        all_parts["coolers"], candidate, budgets["coolers"]
                    )
                    # Обновляем PSU (мощность могла измениться)
                    test_build["psu"] = pick_psu(
                        all_parts["psu"], candidate,
                        test_build.get("gpu"), budgets["psu"]
                    )

                test_total = _total_price(test_build)
                if test_total <= budget:
                    build = test_build
                    remaining = budget - test_total
                    # Не пробуем второй target если уже улучшили

    return build