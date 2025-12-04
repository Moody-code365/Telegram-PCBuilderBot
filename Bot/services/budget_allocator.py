class BudgetAllocator:
    """
    Умный динамический бюджетный планировщик.
    Возможности:
    - Учитывает тип сборки (gaming / work / universal)
    - Увеличивает бюджет под горячие и мощные CPU
    - Гарантирует минимальный уровень для БП / кулера / корпуса
    - Умно корректирует веса, чтобы CPU/GPU не съедали весь бюджет
    - Выдаёт готовые суммы по категориям
    """

    def __init__(self, total_budget: int, preset: str = "universal", cpu_tdp: int | None = None):
        self.total_budget = total_budget
        self.preset = preset
        self.cpu_tdp = cpu_tdp
        self.budgets = self._allocate_budgets()

    # -------------------------------------------------------------------------
    # ГЛАВНАЯ ФУНКЦИЯ РАСПРЕДЕЛЕНИЯ
    # -------------------------------------------------------------------------
    def _allocate_budgets(self) -> dict:
        total = self.total_budget

        # -----------------------------------------------------------
        # 1. БАЗОВЫЕ ВЕСА
        # -----------------------------------------------------------
        if self.preset == "gaming":
            weights = {
                "cpu": 0.18,
                "gpu": 0.42,
                "motherboard": 0.12,
                "ram": 0.10,
                "ssd": 0.08,
                "psu": 0.07,
                "coolers": 0.02,
                "case": 0.01,
            }

        elif self.preset == "work":
            weights = {
                "cpu": 0.32,
                "gpu": 0.12,
                "motherboard": 0.15,
                "ram": 0.18,
                "ssd": 0.10,
                "psu": 0.06,
                "coolers": 0.04,
                "case": 0.03,
            }

        else:  # universal
            weights = {
                "cpu": 0.24,
                "gpu": 0.32,
                "motherboard": 0.14,
                "ram": 0.12,
                "ssd": 0.10,
                "psu": 0.06,
                "coolers": 0.02,
                "case": 0.02,
            }

        # -----------------------------------------------------------
        # 2. МИНИМАЛЬНЫЕ ПОРОГИ ДЛЯ БП / КУЛЕРА / КОРПУСА
        # -----------------------------------------------------------
        min_limits = {
            "coolers": 20000 if total > 200000 else 12000,
            "psu": 25000 if total > 250000 else 15000,
            "case": 15000,
        }

        # -----------------------------------------------------------
        # 3. ДОП. БЮДЖЕТ ПОД ГОРЯЧИЙ CPU
        # -----------------------------------------------------------
        if self.cpu_tdp:

            # умеренно горячий
            if self.cpu_tdp >= 140:
                weights["coolers"] += 0.01

            # i7 / Ryzen 7 — высокое тепловыделение
            if self.cpu_tdp >= 160:
                weights["coolers"] += 0.02
                weights["psu"] += 0.01

            # i9 / R9 / X3D — экстремально горячий
            if self.cpu_tdp >= 200:
                weights["coolers"] += 0.03
                weights["psu"] += 0.02
                weights["motherboard"] += 0.01

        # -----------------------------------------------------------
        # 4. НОРМАЛИЗАЦИЯ ВЕСОВ (на всякий случай)
        # -----------------------------------------------------------
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}

        # -----------------------------------------------------------
        # 5. ПЕРЕВОД В СУММЫ
        # -----------------------------------------------------------
        budgets = {name: int(total * w) for name, w in weights.items()}

        # -----------------------------------------------------------
        # 6. ПРИМЕНЯЕМ МИНИМАЛЬНЫЕ ПОРЯДКИ
        # -----------------------------------------------------------
        for key, minimum in min_limits.items():
            budgets[key] = max(budgets[key], minimum)

        # -----------------------------------------------------------
        # 7. ОГРАНИЧИВАЕМ GPU И CPU, ЕСЛИ ОНИ СЛИШКОМ БОЛЬШИЕ
        # -----------------------------------------------------------

        # GPU не должен съедать > 40% бюджета
        if budgets["gpu"] > total * 0.40:
            diff = budgets["gpu"] - int(total * 0.40)
            budgets["gpu"] -= diff
            # перераспределяем избыток на полезные категории
            budgets["psu"] += diff // 3
            budgets["coolers"] += diff // 4
            budgets["motherboard"] += diff // 4

        # CPU не должен занимать > 28–30%
        if budgets["cpu"] > total * 0.30:
            diff = budgets["cpu"] - int(total * 0.28)
            budgets["cpu"] -= diff
            budgets["coolers"] += diff // 2
            budgets["psu"] += diff // 2

        return budgets

    # -------------------------------------------------------------------------
    def get_budgets(self) -> dict:
        """Возвращает итоговое распределение бюджета по категориям."""
        return self.budgets
