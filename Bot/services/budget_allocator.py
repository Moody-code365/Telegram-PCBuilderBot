"""
Бюджетный планировщик v3.
Гарантия: sum(квот) == total_budget.
Динамические веса в зависимости от размера бюджета.
"""

from typing import Dict

# ── Профили весов ──
PROFILES: Dict[str, Dict[str, float]] = {
    "gaming": {
        "cpu": 0.20, "gpu": 0.35, "motherboard": 0.10,
        "ram": 0.08, "ssd": 0.08, "psu": 0.06,
        "coolers": 0.05, "case": 0.08,
    },
    "work": {
        "cpu": 0.28, "gpu": 0.10, "motherboard": 0.14,
        "ram": 0.16, "ssd": 0.12, "psu": 0.07,
        "coolers": 0.05, "case": 0.08,
    },
    "universal": {
        "cpu": 0.22, "gpu": 0.28, "motherboard": 0.12,
        "ram": 0.10, "ssd": 0.09, "psu": 0.07,
        "coolers": 0.05, "case": 0.07,
    },
}

# Минимумы — ниже нельзя
MIN_ABS: Dict[str, int] = {
    "coolers": 5000,
    "psu": 15000,
    "case": 6000,
    "ssd": 12000,
    "ram": 22000,
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

        # ── Динамическая коррекция при больших бюджетах ──
        # При бюджете > 600k: увеличиваем SSD (чтобы не ставить 512GB Hiksemi на 900k сборку)
        if total > 600_000:
            weights["ssd"] += 0.03
            weights["gpu"] -= 0.015
            weights["cpu"] -= 0.015

        # При бюджете > 800k: ещё больше на GPU (чтобы влезла 5070+)
        if total > 800_000 and self.preset == "gaming":
            weights["gpu"] += 0.03
            weights["ram"] -= 0.015
            weights["motherboard"] -= 0.015

        # Нормализация
        w_sum = sum(weights.values())
        weights = {k: v / w_sum for k, v in weights.items()}

        # Первичный расчёт
        budgets = {k: int(total * w) for k, w in weights.items()}

        # Минимумы
        min_total = sum(MIN_ABS.get(k, 0) for k in budgets)
        if total >= min_total:
            for cat, minimum in MIN_ABS.items():
                if cat in budgets and budgets[cat] < minimum:
                    budgets[cat] = minimum

        # Балансировка
        self._balance(budgets, total)
        return budgets

    def _balance(self, budgets: Dict[str, int], total: int) -> None:
        current = sum(budgets.values())
        diff = current - total

        if diff == 0:
            return

        if diff > 0:
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
            if remaining > 0:
                biggest = max(budgets, key=lambda k: budgets[k])
                budgets[biggest] -= remaining
        else:
            bonus_map = {"gaming": "gpu", "work": "cpu", "universal": "gpu"}
            target = bonus_map.get(self.preset, "gpu")
            budgets[target] += abs(diff)

    def get_budgets(self) -> Dict[str, int]:
        return dict(self._budgets)