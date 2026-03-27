"""
PC Builder Pick v2 — строгий подбор компонентов.

Ключевые принципы:
1. Каждая pick_* функция СТРОГО укладывается в переданный бюджет.
   Fallback на самый дешёвый компонент (а не самый дорогой).
2. Совместимость: сокет CPU↔Mobo, DDR-тип Mobo↔RAM, мощность PSU.
3. Баллы качества (score) — чем дороже/лучше в рамках бюджета, тем лучше.
"""

from typing import List, Dict, Optional, Any


# ══════════════════════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════════════════

def _get(component: Optional[Dict], *keys, default=None):
    """Безопасное извлечение из вложенных dict."""
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
    """Фильтрует только компоненты с ценой <= budget."""
    return [i for i in items if i["price"] <= budget]


def _cheapest(items: List[Dict]) -> Optional[Dict]:
    """Возвращает самый дешёвый компонент (или None)."""
    if not items:
        return None
    return min(items, key=lambda x: x["price"])


# ══════════════════════════════════════════════════════════
#  CPU
# ══════════════════════════════════════════════════════════

def pick_cpu(cpus: List[Dict], budget: int) -> Optional[Dict]:
    """
    Выбирает лучший CPU в рамках бюджета.
    Критерии (по убыванию приоритета):
      1. Больше ядер
      2. Больше потоков
      3. Цена ближе к 80-90% бюджета (используем бюджет по максимуму)
    Fallback: самый дешёвый CPU из всего списка.
    """
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
        price = cpu["price"]
        # Ценовая эффективность: предпочитаем тратить 80-95% квоты
        usage_ratio = price / budget if budget > 0 else 0
        # Бонус за использование бюджета (ближе к 0.9 — лучше)
        price_score = -abs(0.9 - usage_ratio)
        return (cores, threads, tdp, price_score)

    candidates.sort(key=score, reverse=True)
    return candidates[0]


# ══════════════════════════════════════════════════════════
#  MOTHERBOARD
# ══════════════════════════════════════════════════════════

def pick_motherboard(
    mobos: List[Dict],
    cpu: Optional[Dict],
    budget: int
) -> Optional[Dict]:
    """
    Выбирает материнскую плату:
      1. Совместимую по сокету с CPU
      2. В рамках бюджета
      3. Предпочитает ATX > mATX > ITX
      4. Предпочитает DDR5 > DDR4 (при прочих равных)
    """
    if not mobos:
        return None

    cpu_socket = _get(cpu, "specs", "socket")

    # Шаг 1: фильтр по сокету
    if cpu_socket:
        socket_ok = [m for m in mobos
                     if _get(m, "specs", "socket") == cpu_socket]
    else:
        socket_ok = list(mobos)

    # Шаг 2: фильтр по бюджету
    in_budget = _in_budget(socket_ok, budget)

    # Шаг 3: fallback — если ничего не нашлось в бюджете,
    #         берём самую дешёвую совместимую по сокету
    if not in_budget:
        if socket_ok:
            return _cheapest(socket_ok)
        return _cheapest(mobos)

    # Шаг 4: скоринг
    def score(m: Dict) -> tuple:
        specs = m.get("specs") or {}
        ff = (specs.get("formfactor") or specs.get("form_factor") or "").lower()
        ff_rank = {"atx": 3, "matx": 2, "m-atx": 2, "itx": 1}.get(ff, 0)
        ram_type = specs.get("ram_type", "")
        ddr_rank = 2 if ram_type == "DDR5" else 1 if ram_type == "DDR4" else 0
        # Предпочитаем использовать 60-85% квоты
        usage = m["price"] / budget if budget > 0 else 0
        usage_score = -abs(0.75 - usage)
        return (ff_rank, ddr_rank, usage_score)

    in_budget.sort(key=score, reverse=True)
    return in_budget[0]


# ══════════════════════════════════════════════════════════
#  RAM
# ══════════════════════════════════════════════════════════

def pick_ram(
    rams: List[Dict],
    mobo: Optional[Dict],
    budget: int
) -> Optional[Dict]:
    """
    Выбирает оперативную память:
      1. Совместимую по DDR-типу с материнской платой
      2. В рамках бюджета
      3. Максимум объёма, затем максимум MHz
    """
    if not rams:
        return None

    mobo_ddr = _get(mobo, "specs", "ram_type")  # "DDR4" / "DDR5" / None

    # Фильтр совместимости + бюджет
    if mobo_ddr:
        compat = [r for r in rams
                  if _get(r, "specs", "ddr") == mobo_ddr]
    else:
        compat = list(rams)

    in_budget = _in_budget(compat, budget)

    if not in_budget:
        # Fallback: самая дешёвая совместимая
        if compat:
            return _cheapest(compat)
        return _cheapest(rams)

    def score(r: Dict) -> tuple:
        specs = r.get("specs") or {}
        cap = specs.get("capacity_gb", 0)
        mhz = specs.get("mhz", 0)
        # Предпочитаем >= 16 GB, но не переплачиваем
        return (cap, mhz, -r["price"])

    in_budget.sort(key=score, reverse=True)
    return in_budget[0]


# ══════════════════════════════════════════════════════════
#  GPU
# ══════════════════════════════════════════════════════════

def pick_gpu(gpus: List[Dict], budget: int) -> Optional[Dict]:
    """
    Выбирает видеокарту:
      1. В рамках бюджета
      2. Максимум VRAM, затем GDDR-поколение
      3. При равных — дешевле
    Fallback: самая дешёвая GPU.
    """
    if not gpus:
        return None

    candidates = _in_budget(gpus, budget)
    if not candidates:
        return _cheapest(gpus)

    def score(g: Dict) -> tuple:
        specs = g.get("specs") or {}
        vram = specs.get("vram_gb", 0)
        gddr = specs.get("gddr", 0)
        return (vram, gddr, -g["price"])

    candidates.sort(key=score, reverse=True)
    return candidates[0]


# ══════════════════════════════════════════════════════════
#  SSD
# ══════════════════════════════════════════════════════════

def pick_ssd(ssds: List[Dict], budget: int) -> Optional[Dict]:
    """
    Выбирает SSD:
      1. В рамках бюджета
      2. NVMe > SATA
      3. Максимум объёма
    """
    if not ssds:
        return None

    candidates = _in_budget(ssds, budget)
    if not candidates:
        return _cheapest(ssds)

    def iface_rank(s: Dict) -> int:
        iface = (_get(s, "specs", "interface") or "").lower()
        if "nvme" in iface or "pcie" in iface:
            return 2
        return 1  # SATA и прочие

    def score(s: Dict) -> tuple:
        cap = _get(s, "specs", "capacity_gb", default=0)
        return (iface_rank(s), cap, -s["price"])

    candidates.sort(key=score, reverse=True)
    return candidates[0]


# ══════════════════════════════════════════════════════════
#  PSU
# ══════════════════════════════════════════════════════════

def estimate_system_power(cpu: Optional[Dict], gpu: Optional[Dict]) -> int:
    """Оценивает необходимую мощность БП (в ваттах)."""
    cpu_tdp = _get(cpu, "specs", "tdp", default=65)

    # GPU TDP оценка по VRAM
    gpu_vram = _get(gpu, "specs", "vram_gb", default=0)
    if gpu_vram <= 0:
        gpu_power = 0
    elif gpu_vram <= 2:
        gpu_power = 50
    elif gpu_vram <= 4:
        gpu_power = 100
    elif gpu_vram <= 8:
        gpu_power = 180
    elif gpu_vram <= 12:
        gpu_power = 220
    elif gpu_vram <= 16:
        gpu_power = 280
    else:
        gpu_power = 350

    # Всё остальное (RAM, SSD, вентиляторы, потери) ~80-120W
    overhead = 100

    # Рекомендуемая мощность = (нагрузка) * 1.25 (25% запас)
    raw = cpu_tdp + gpu_power + overhead
    recommended = int(raw * 1.25)

    # Округляем вверх до ближайших 50W
    recommended = ((recommended + 49) // 50) * 50
    return max(recommended, 400)  # минимум 400W для любой сборки


def pick_psu(
    psus: List[Dict],
    cpu: Optional[Dict],
    gpu: Optional[Dict],
    budget: int
) -> Optional[Dict]:
    """
    Выбирает блок питания:
      1. Мощность >= рассчитанной
      2. В рамках бюджета
      3. Предпочитает Gold > Bronze > без сертификата
      4. При равных — дешевле
    """
    if not psus:
        return None

    required_watts = estimate_system_power(cpu, gpu)

    def get_watt(p: Dict) -> int:
        return _get(p, "specs", "watt", default=0)

    def cert_rank(p: Dict) -> int:
        name = p.get("name", "").lower()
        if "titanium" in name:
            return 5
        if "platinum" in name:
            return 4
        if "gold" in name:
            return 3
        if "silver" in name:
            return 2
        if "bronze" in name:
            return 1
        return 0

    # Фильтр: достаточная мощность + в бюджете
    good = [p for p in psus
            if get_watt(p) >= required_watts and p["price"] <= budget]

    if not good:
        # Смягчение: достаточная мощность, но вне бюджета — берём самый дешёвый
        powerful_enough = [p for p in psus if get_watt(p) >= required_watts]
        if powerful_enough:
            return _cheapest(powerful_enough)
        # Крайний fallback: самый мощный из доступных
        if psus:
            return max(psus, key=lambda p: (get_watt(p), -p["price"]))
        return None

    # Скоринг: сертификат → мощность → цена
    def score(p: Dict) -> tuple:
        return (cert_rank(p), get_watt(p), -p["price"])

    good.sort(key=score, reverse=True)

    # Из топ-кандидатов берём самый дешёвый (не переплачиваем)
    best_cert = cert_rank(good[0])
    top_tier = [p for p in good if cert_rank(p) >= best_cert - 1]
    return min(top_tier, key=lambda p: p["price"])


# ══════════════════════════════════════════════════════════
#  COOLER
# ══════════════════════════════════════════════════════════

def pick_cooler(
    coolers: List[Dict],
    cpu: Optional[Dict],
    budget: int
) -> Optional[Dict]:
    """
    Выбирает кулер:
      1. TDP кулера >= TDP процессора (с запасом 15%)
      2. В рамках бюджета
      3. Водянка только если TDP > 200W
      4. Предпочитает воздушный при умеренном TDP (дешевле и надёжнее)
    """
    if not coolers:
        return None
    if not cpu:
        return _cheapest(_in_budget(coolers, budget)) or _cheapest(coolers)

    cpu_tdp = _get(cpu, "specs", "tdp", default=65)
    required_tdp = int(cpu_tdp * 1.15)

    WATER_THRESHOLD = 200  # водянка рекомендована при TDP > 200W

    def is_water(c: Dict) -> bool:
        w = _get(c, "specs", "water", default=False)
        if w:
            return True
        name = c.get("name", "").lower()
        return "water" in name or "liquid" in name or "aio" in name

    def cooler_tdp(c: Dict) -> int:
        return _get(c, "specs", "tdp", default=0)

    # --- Если нужна водянка ---
    if required_tdp > WATER_THRESHOLD:
        water_ok = [c for c in coolers
                    if is_water(c) and cooler_tdp(c) >= required_tdp
                    and c["price"] <= budget]
        if water_ok:
            return min(water_ok, key=lambda c: c["price"])

        # Любая водянка в бюджете
        water_any = [c for c in coolers
                     if is_water(c) and c["price"] <= budget]
        if water_any:
            return max(water_any, key=lambda c: cooler_tdp(c))

    # --- Воздушный кулер ---
    air_ok = [c for c in coolers
              if not is_water(c) and cooler_tdp(c) >= required_tdp
              and c["price"] <= budget]
    if air_ok:
        # Самый дешёвый из подходящих
        return min(air_ok, key=lambda c: c["price"])

    # Любой воздушный в бюджете (лучший по TDP)
    air_any = [c for c in coolers
               if not is_water(c) and c["price"] <= budget]
    if air_any:
        return max(air_any, key=lambda c: cooler_tdp(c))

    # Fallback: самый дешёвый кулер вообще
    return _cheapest(coolers)


# ══════════════════════════════════════════════════════════
#  CASE
# ══════════════════════════════════════════════════════════

def pick_case(
    cases: List[Dict],
    mobo: Optional[Dict],
    budget: int
) -> Optional[Dict]:
    """
    Выбирает корпус:
      1. Совместимый по форм-фактору с материнской платой
      2. БЕЗ встроенного БП (мы выбираем БП отдельно)
      3. В рамках бюджета
      4. Предпочитает корпус с вентиляторами
    """
    if not cases:
        return None

    mobo_ff = (_get(mobo, "specs", "formfactor")
               or _get(mobo, "specs", "form_factor")
               or "").lower()

    # Совместимость форм-фактора: ATX корпус подходит для ATX и mATX плат,
    # mATX корпус — только для mATX/ITX
    FF_COMPAT = {
        "atx":  {"atx", "matx", "m-atx", "itx"},
        "matx": {"matx", "m-atx", "itx"},
        "m-atx": {"matx", "m-atx", "itx"},
        "itx":  {"itx"},
    }

    def is_compatible_ff(case: Dict) -> bool:
        case_ff = (_get(case, "specs", "form_factor")
                   or _get(case, "specs", "formfactor")
                   or "").lower()
        if not mobo_ff or not case_ff:
            return True  # если нет данных — считаем совместимым
        supported = FF_COMPAT.get(case_ff, set())
        return mobo_ff in supported

    # Фильтры
    filtered = []
    for c in cases:
        specs = c.get("specs") or {}
        # Пропускаем корпуса со встроенным БП
        if specs.get("psu_watts"):
            continue
        if c["price"] > budget:
            continue
        if not is_compatible_ff(c):
            continue
        filtered.append(c)

    if not filtered:
        # Fallback: любой корпус в бюджете (без БП)
        relaxed = [c for c in cases
                   if c["price"] <= budget
                   and not (c.get("specs") or {}).get("psu_watts")]
        if relaxed:
            return _cheapest(relaxed)
        return _cheapest(cases)

    # Скоринг: вентиляторы → цена ближе к 60% квоты
    target = budget * 0.6

    def score(c: Dict) -> tuple:
        specs = c.get("specs") or {}
        has_fans = 1 if specs.get("fans_count", 0) > 0 else 0
        price_diff = abs(c["price"] - target)
        return (has_fans, -price_diff)

    filtered.sort(key=score, reverse=True)
    return filtered[0]