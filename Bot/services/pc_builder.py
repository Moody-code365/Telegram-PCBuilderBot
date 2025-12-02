import json
import os
import re
from typing import Dict, Any, List, Tuple

COMPONENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "components")


# ---------- утилиты (используем твою логику нормализации) ----------
def _safe_int(v):
    try:
        if v is None:
            return 0
        if isinstance(v, (int, float)):
            return int(v)
        s = str(v).strip().replace("\xa0", "").replace(" ", "").replace(",", "")
        if s == "" or not any(ch.isdigit() for ch in s):
            return 0
        filtered = "".join(ch for ch in s if ch.isdigit() or ch == "-")
        return int(filtered) if filtered else 0
    except Exception:
        return 0


def _normalize_item(raw: dict) -> dict:
    if not isinstance(raw, dict):
        return {"name": str(raw), "price": 0}

    name = raw.get("name") or raw.get("title") or raw.get("product") or raw.get("Наименование") or ""

    # priority price fields
    for key in ("price", "price_reseller", "price_wholesale", "price_retail", "price_opt", "price_rrp"):
        if key in raw and raw[key] not in (None, ""):
            return {"name": _clean_name(name), "price": _safe_int(raw[key]), "raw": raw}

    # fallback: any numeric field
    for k, v in raw.items():
        if isinstance(v, (int, float)) or (isinstance(v, str) and any(ch.isdigit() for ch in v)):
            return {"name": _clean_name(name), "price": _safe_int(v), "raw": raw}

    return {"name": _clean_name(name), "price": 0, "raw": raw}


def _clean_name(name: str) -> str:
    if not isinstance(name, str):
        return str(name or "")
    name = re.sub(r"http\S+", "", name)  # remove URLs
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _is_bad_name(name: str) -> bool:
    if not name:
        return True
    low = name.lower()
    if "смотрите в разделе" in low or "для серверов" in low or "сервер" in low and "серверные" in low:
        return True
    if "http" in low or "://" in low:
        return True
    if "б/у" in low or "used" in low:
        return True
    # very short or meaningless
    if len(low) < 3:
        return True
    return False


# ---------- загрузка всех компонентов (твоя старая функция, слегка улучшена) ----------
def load_all_components() -> Dict[str, List[dict]]:
    base_path = COMPONENTS_DIR
    result: Dict[str, List[dict]] = {}
    if not os.path.isdir(base_path):
        return result

    for fn in os.listdir(base_path):
        if not fn.endswith(".json"):
            continue
        key = fn[:-5]
        path = os.path.join(base_path, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            result[key] = []
            continue

        normalized: List[dict] = []
        if isinstance(raw, dict):
            for sub in raw.values():
                item = _normalize_item(sub)
                if not _is_bad_name(item["name"]) and item["price"] > 0:
                    normalized.append(item)
        elif isinstance(raw, list):
            for sub in raw:
                item = _normalize_item(sub)
                if not _is_bad_name(item["name"]) and item["price"] > 0:
                    normalized.append(item)
        else:
            result[key] = []
            continue

        # remove exact duplicate names
        seen = set()
        uniq = []
        for it in normalized:
            if it["name"] in seen:
                continue
            seen.add(it["name"])
            uniq.append(it)

        result[key] = sorted(uniq, key=lambda i: i["price"])
    return result


# ---------- детекторы / парсеры из названия ----------
def detect_socket_from_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    s = name.lower()
    # common explicit tokens
    tokens = ["lga1700", "lga1200", "lga1151", "lga1150", "am5", "am4", "s1700", "socket1700", "socket1151", "socket1200"]
    for t in tokens:
        if t in s:
            return t.upper().replace("SOCKET", "").replace("LGA", "LGA").replace("AM", "AM")
    # look for explicit numbers like 1700, 1200, 1151
    m = re.search(r"\b(1700|1200|1151|1150|2066)\b", s)
    if m:
        return m.group(1)
    # brand heuristics
    if "ryzen" in s:
        # prefer AM5 if DDR5 mention or 7000/700x/... presence
        if "ddr5" in s or re.search(r"ryzen\s?7|ryzen\s?9|ryzen\s?7000", s):
            return "AM5"
        return "AM4"
    if "intel" in s or re.search(r"\bi\d\b|\bi3\b|\bi5\b|\bi7\b|\bi9\b", s):
        # assume modern -> LGA1700 (best-effort)
        return "LGA1700"
    return ""


def detect_ram_type_from_mobo(name: str) -> str:
    s = (name or "").lower()
    if "ddr5" in s:
        return "DDR5"
    if "ddr4" in s:
        return "DDR4"
    # fallback: look for motherboard model families: B650/X670 -> DDR5 likely
    if re.search(r"\b(b6|x6|z7)\d", s):
        return "DDR5"
    return "DDR4"


def detect_gpu_tier(name: str) -> int:
    # approximate GPU "tier" by price keywords or model
    s = (name or "").lower()
    # heavy heuristics
    if any(k in s for k in ["4090", "4080", "3090"]):
        return 5
    if any(k in s for k in ["4070", "3080", "3070", "6900"]):
        return 4
    if any(k in s for k in ["4060", "3060", "6700", "6600"]):
        return 3
    if any(k in s for k in ["3060 ti", "2060", "1660", "1650"]):
        return 2
    return 1


def estimate_cpu_tdp_by_name(name: str) -> int:
    s = (name or "").lower()
    # rough
    if any(x in s for x in ["ryzen 9", "i9", "threadripper", "epyc"]):
        return 125
    if any(x in s for x in ["ryzen 7", "i7"]):
        return 95
    if any(x in s for x in ["ryzen 5", "i5"]):
        return 65
    if any(x in s for x in ["celeron", "pentium", "athlon"]):
        return 35
    return 65


def estimate_gpu_power_by_tier(tier: int) -> int:
    # approximate GPU TDP by tier
    mapping = {1: 75, 2: 150, 3: 200, 4: 300, 5: 450}
    return mapping.get(tier, 150)


def parse_psu_wattage(name: str) -> int:
    if not isinstance(name, str):
        return 0
    s = name.lower()
    m = re.search(r"(\d{3,4})\s*w", s)
    if m:
        return int(m.group(1))
    m2 = re.search(r"(\d{3,4})\s*вт", s)  # russian
    if m2:
        return int(m2.group(1))
    # try digits with 'w' missing
    m3 = re.search(r"(\d{3,4})\b", s)
    if m3:
        val = int(m3.group(1))
        if 200 <= val <= 2000:
            return val
    return 0


# ---------- выбор компонентов ----------
def pick_best_component(components: Dict[str, list], category: str, part_budget: int = None) -> dict:
    items = components.get(category, [])
    if not items:
        return {"name": "Нет данных", "price": 0}

    # ensure price exists and positive
    items = [i for i in items if isinstance(i.get("price", None), (int, float)) and i["price"] > 0]
    if not items:
        return {"name": "Нет данных", "price": 0}

    # if no budget constraint — return a mid-high choice (not absolute cheapest)
    if not part_budget or part_budget <= 0:
        # pick item around 25% from top by price to avoid ultra-cheap trash
        idx = max(0, min(len(items)-1, int(len(items) * 0.25)))
        return items[idx]

    # choose the priciest item <= part_budget
    under = [i for i in items if i["price"] <= part_budget]
    if under:
        best = sorted(under, key=lambda x: x["price"], reverse=True)[0]
        return best

    # nothing fits -> return the cheapest
    return items[0]


def pick_motherboard_for_cpu(components: Dict[str, list], cpu_item: dict, part_budget: int = None) -> dict:
    mobos = components.get("motherboard", [])
    if not mobos:
        return {"name": "Нет данных", "price": 0}

    cpu_name = cpu_item.get("name", "")
    socket = detect_socket_from_name(cpu_name)
    # filter mobos by socket keyword
    candidates = []
    for m in mobos:
        mname = m.get("name", "").lower()
        if socket and socket.lower() in mname:
            candidates.append(m)
    # if none matched, try to prefer DDR5 motherboards for modern CPUs
    if not candidates:
        if "ddr5" in cpu_name.lower() or "am5" in cpu_name.lower():
            candidates = [m for m in mobos if "ddr5" in m.get("name", "").lower()]
    # fallback all
    if not candidates:
        candidates = mobos

    # normalize
    candidates = [i for i in candidates if isinstance(i.get("price", None), (int,float)) and i["price"]>0]
    if not candidates:
        return {"name": "Нет данных", "price": 0}

    # apply part_budget if exists
    if part_budget and part_budget>0:
        under = [i for i in candidates if i["price"] <= part_budget]
        if under:
            return sorted(under, key=lambda x: x["price"], reverse=True)[0]
    # else return mid option
    idx = max(0, min(len(candidates)-1, int(len(candidates) * 0.3)))
    return candidates[idx]


def pick_ram_for_mobo(components: Dict[str, list], mobo_item: dict, part_budget: int = None) -> dict:
    rams = components.get("ram", [])
    if not rams:
        return {"name": "Нет данных", "price": 0}
    ram_type = detect_ram_type_from_mobo(mobo_item.get("name", "")) if mobo_item and isinstance(mobo_item, dict) else "DDR4"
    candidates = [r for r in rams if ram_type.lower() in r.get("name","").lower()]
    if not candidates:
        candidates = rams
    candidates = [i for i in candidates if isinstance(i.get("price", None), (int,float)) and i["price"]>0]
    if not candidates:
        return {"name":"Нет данных","price":0}
    if part_budget and part_budget>0:
        under = [i for i in candidates if i["price"] <= part_budget]
        if under:
            return sorted(under, key=lambda x: x["price"], reverse=True)[0]
    # pick cheapest 25% index to save money on RAM
    idx = max(0, min(len(candidates)-1, int(len(candidates)*0.15)))
    return candidates[idx]


def pick_gpu(components: Dict[str, list], part_budget: int = None, prefs: str = "") -> dict:
    gpus = components.get("gpu", [])
    if not gpus:
        return {"name":"Нет данных","price":0}
    # filter by preference keywords
    if prefs:
        p = prefs.lower()
        with_pref = [g for g in gpus if p in g.get("name","").lower()]
        if with_pref:
            gpus = with_pref
    gpus = [i for i in gpus if isinstance(i.get("price", None), (int,float)) and i["price"]>0]
    if not gpus:
        return {"name":"Нет данных","price":0}
    if part_budget and part_budget>0:
        under = [i for i in gpus if i["price"] <= part_budget]
        if under:
            # choose the most powerful-look by price (highest within budget)
            return sorted(under, key=lambda x: x["price"], reverse=True)[0]
    # pick median-ish GPU
    idx = max(0, min(len(gpus)-1, int(len(gpus)*0.5)))
    return gpus[idx]


def pick_ssd(components: Dict[str, list], part_budget: int = None, prefer_capacity_gb: int = 500) -> dict:
    ssds = components.get("ssd", [])
    if not ssds:
        return {"name":"Нет данных","price":0}
    ssds = [i for i in ssds if isinstance(i.get("price", None),(int,float)) and i["price"]>0]
    # try to prefer capacity in name
    candidates = []
    for s in ssds:
        nm = s.get("name","").lower()
        cap = 0
        m = re.search(r"(\d{3,4})\s*gb", nm)
        if m:
            cap = int(m.group(1))
        if cap >= prefer_capacity_gb:
            candidates.append((cap, s))
    if candidates:
        # sort by cap desc then price asc
        candidates = sorted(candidates, key=lambda x: (-x[0], x[1]["price"]))
        # get items
        items = [c[1] for c in candidates]
    else:
        items = ssds

    if part_budget and part_budget>0:
        under = [i for i in items if i["price"] <= part_budget]
        if under:
            return sorted(under, key=lambda x: x["price"], reverse=True)[0]
    return items[0]


def pick_psu(components: Dict[str, list], required_watt: int, part_budget: int = None) -> dict:
    psus = components.get("psu", [])
    if not psus:
        return {"name":"Нет данных","price":0}
    valid = []
    for p in psus:
        name = p.get("name","")
        watt = parse_psu_wattage(name)
        price = p.get("price",0)
        if watt >= required_watt and price>0:
            valid.append((watt,price,p))
    if valid:
        # prefer cheapest that still meets watt
        valid = sorted(valid, key=lambda x: (x[1], -x[0]))
        for watt,price,item in valid:
            if part_budget and part_budget>0 and price>part_budget:
                continue
            return item
        # none within part_budget -> return cheapest overall
        return valid[0][2]
    # fallback: choose the highest watt available
    psus_sorted = sorted([p for p in psus if p.get("price",0)>0], key=lambda x: parse_psu_wattage(x.get("name","")), reverse=True)
    return psus_sorted[0] if psus_sorted else {"name":"Нет данных","price":0}


# ---------- пресеты и распределение (остается) ----------
BUILD_PRESETS = {
    "office": {
        "cpu": "cpu",
        "gpu": "gpu",
        "ram": "ram",
        "case": "case",
        "motherboard": "motherboard",
        "coolers":"coolers",
        "ssd": "ssd",
        "psu": "psu",
    },
    "gaming_low": {
         "cpu": "cpu",
        "gpu": "gpu",
        "ram": "ram",
        "case": "case",
        "motherboard": "motherboard",
        "coolers":"coolers",
        "ssd": "ssd",
        "psu": "psu",
    },
    "gaming_mid": {
        "cpu": "cpu",
        "gpu": "gpu",
        "ram": "ram",
        "case": "case",
        "motherboard": "motherboard",
        "coolers": "coolers",
        "ssd": "ssd",
        "psu": "psu",
    },
    "gaming_high": {
        "cpu": "cpu",
        "gpu": "gpu",
        "ram": "ram",
        "case": "case",
        "motherboard": "motherboard",
        "coolers": "coolers",
        "ssd": "ssd",
        "psu": "psu",
    }
}

BUDGET_MAP = {
    "до 150 000 ₸": (0, 150_000),
    "150–200 000 ₸": (150_000, 200_000),
    "250–300 000 ₸": (250_000, 300_000),
    "400–600 000 ₸": (400_000, 600_000),
    "600 000 ₸+": (600_000, 10_000_000),
}

def normalize_budget(budget: Any) -> int:
    if isinstance(budget, int):
        return budget
    return BUDGET_MAP.get(budget, (0, 0))[1]


BUDGET_DISTRIBUTION = {
    "office": {"cpu": 0.30, "ram": 0.20, "ssd": 0.15, "psu": 0.10, "gpu": 0.00, "case":0.05, "motherboard":0.10, "coolers":0.05},
    "gaming_low": {"cpu": 0.25, "gpu": 0.35, "ram": 0.15, "ssd": 0.15, "psu": 0.10, "case":0.05, "motherboard":0.10, "coolers":0.05},
    "gaming_mid": {"cpu": 0.25, "gpu": 0.40, "ram": 0.15, "ssd": 0.10, "psu": 0.10, "case":0.05, "motherboard":0.10, "coolers":0.05},
    "gaming_high": {"cpu": 0.30, "gpu": 0.45, "ram": 0.10, "ssd": 0.05, "psu": 0.10, "case":0.05, "motherboard":0.10, "coolers":0.05},
}


# ---------- главная логика сборки ----------
def build_pc(data: Dict[str, Any]) -> Dict[str, Any]:
    budget = normalize_budget(data.get("budget", 0))
    usage = data.get("usage", "работа")
    prefs = (data.get("preferences") or "").lower()

    preset_key = "office"
    if usage == "работа":
        preset_key = "office"
    elif usage == "игры":
        if budget < 200_000:
            preset_key = "gaming_low"
        elif budget < 400_000:
            preset_key = "gaming_mid"
        else:
            preset_key = "gaming_high"
    elif usage == "универсальный":
        preset_key = "gaming_low" if budget < 300_000 else "gaming_mid"

    preset = BUILD_PRESETS.get(preset_key)
    components = load_all_components()
    dist = BUDGET_DISTRIBUTION.get(preset_key, BUDGET_DISTRIBUTION["office"])

    final: Dict[str, dict] = {}
    total = 0

    # 1) CPU
    cpu_share = int(budget * dist.get("cpu", 0))
    cpu = pick_best_component(components, preset["cpu"], part_budget=cpu_share)
    final["cpu"] = cpu
    total += cpu.get("price", 0)

    # 2) GPU (use prefs)
    gpu_share = int(budget * dist.get("gpu", 0))
    gpu = pick_gpu(components, part_budget=gpu_share, prefs=prefs)
    final["gpu"] = gpu
    total += gpu.get("price", 0)

    # 3) Motherboard (compatible with CPU)
    mobo_share = int(budget * dist.get("motherboard", 0))
    motherboard = pick_motherboard_for_cpu(components, cpu, part_budget=mobo_share)
    final["motherboard"] = motherboard
    total += motherboard.get("price", 0)

    # 4) RAM (compatible with mobo)
    ram_share = int(budget * dist.get("ram", 0))
    ram = pick_ram_for_mobo(components, motherboard, part_budget=ram_share)
    final["ram"] = ram
    total += ram.get("price", 0)

    # 5) SSD
    ssd_share = int(budget * dist.get("ssd", 0))
    # prefer 500GB for mid/gaming, 240/256 for office
    prefer_cap = 500 if "gaming" in preset_key else 256
    ssd = pick_ssd(components, part_budget=ssd_share, prefer_capacity_gb=prefer_cap)
    final["ssd"] = ssd
    total += ssd.get("price", 0)

    # 6) Coolers (if need)
    cooler_share = int(budget * dist.get("coolers", 0))
    # if CPU TDP high, try to pick better cooler; for now pick generic
    cooler = pick_best_component(components, "coolers", part_budget=cooler_share)
    final["coolers"] = cooler
    total += cooler.get("price", 0)

    # 7) Case
    case_share = int(budget * dist.get("case", 0))
    case = pick_best_component(components, "case", part_budget=case_share)
    final["case"] = case
    total += case.get("price", 0)

    # 8) PSU — estimate required watt
    cpu_tdp = estimate_cpu_tdp_by_name(cpu.get("name",""))
    gpu_tier = detect_gpu_tier(gpu.get("name",""))
    gpu_tdp = estimate_gpu_power_by_tier(gpu_tier)
    required = int(cpu_tdp + gpu_tdp + 200)  # safety buffer
    psu_share = int(budget * dist.get("psu", 0))
    psu = pick_psu(components, required_watt=required, part_budget=psu_share)
    final["psu"] = psu
    total += psu.get("price", 0)

    return {"build": final, "total_price": total}
