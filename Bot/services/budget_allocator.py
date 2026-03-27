"""
Бюджетный планировщик v2.
Гарантия: sum(квот) == total_budget (ни тенге больше).
"""

from typing import Dict

# ── Профили весов (сумма = 1.0) ──────────────────────────
PROFILES: Dict[str, Dict[str, float]] = {
    "gaming": {
        "cpu": 0.18, "gpu": 0.35, "motherboard": 0.12,
        "ram": 0.10, "ssd": 0.08, "psu": 0.07,
        "coolers": 0.05, "case": 0.05,
    },
    "work": {
        "cpu": 0.28, "gpu": 0.10, "motherboard": 0.15,
        "ram": 0.18, "ssd": 0.12, "psu": 0.07,
        "coolers": 0.05, "case": 0.05,
    },
    "universal": {
        "cpu": 0.22, "gpu": 0.28, "motherboard": 0.13,
        "ram": 0.11, "ssd": 0.09, "psu": 0.07,
        "coolers": 0.05, "case": 0.05,
    },
}

# Абсолютные минимумы (₸) — ниже нельзя, иначе компонент будет мусорный
MIN_ABS: Dict[str, int] = {
    "coolers": 4000,
    "psu": 13000,
    "case": 5000,
    "ssd": 8000,
    "ram": 20000,
}


class BudgetAllocator:

    def __init__(self, total_budget: int, preset: str = "universal"):
        self.total_budget = max(total_budget, 0)
        self.preset = preset if preset in PROFILES else "universal"
        self._budgets = self._allocate()

    def _allocate(self) -> Dict[str, int]:
        total = self.total_budget
        if total <= 0:
            return {k: 0 for k in PROFILES[self.preset]}

        weights = dict(PROFILES[self.preset])
        w_sum = sum(weights.values())
        weights = {k: v / w_sum for k, v in weights.items()}

        # Первичный расчёт
        budgets = {k: int(total * w) for k, w in weights.items()}

        # Применяем минимумы (но только если total позволяет)
        min_total_needed = sum(MIN_ABS.get(k, 0) for k in budgets)
        if total >= min_total_needed:
            for cat, minimum in MIN_ABS.items():
                if cat in budgets and budgets[cat] < minimum:
                    budgets[cat] = minimum

        # Балансировка
        self._balance_to_total(budgets, total)
        return budgets

    def _balance_to_total(self, budgets: Dict[str, int], total: int) -> None:
        """Корректирует budgets in-place так, что sum == total."""
        current = sum(budgets.values())
        diff = current - total

        if diff == 0:
            return

        if diff > 0:
            # Перебор — нужно урезать
            # Сортируем по убыванию размера квоты, режем сверху
            ordered = sorted(budgets.keys(), key=lambda k: -budgets[k])
            remaining = diff
            for k in ordered:
                if remaining <= 0:
                    break
                floor = MIN_ABS.get(k, 0)
                can_cut = max(0, budgets[k] - floor)
                cut = min(can_cut, remaining)
                budgets[k] -= cut
                remaining -= cut
            # Если из-за минимумов всё ещё перебор — режем принудительно
            if remaining > 0:
                biggest = max(budgets, key=lambda k: budgets[k])
                budgets[biggest] -= remaining
        else:
            # Недобор — добавляем остаток к главной категории
            bonus_map = {"gaming": "gpu", "work": "cpu", "universal": "gpu"}
            target = bonus_map.get(self.preset, "gpu")
            budgets[target] += abs(diff)

    def get_budgets(self) -> Dict[str, int]:
        return dict(self._budgets)