# services/pc_builder_cpu.py
from typing import List, Dict, Optional


def pick_cpu(cpus: List[Dict], budget: int) -> Optional[Dict]:
    candidates = [c for c in cpus if c["price"] <= budget]
    if not candidates:
        # fallback: take the cheapest CPU (so build is always complete)
        if cpus:
            return sorted(cpus, key=lambda x: x["price"])[0]
        return None

    def score(cpu):
        specs = cpu.get("specs", {}) or {}
        cores = specs.get("cores", 0)
        threads = specs.get("threads", 0)
        freq = specs.get("mhz", 0)
        price = cpu["price"]
        target_price = budget * 0.85
        price_penalty = abs(target_price - price)
        return (cores, threads, freq, -price_penalty)

    candidates.sort(key=score, reverse=True)
    return candidates[0]


def pick_motherboard(mobos: List[Dict], cpu: Dict, max_budget: int | None = None) -> Optional[Dict]:
    if not cpu:
        return None

    cpu_socket = (cpu.get("specs") or {}).get("socket")
    if not cpu_socket:
        # fallback: pick the most common mobo (cheapest)
        if mobos:
            return sorted(mobos, key=lambda m: m["price"])[0]
        return None

    # 1) Совместимость по сокету
    candidates = [m for m in mobos if (m.get("specs") or {}).get("socket") == cpu_socket]

    # Relax: возможно в базе нет идеальной платы — попробуем без сокета (cheapest)
    if not candidates:
        # возвращаем самую дешевую совместимую по форм-фактору/если есть — иначе самую дешевую
        if mobos:
            # попробуем хотя бы по formfactor, если CPU дает hint через specs.ram_type
            mobo_by_price = sorted(mobos, key=lambda m: m["price"])
            return mobo_by_price[0]
        return None

    # 2) Отбрасываем слишком дешёвые платы (условно хлам)
    min_ok_price = cpu["price"] * 0.25
    filtered = [m for m in candidates if m["price"] >= min_ok_price]

    if not filtered:
        # relax: если ничего не осталось — берем кандидатов (чтобы не вернуть None)
        filtered = candidates

    # 3) Учитываем бюджет сборки (если указан)
    if max_budget:
        in_budget = [m for m in filtered if m["price"] <= max_budget]
        if in_budget:
            filtered = in_budget
        # else: оставляем filtered (не делать None) — fallback will handle

    # 4) Оценка качества
    def score(m):
        specs = m.get("specs") or {}
        rating = 0
        form = specs.get("formfactor", "") or specs.get("form_factor", "")
        form = form.lower()
        if form == "atx":
            rating += 3
        elif form in ("matx", "mATX".lower()):
            rating += 2
        elif form == "itx":
            rating += 1
        rating += m["price"] / 10000
        return rating

    filtered.sort(key=lambda m: score(m), reverse=True)
    return filtered[0]


def pick_ram(rams: List[Dict], mobo: Dict, budget_left: int) -> Optional[Dict]:
    if not mobo:
        # fallback: best affordable RAM
        candidates = [r for r in rams if r["price"] <= budget_left] or rams
        if not candidates:
            return None
        candidates.sort(key=lambda r: (- (r.get("specs") or {}).get("capacity_gb", 0),
                                       - (r.get("specs") or {}).get("mhz", 0),
                                       r["price"]))
        return candidates[0]

    mobo_ram_type = (mobo.get("specs") or {}).get("ram_type")
    candidates = [
        r for r in rams
        if (r.get("specs") or {}).get("ddr") == mobo_ram_type and r["price"] <= budget_left
    ]

    if not candidates:
        # relax: compatible but over budget
        candidates = [
            r for r in rams
            if (r.get("specs") or {}).get("ddr") == mobo_ram_type
        ]

    if not candidates:
        # as last resort — any RAM within budget or cheapest RAM
        candidates = [r for r in rams if r["price"] <= budget_left] or rams

    if not candidates:
        return None

    candidates.sort(
        key=lambda r: (
            - (r.get("specs") or {}).get("capacity_gb", 0),
            - (r.get("specs") or {}).get("mhz", 0),
            r["price"]
        )
    )
    return candidates[0]


def pick_gpu(gpus: List[Dict], budget: int) -> Optional[Dict]:
    candidates = [g for g in gpus if g["price"] <= budget]
    if not candidates:
        # fallback: take the best GPU ignoring budget (but prefer cheaper)
        if not gpus:
            return None
        gpus.sort(key=lambda g: (- (g.get("specs") or {}).get("vram_gb", 0),
                                 - (g.get("specs") or {}).get("gddr", 0),
                                 g["price"]))
        return gpus[0]

    def gpu_score(g):
        specs = g.get("specs") or {}
        return (specs.get("vram_gb", 0), specs.get("gddr", 0))

    candidates.sort(
        key=lambda g: (
            -gpu_score(g)[0],
            -gpu_score(g)[1],
            g["price"]
        )
    )
    return candidates[0]


def pick_ssd(ssds: List[Dict], budget: int) -> Optional[Dict]:
    candidates = [s for s in ssds if s["price"] <= budget]
    if not candidates:
        # fallback: prefer NVMe if exists, otherwise cheapest
        nvmes = [s for s in ssds if (s.get("specs") or {}).get("interface", "").lower().find("nvme") != -1]
        if nvmes:
            nvmes.sort(key=lambda s: (- (s.get("specs") or {}).get("capacity_gb", 0), s["price"]))
            return nvmes[0]
        if ssds:
            return sorted(ssds, key=lambda s: s["price"])[0]
        return None

    iface_rank = {
        "sata": 1, "sata3": 1, "sata 6gb/s": 1, "m.2 sata": 1,
        "nvme": 2, "m.2 nvme": 2, "pcie": 2,
    }

    def ssd_score(s):
        specs = s.get("specs") or {}
        interface = specs.get("interface", "").lower()
        return (specs.get("capacity_gb", 0), iface_rank.get(interface, 1))

    candidates.sort(key=lambda s: (-ssd_score(s)[0], -ssd_score(s)[1], s["price"]))
    return candidates[0]


def estimate_gpu_tdp(gpu: Dict | None) -> int:
    if not gpu:
        return 0
    vram = (gpu.get("specs") or {}).get("vram_gb", 0)
    # preserve your mapping
    if vram <= 2:
        return 50
    if vram <= 4:
        return 100
    if vram <= 8:
        return 180
    if vram <= 12:
        return 200
    if vram <= 16:
        return 250
    if vram <= 32:
        return 350
    return 250


def pick_psu(psus: List[Dict], cpu: Dict, gpu: Dict, budget: int) -> Optional[Dict]:
    """
    Improved PSU picker:
    - prefer known-good units (look for Gold/Platinum in name/specs)
    - filter obvious trash by name
    - choose by (cert, wattage, price)
    - if nothing fits budget, relax budget and try again; as last resort return the strongest unit available
    """
    if not psus:
        return None

    # compute required watt roughly
    cpu_tdp = (cpu.get("specs") or {}).get("tdp", 65)
    gpu_tdp = estimate_gpu_tdp(gpu)
    base_load = cpu_tdp + gpu_tdp + 100
    required = int(base_load * 1.3)

    # helpers for robustness (some DBs use 'watt' or 'wattage' or 'watt' under specs)
    def get_watt(p):
        specs = p.get("specs") or {}
        return specs.get("watt") or specs.get("wattage") or specs.get("power") or 0

    # blacklist obvious junk by substring in name
    blacklist = ["delux", "wintek", "powerman", "power man", "aerocool vx", "gamemax", "q-dion"]
    pool = [p for p in psus if not any(b in p["name"].lower() for b in blacklist)]

    # if pool empty, fallback to full list (don't return None yet)
    if not pool:
        pool = psus.copy()

    # filter by watt requirement first
    candidates = [p for p in pool if get_watt(p) >= required and p["price"] <= budget]

    # if none in budget, allow >= required but ignore budget
    if not candidates:
        candidates = [p for p in pool if get_watt(p) >= required]

    # if still none, take the highest-watt unit available (fallback)
    if not candidates:
        pool_sorted = sorted(pool, key=lambda p: (get_watt(p), -p["price"]), reverse=True)
        return pool_sorted[0] if pool_sorted else None

    # scoring by certification (try to detect in specs or name)
    def cert_score(p):
        specs = p.get("specs") or {}
        eff = (specs.get("efficiency") or p["name"]).lower()
        if "platinum" in eff:
            return 4
        if "gold" in eff:
            return 3
        if "silver" in eff:
            return 2
        if "bronze" in eff:
            return 1
        return 0

    # prefer higher cert, then higher watt, then lower price
    candidates.sort(key=lambda p: (cert_score(p), get_watt(p), -p["price"]), reverse=True)
    # we sorted reverse so best is first
    # but we want cheaper among equals — reorder to pick best cert/watt but moderate price
    candidates.sort(key=lambda p: (-cert_score(p), -get_watt(p), p["price"]))
    return candidates[0]


def pick_cooler(coolers: List[Dict], cpu: Dict, budget: int) -> Optional[Dict]:
    """
    Improved cooler picker:
    - calculate required_tdp
    - if water needed: try water within budget
        * if none in budget: try best air with highest tdp within budget
        * if none still: pick best water/air ignoring budget (fallback)
    - if air needed: pick air with tdp >= required within budget, else choose highest-TDP air in budget,
      else fallback to cheapest overall
    """
    if not cpu:
        return None

    cpu_tdp = (cpu.get("specs") or {}).get("tdp", 65)
    cores = (cpu.get("specs") or {}).get("cores", 4)
    threads = (cpu.get("specs") or {}).get("threads", 4)

    core_heat = cpu_tdp * (1 + max(0, cores - 4) * 0.12)
    thread_heat = cpu_tdp * (threads * 0.01)
    required_tdp = int((core_heat + thread_heat) * 1.10)

    NEED_WATER_THRESHOLD = 260

    def is_water(c):
        return (c.get("specs") or {}).get("water", False) or ("aio" in c["name"].lower()) or ("water" in c["name"].lower())

    def cooler_tdp(c):
        return (c.get("specs") or {}).get("tdp") or (c.get("specs") or {}).get("cooler_tdp") or 0

    # helper sorters
    def best_water_sort_key(c):
        # prefer cheaper water with bigger rad (we don't have rad size; use tdp)
        return (-cooler_tdp(c), c["price"])

    def best_air_sort_key(c):
        # prefer higher TDP, then lower price
        return (-cooler_tdp(c), c["price"])

    # --- if water recommended ---
    if required_tdp > NEED_WATER_THRESHOLD:
        water_in_budget = [c for c in coolers if is_water(c) and c["price"] <= budget]
        if water_in_budget:
            water_in_budget.sort(key=best_water_sort_key)
            return water_in_budget[0]
        # no water in budget -> try best air in budget with highest tdp
        air_in_budget = [c for c in coolers if not is_water(c) and c["price"] <= budget]
        if air_in_budget:
            air_in_budget.sort(key=best_air_sort_key)
            return air_in_budget[0]
        # fallback: pick best water ignoring budget
        all_water = [c for c in coolers if is_water(c)]
        if all_water:
            all_water.sort(key=best_water_sort_key)
            return all_water[0]
        # final fallback: best air ignoring budget
        if coolers:
            coolers.sort(key=best_air_sort_key)
            return coolers[0]
        return None

    # --- otherwise air is OK ---
    air_candidates = [c for c in coolers if not is_water(c) and cooler_tdp(c) >= required_tdp and c["price"] <= budget]
    if air_candidates:
        air_candidates.sort(key=best_air_sort_key)
        return air_candidates[0]

    # try best air in budget even if tdp < required
    air_in_budget = [c for c in coolers if not is_water(c) and c["price"] <= budget]
    if air_in_budget:
        air_in_budget.sort(key=best_air_sort_key)
        return air_in_budget[0]

    # try any cooler ignoring budget (pick highest TDP)
    if coolers:
        coolers.sort(key=best_air_sort_key)
        return coolers[0]

    return None


def pick_case(cases: List[Dict], mobo: Dict, budget: int) -> Optional[Dict]:
    if not cases:
        return None

    # guard if mobo is None -> pick a reasonable ATX case if exists else cheapest
    required_ff = None
    if mobo:
        required_ff = (mobo.get("specs") or {}).get("formfactor") or (mobo.get("specs") or {}).get("form_factor")

    filtered = []
    for case in cases:
        price = case["price"]
        specs = case.get("specs") or {}

        # ignore cases with built-in PSU (we decided to never pick them)
        if specs.get("psu_watts"):
            continue

        # budget filter
        if price > budget:
            continue

        case_ff = specs.get("form_factor") or specs.get("formfactor")
        # normalize
        if isinstance(case_ff, str):
            case_ff_norm = case_ff.lower()
        else:
            case_ff_norm = case_ff

        # compatibility if we have required formfactor
        if required_ff:
            req = required_ff.lower()
            if req == "atx" and case_ff_norm != "atx":
                continue
            if req == "matx" and case_ff_norm not in ("matx", "m-atx", "microatx", "atx"):
                continue
            if req == "itx" and case_ff_norm not in ("itx", "mini-itx", "m-atx", "atx"):
                continue

        # track fans
        specs["_has_fans"] = specs.get("fans_count", 0) > 0
        filtered.append(case)

    if not filtered:
        # fallback: any case within budget or cheapest case overall
        in_budget = [c for c in cases if c["price"] <= budget]
        if in_budget:
            # prefer ones with fans
            in_budget.sort(key=lambda c: (0 if (c.get("specs") or {}).get("_has_fans", False) else 1, abs(c["price"] - budget)))
            return in_budget[0]
        # cheapest overall
        return sorted(cases, key=lambda c: c["price"])[0]

    # prefer cases with fans and price close to 70% of budget
    target_price = budget * 0.7

    def score_case(c):
        p = c["price"]
        has_fans = (c.get("specs") or {}).get("_has_fans", False)
        return (0 if has_fans else 1, abs(p - target_price))

    filtered.sort(key=score_case)
    return filtered[0]
