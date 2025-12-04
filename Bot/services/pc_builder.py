from Bot.services.budget_allocator import BudgetAllocator
from Bot.services.pc_builder_pick import pick_cpu, pick_case, pick_gpu, pick_ssd, pick_psu, pick_cooler, pick_ram,pick_motherboard


def build_pc(budget: int, preset: str, all_parts: dict) -> dict:
    """
    Главная функция сборки ПК.

    all_parts = {
        "cpus": [...],
        "mobos": [...],
        "rams": [...],
        "gpus": [...],
        "ssds": [...],
        "psus": [...],
        "coolers": [...],
        "cases": [...],
    }
    """

    # 1) Создаём аллокатор
    allocator = BudgetAllocator(total_budget=budget, preset=preset)
    budgets = allocator.get_budgets()

    # 2) Выбор CPU
    cpu = pick_cpu(all_parts["cpu"], budgets["cpu"])

    # 3) Выбор материнской платы
    mobo = pick_motherboard(all_parts["motherboard"], cpu, budgets["motherboard"])

    # 4) RAM
    ram = pick_ram(all_parts["ram"], mobo, budgets["ram"])

    # 5) GPU
    gpu = pick_gpu(all_parts["gpu"], budgets["gpu"])

    # 6) SSD
    ssd = pick_ssd(all_parts["ssd"], budgets["ssd"])

    # 7) БП
    psu = pick_psu(all_parts["psu"], cpu, gpu, budgets["psu"])

    # 8) Кулер
    cooler = pick_cooler(all_parts["coolers"], cpu, budgets["coolers"])

    # 9) Корпус
    case = pick_case(all_parts["case"], mobo, budgets["case"])

    # ====== Возвращаем всю сборку ======
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
