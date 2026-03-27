from Bot.services.budget_allocator import BudgetAllocator
from Bot.services.pc_builder_pick import (
    pick_cpu, pick_case, pick_gpu, pick_ssd, pick_psu, pick_cooler, pick_ram, pick_motherboard
)
import re


def escape_md(text: str) -> str:
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)


def build_pc(budget: int, preset: str, all_parts: dict) -> dict:

    allocator = BudgetAllocator(total_budget=budget, preset=preset)
    budgets = allocator.get_budgets()

    cpu = pick_cpu(all_parts["cpu"], budgets["cpu"])
    mobo = pick_motherboard(all_parts["motherboard"], cpu, budgets["motherboard"])
    ram = pick_ram(all_parts["ram"], mobo, budgets["ram"])
    gpu = pick_gpu(all_parts["gpu"], budgets["gpu"])
    ssd = pick_ssd(all_parts["ssd"], budgets["ssd"])
    psu = pick_psu(all_parts["psu"], cpu, gpu, budgets["psu"])
    cooler = pick_cooler(all_parts["coolers"], cpu, budgets["coolers"])
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
