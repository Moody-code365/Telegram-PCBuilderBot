"""
PC Builder Pick v3 — строгий подбор с учётом ранга GPU-серий.
"""

from typing import List, Dict, Optional
import re


# ══════════════════════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════════════════

def _get(component: Optional[Dict], *keys, default=None):
    if component is None:
        return default
    cur = component
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k)
        else:
            return default
        if cur is None:
            return default
    return cur


def _in_budget(items: List[Dict], budget: int) -> List[Dict]:
    return [i for i in items if i["price"] <= budget]


def _cheapest(items: List[Dict]) -> Optional[Dict]:
    if not items:
        return None
    return min(items, key=lambda x: x["price"])


# ══════════════════════════════════════════════════════════
#  РАНГ GPU ПО МОДЕЛИ (чем выше — тем мощнее)
# ══════════════════════════════════════════════════════════

# Таблица рангов GPU: ключ — модель (lowercase без пробелов), значение — ранг
_GPU_RANK_TABLE: dict[str, int] = {
    # NVIDIA — старые
    "gt210": 1, "gt710": 2, "gt730": 3, "gt740": 4,
    "gt1030": 5, "gtx1050": 10, "gtx1050ti": 12,
    "gtx1660": 18, "gtx1660super": 20,
    "rtx3050": 22, "rtx3060": 28, "rtx3070": 32, "rtx3070ti": 34,
    # NVIDIA — новые
    "rtx5050": 35, "rtx5060": 42, "rtx5060ti": 50,
    "rtx5070": 60, "rtx5070ti": 68, "rtx5080": 78, "rtx5090": 90,
    # AMD
    "rx580": 15, "rx6500": 13, "rx6500xt": 14,
    "rx7600": 30, "rx9060xt": 45,
    "rx9070": 55, "rx9070xt": 62,
    # Intel
    "arcb570": 29,
}


def _gpu_model_rank(gpu: Dict) -> int:
    """Извлекает ранг GPU из названия."""
    name = gpu.get("name", "").lower()

    # Пробуем найти серию вида RTX 5070 Ti, RX 9060 XT и т.д.
    # Сначала ищем с суффиксом Ti/XT
    m = re.search(r"(rtx|gtx|rx|gt|arc\s*b)\s*(\d{3,4})\s*(ti|xt|super)?", name)
    if m:
        prefix = m.group(1).replace(" ", "")
        number = m.group(2)
        suffix = m.group(3) or ""
        key = f"{prefix}{number}{suffix}"
        rank = _GPU_RANK_TABLE.get(key, 0)
        if rank > 0:
            return rank
        # Попробуем без суффикса
        rank = _GPU_RANK_TABLE.get(f"{prefix}{number}", 0)
        if rank > 0:
            # Если был суффикс — добавляем небольшой бонус
            if suffix:
                return rank + 3
            return rank

    return 0


# ══════════════════════════════════════════════════════════
#  CPU
# ══════════════════════════════════════════════════════════

def pick_cpu(cpus: List[Dict], budget: int) -> Optional[Dict]:
    if not cpus:
        return None

    candidates = _in_budget(cpus, budget)
    if not candidates:
        return _cheapest(cpus)

    def score(cpu: Dict) -> tuple:
        specs = cpu.get("specs") or {}
        cores = specs.get("cores", 0)
        threads = specs.get("threads", 0)
        tdp = specs.get("tdp", 0)
        usage = cpu["price"] / budget if budget > 0 else 0
        price_score = -abs(0.9 - usage)
        return (cores, threads, tdp, price_score)

    candidates.sort(key=score, reverse=True)
    return candidates[0]


# ══════════════════════════════════════════════════════════
#  MOTHERBOARD
# ══════════════════════════════════════════════════════════

def pick_motherboard(mobos: List[Dict], cpu: Optional[Dict], budget: int) -> Optional[Dict]:
    if not mobos:
        return None

    cpu_socket = _get(cpu, "specs", "socket")

    socket_ok = ([m for m in mobos if _get(m, "specs", "socket") == cpu_socket]
                 if cpu_socket else list(mobos))

    in_budget = _in_budget(socket_ok, budget)

    if not in_budget:
        return _cheapest(socket_ok) if socket_ok else _cheapest(mobos)

    def score(m: Dict) -> tuple:
        specs = m.get("specs") or {}
        ff = (specs.get("formfactor") or specs.get("form_factor") or "").lower()
        ff_rank = {"atx": 3, "matx": 2, "m-atx": 2, "itx": 1}.get(ff, 0)
        ddr_rank = 2 if specs.get("ram_type") == "DDR5" else 1
        usage = m["price"] / budget if budget > 0 else 0
        return (ff_rank, ddr_rank, -abs(0.75 - usage))

    in_budget.sort(key=score, reverse=True)
    return in_budget[0]


# ══════════════════════════════════════════════════════════
#  RAM
# ══════════════════════════════════════════════════════════

def pick_ram(rams: List[Dict], mobo: Optional[Dict], budget: int) -> Optional[Dict]:
    if not rams:
        return None

    mobo_ddr = _get(mobo, "specs", "ram_type")
    compat = ([r for r in rams if _get(r, "specs", "ddr") == mobo_ddr]
              if mobo_ddr else list(rams))

    in_budget = _in_budget(compat, budget)

    if not in_budget:
        return _cheapest(compat) if compat else _cheapest(rams)

    def score(r: Dict) -> tuple:
        specs = r.get("specs") or {}
        return (specs.get("capacity_gb", 0), specs.get("mhz", 0), -r["price"])

    in_budget.sort(key=score, reverse=True)
    return in_budget[0]


# ══════════════════════════════════════════════════════════
#  GPU — с рангом серии
# ══════════════════════════════════════════════════════════

def pick_gpu(gpus: List[Dict], budget: int) -> Optional[Dict]:
    """
    Выбирает GPU:
      1. В бюджете
      2. Приоритет: ранг модели > VRAM > GDDR > цена
    """
    if not gpus:
        return None

    candidates = _in_budget(gpus, budget)
    if not candidates:
        return _cheapest(gpus)

    def score(g: Dict) -> tuple:
        specs = g.get("specs") or {}
        rank = _gpu_model_rank(g)
        vram = specs.get("vram_gb", 0)
        gddr = specs.get("gddr", 0)
        return (rank, vram, gddr, -g["price"])

    candidates.sort(key=score, reverse=True)
    return candidates[0]


# ══════════════════════════════════════════════════════════
#  SSD
# ══════════════════════════════════════════════════════════

def pick_ssd(ssds: List[Dict], budget: int) -> Optional[Dict]:
    if not ssds:
        return None

    candidates = _in_budget(ssds, budget)
    if not candidates:
        return _cheapest(ssds)

    def iface_rank(s: Dict) -> int:
        iface = (_get(s, "specs", "interface") or "").lower()
        return 2 if ("nvme" in iface or "pcie" in iface) else 1

    def score(s: Dict) -> tuple:
        cap = _get(s, "specs", "capacity_gb", default=0)
        return (iface_rank(s), cap, -s["price"])

    candidates.sort(key=score, reverse=True)
    return candidates[0]


# ══════════════════════════════════════════════════════════
#  PSU
# ══════════════════════════════════════════════════════════

def estimate_system_power(cpu: Optional[Dict], gpu: Optional[Dict]) -> int:
    cpu_tdp = _get(cpu, "specs", "tdp", default=65)

    gpu_vram = _get(gpu, "specs", "vram_gb", default=0)
    gpu_rank = _gpu_model_rank(gpu) if gpu else 0

    # Мощность GPU по рангу (точнее чем по VRAM)
    if gpu_rank >= 78:      gpu_power = 350  # 5080+
    elif gpu_rank >= 60:    gpu_power = 280  # 5070+
    elif gpu_rank >= 50:    gpu_power = 220  # 5060 Ti
    elif gpu_rank >= 35:    gpu_power = 180  # 5050-5060
    elif gpu_rank >= 20:    gpu_power = 150  # GTX 1660 / RTX 3050
    elif gpu_rank >= 10:    gpu_power = 100  # GTX 1050
    elif gpu_vram > 0:      gpu_power = 50
    else:                   gpu_power = 0

    raw = cpu_tdp + gpu_power + 100
    recommended = int(raw * 1.25)
    recommended = ((recommended + 49) // 50) * 50
    return max(recommended, 400)


def pick_psu(psus: List[Dict], cpu: Optional[Dict], gpu: Optional[Dict], budget: int) -> Optional[Dict]:
    if not psus:
        return None

    required = estimate_system_power(cpu, gpu)

    def get_watt(p: Dict) -> int:
        return _get(p, "specs", "watt", default=0)

    def cert(p: Dict) -> int:
        n = p.get("name", "").lower()
        if "titanium" in n: return 5
        if "platinum" in n: return 4
        if "gold" in n: return 3
        if "silver" in n: return 2
        if "bronze" in n: return 1
        return 0

    good = [p for p in psus if get_watt(p) >= required and p["price"] <= budget]

    if not good:
        enough = [p for p in psus if get_watt(p) >= required]
        if enough:
            return _cheapest(enough)
        return max(psus, key=lambda p: get_watt(p)) if psus else None

    good.sort(key=lambda p: (cert(p), get_watt(p)), reverse=True)
    best = cert(good[0])
    top = [p for p in good if cert(p) >= best - 1]
    return min(top, key=lambda p: p["price"])


# ══════════════════════════════════════════════════════════
#  COOLER
# ══════════════════════════════════════════════════════════

def pick_cooler(coolers: List[Dict], cpu: Optional[Dict], budget: int) -> Optional[Dict]:
    if not coolers:
        return None
    if not cpu:
        return _cheapest(_in_budget(coolers, budget)) or _cheapest(coolers)

    cpu_tdp = _get(cpu, "specs", "tdp", default=65)
    required = int(cpu_tdp * 1.15)

    def is_water(c: Dict) -> bool:
        if _get(c, "specs", "water", default=False):
            return True
        n = c.get("name", "").lower()
        return "water" in n or "liquid" in n or "aio" in n

    def tdp(c: Dict) -> int:
        return _get(c, "specs", "tdp", default=0)

    # Водянка при TDP > 200
    if required > 200:
        water = [c for c in coolers if is_water(c) and tdp(c) >= required and c["price"] <= budget]
        if water:
            return min(water, key=lambda c: c["price"])
        water_any = [c for c in coolers if is_water(c) and c["price"] <= budget]
        if water_any:
            return max(water_any, key=lambda c: tdp(c))

    air = [c for c in coolers if not is_water(c) and tdp(c) >= required and c["price"] <= budget]
    if air:
        return min(air, key=lambda c: c["price"])

    air_any = [c for c in coolers if not is_water(c) and c["price"] <= budget]
    if air_any:
        return max(air_any, key=lambda c: tdp(c))

    return _cheapest(coolers)


# ══════════════════════════════════════════════════════════
#  CASE
# ══════════════════════════════════════════════════════════

def pick_case(cases: List[Dict], mobo: Optional[Dict], budget: int) -> Optional[Dict]:
    if not cases:
        return None

    mobo_ff = (_get(mobo, "specs", "formfactor") or _get(mobo, "specs", "form_factor") or "").lower()

    FF_COMPAT = {
        "atx": {"atx", "matx", "m-atx", "itx"},
        "matx": {"matx", "m-atx", "itx"},
        "m-atx": {"matx", "m-atx", "itx"},
        "itx": {"itx"},
    }

    def compat(c: Dict) -> bool:
        ff = (_get(c, "specs", "form_factor") or _get(c, "specs", "formfactor") or "").lower()
        if not mobo_ff or not ff:
            return True
        return mobo_ff in FF_COMPAT.get(ff, set())

    filtered = [c for c in cases
                if c["price"] <= budget
                and not (c.get("specs") or {}).get("psu_watts")
                and compat(c)]

    if not filtered:
        relaxed = [c for c in cases
                   if c["price"] <= budget
                   and not (c.get("specs") or {}).get("psu_watts")]
        return _cheapest(relaxed) if relaxed else _cheapest(cases)

    target = budget * 0.6

    def score(c: Dict) -> tuple:
        fans = 1 if (c.get("specs") or {}).get("fans_count", 0) > 0 else 0
        return (fans, -abs(c["price"] - target))

    filtered.sort(key=score, reverse=True)
    return filtered[0]