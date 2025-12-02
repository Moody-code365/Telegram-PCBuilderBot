# Bot/services/pc_builder.py
# Профессиональный, самодостаточный smart builder — версия 1.0
# Интерфейс: build_pc(data: Dict[str,Any]) -> {"build": {...}, "total_price": int, "explain": str}

import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from functools import lru_cache

COMPONENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "components")

# -------------------------
# Конфигурация: бюджетные метки
# -------------------------
BUDGET_MAP = {
    "до 150 000 ₸": (0, 150_000),
    "150–200 000 ₸": (150_000, 200_000),
    "250–300 000 ₸": (250_000, 300_000),
    "400–600 000 ₸": (400_000, 600_000),
    "600 000 ₸+": (600_000, 10_000_000),
}

# Usage profiles — веса для scoring
USAGE_PROFILES = {
    "games": {"cpu_single": 0.6, "cpu_multi": 0.2, "gpu": 1.0, "ram": 0.5, "ssd": 0.2},
    "work":  {"cpu_single": 0.2, "cpu_multi": 1.0, "gpu": 0.2, "ram": 0.8, "ssd": 0.3},
    "universal": {"cpu_single": 0.4, "cpu_multi": 0.6, "gpu": 0.6, "ram": 0.6, "ssd": 0.3},
}

# Budget distributions (preset)
BUDGET_DISTRIBUTION = {
    "office": {"cpu": 0.30, "ram": 0.20, "ssd": 0.15, "psu": 0.10, "gpu": 0.00, "case":0.05, "motherboard":0.10, "coolers":0.05},
    "gaming_low": {"cpu": 0.25, "gpu": 0.35, "ram":0.15, "ssd":0.15, "psu":0.10, "case":0.05, "motherboard":0.05, "coolers":0.05},
    "gaming_mid": {"cpu": 0.25, "gpu": 0.40, "ram":0.15, "ssd":0.10, "psu":0.10, "case":0.05, "motherboard":0.05, "coolers":0.05},
    "gaming_high": {"cpu": 0.30, "gpu": 0.45, "ram":0.10, "ssd":0.05, "psu":0.10, "case":0.05, "motherboard":0.05},
    "universal": {"cpu":0.25,"gpu":0.25,"ram":0.20,"ssd":0.12,"psu":0.08,"motherboard":0.05,"case":0.03,"coolers":0.02}
}

# -------------------------
# Утилиты: нормализация и безопасный int
# -------------------------
def _safe_int(v) -> int:
    try:
        if v is None: return 0
        if isinstance(v, bool): return 0
        if isinstance(v, (int, float)): return int(v)
        s = str(v)
        s = s.replace("\u2009","").replace("\xa0","").replace("₸","").replace(",","").replace(" ", "")
        filtered = "".join(ch for ch in s if ch.isdigit() or ch == "-")
        if filtered in ("", "-", "+"): return 0
        return int(filtered)
    except Exception:
        return 0

def _clean_name(name: Any) -> str:
    try:
        if name is None: return ""
        s = str(name)
        s = re.sub(r"http\S+", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s
    except:
        return str(name or "")

# -------------------------
# Loader: читаем компоненты и нормализуем к единообразному объекту
# -------------------------
@lru_cache(maxsize=1)
def load_all_components() -> Dict[str, List[Dict[str,Any]]]:
    """
    Возвращает dict: категория -> list[component]
    Компонент: {"name","price","category","specs":{...},"_raw":...}
    Попытка извлечь сокет/ram_type/tdp/psu_watt из названия.
    """
    res: Dict[str, List[Dict[str,Any]]] = {}
    base = Path(COMPONENTS_DIR)
    if not base.exists():
        return res
    for f in base.glob("*.json"):
        key = f.stem
        arr = []
        try:
            raw = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            res[key] = []
            continue
        iterable = raw.values() if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
        for entry in iterable:
            if not isinstance(entry, dict):
                continue
            name = _clean_name(entry.get("name") or entry.get("title") or entry.get("Наименование") or "")
            if not name:
                continue
            # price extraction
            price = 0
            for pk in ("price","price_reseller","price_wholesale","price_retail","price_opt","cost","price_rrp"):
                if pk in entry and entry[pk] not in (None, ""):
                    price = _safe_int(entry[pk]); break
            if price == 0:
                # fallback any numeric field
                for v in entry.values():
                    if isinstance(v, (int,float)) or (isinstance(v, str) and re.search(r"\d", v)):
                        price = _safe_int(v)
                        if price > 0: break
            if price <= 0:
                continue
            # basic specs extraction attempt (best-effort)
            specs = {}
            name_l = name.lower()
            # socket
            if "am5" in name_l: specs["socket"] = "AM5"
            elif "am4" in name_l: specs["socket"] = "AM4"
            elif "lga1700" in name_l or "1700" in name_l: specs["socket"] = "LGA1700"
            elif "lga1200" in name_l or "1200" in name_l: specs["socket"] = "LGA1200"
            # ram type
            if "ddr5" in name_l: specs["ram_type"] = "DDR5"
            elif "ddr4" in name_l: specs["ram_type"] = "DDR4"
            # tdp detect -- naive
            m = re.search(r"(\d{2,3})\s*w", name_l)
            if m: specs["tdp"] = int(m.group(1))
            # psu watt
            m2 = re.search(r"(\d{3,4})\s*w", name_l)
            if m2: specs["psu_watt"] = int(m2.group(1))
            # ram capacity
            m3 = re.search(r"(\d{1,2})\s*x\s*(\d{1,3})\s*gb", name_l)
            if m3:
                try: specs["ram_capacity"] = int(m3.group(1))*int(m3.group(2))
                except: pass
            else:
                m4 = re.search(r"(\d{2,4})\s*gb", name_l)
                if m4: specs["ram_capacity"] = int(m4.group(1))
            arr.append({
                "name": name,
                "price": int(price),
                "category": key,
                "specs": specs,
                "_raw": entry
            })
        # dedupe by name keep cheapest
        uniq = {}
        for it in arr:
            n = it["name"]
            if n in uniq:
                if it["price"] < uniq[n]["price"]:
                    uniq[n] = it
            else:
                uniq[n] = it
        res[key] = sorted(list(uniq.values()), key=lambda x: x["price"])
    return res

# -------------------------
# Compatibility rules
# -------------------------
def cpu_mobo_compatible(cpu: Dict[str,Any], mobo: Dict[str,Any]) -> bool:
    if not cpu or not mobo: return True
    c_socket = cpu.get("specs", {}).get("socket")
    m_socket = mobo.get("specs", {}).get("socket")
    if c_socket and m_socket:
        return c_socket.lower() == m_socket.lower()
    # fallback: if mobo name contains CPU series -> assume ok (best effort)
    if cpu.get("name","").split()[0].lower() in mobo.get("name","").lower():
        return True
    return True  # be permissive if unknown

def ram_mobo_compatible(ram: Dict[str,Any], mobo: Dict[str,Any]) -> bool:
    if not ram or not mobo: return True
    m_type = mobo.get("specs", {}).get("ram_type")
    r_name = ram.get("name","").lower()
    if m_type:
        return m_type.lower() in r_name
    return True

def psu_sufficient(psu: Dict[str,Any], required_watt: int) -> bool:
    if not psu: return False
    # try parse from psu.specs or name
    p_w = psu.get("specs", {}).get("psu_watt") or 0
    if p_w >= required_watt: return True
    # fallback parse digits from name
    m = re.search(r"(\d{3,4})\s*w", psu.get("name","").lower())
    if m:
        return int(m.group(1)) >= required_watt
    return False

# -------------------------
# Scoring (simple, extensible)
# -------------------------
def score_component(comp: Dict[str,Any], category: str, usage_profile: Dict[str,float]) -> float:
    """
    Возвращаем относительную оценку — чем больше, тем лучше.
    Базовая формула: perf_score / price_penalty + compatibility bonuses.
    perf_score — зависит от category and specs (best-effort)
    """
    specs = comp.get("specs", {})
    name = comp.get("name","").lower()
    price = max(1, int(comp.get("price",0)))

    perf = 1.0
    # heuristics: try to infer perf numbers from names/specs
    if category == "cpu":
        # try extract model number like 7600, 5600, i5-12400 etc
        m = re.search(r"(\b\d{3,4}\b)", name)
        if m:
            try: perf = float(int(m.group(1)) / 1000.0 + 1.0)
            except: perf = 1.0
        # tdp as proxy
        perf += (specs.get("tdp",0) / 100.0)
        # usage influence
        up = usage_profile.get("cpu_multi",1.0) * 0.6 + usage_profile.get("cpu_single",1.0)*0.4
        perf *= up
    elif category == "gpu":
        # gpu tier from name
        t = 1
        if "4090" in name or "4090" in name: t = 5
        elif "4080" in name or "4090" in name: t = 5
        elif "4070" in name or "3080" in name: t = 4
        elif "4060" in name or "3060" in name: t = 3
        perf = float(t)
        perf *= usage_profile.get("gpu", 1.0)
    elif category == "ram":
        cap = specs.get("ram_capacity",0)
        perf = 1.0 + (cap/16.0)
        perf *= usage_profile.get("ram",1.0)
    elif category == "ssd":
        # prefer higher capacity (simple)
        cap = specs.get("ram_capacity",0) or 0
        perf = 1.0 + (cap / 256.0)
        perf *= usage_profile.get("ssd",1.0)
    else:
        perf = 1.0

    # price penalty
    score = perf / (price**0.3)  # soft penalty
    return float(score)

# -------------------------
# Pickers (choose best candidate given budget and usage)
# -------------------------
def pick_best(components: List[Dict[str,Any]], budget_part: int, category: str, usage_profile: Dict[str,float]) -> Dict[str,Any]:
    """
    Выбор лучшего по score среди кандидатов в бюджете.
    Если ничего не помещается — возвращаем самый дешёвый (фоллбек).
    """
    if not components:
        return {"name":"Нет данных","price":0, "category": category}
    items = [c for c in components if isinstance(c.get("price"), int) and c["price"]>0]
    if not items:
        return {"name":"Нет данных","price":0, "category": category}
    # candidates under budget
    under = [c for c in items if c["price"] <= max(0,int(budget_part))]
    if under:
        ranked = sorted(under, key=lambda c: score_component(c, category, usage_profile), reverse=True)
        return ranked[0]
    # none under budget, pick smallest over (balanced)
    over = sorted(items, key=lambda c: c["price"])
    return over[0]

# -------------------------
# Degrade logic: понижение в порядке минимального damage
# -------------------------
def degrade_to_budget(build: Dict[str,Dict[str,Any]], components: Dict[str,List[Dict[str,Any]]], target_budget: int) -> Tuple[Dict[str,Dict[str,Any]], int]:
    """
    Попытка понизить наиболее дорогостоящие элементы, минимально влияя на perf.
    Простая стратегия: пробуем по очереди уменьшать GPU->CPU->RAM->SSD->Motherboard->PSU->Case->Cooler
    """
    order = ["gpu","cpu","ram","ssd","motherboard","psu","case","coolers"]
    def total(b):
        return sum(int(v.get("price",0)) for v in b.values() if isinstance(v, dict))
    cur = total(build)
    if cur <= target_budget:
        return build, cur
    changed = True
    while cur > target_budget and changed:
        changed = False
        for part in order:
            cur_item = build.get(part)
            if not isinstance(cur_item, dict): continue
            cur_price = int(cur_item.get("price",0))
            candidates = components.get(part) or []
            cheaper = [c for c in candidates if c.get("price",0) < cur_price]
            if not cheaper: continue
            # choose the most expensive among cheaper (best trade-off)
            candidate = sorted(cheaper, key=lambda x: x["price"], reverse=True)[0]
            build[part] = candidate
            cur = total(build)
            changed = True
            if cur <= target_budget:
                break
    return build, cur

# -------------------------
# Budget parsing helper
# -------------------------
def parse_budget_label(budget_raw: Any) -> int:
    if isinstance(budget_raw, (int,float)):
        return int(budget_raw)
    if not isinstance(budget_raw, str):
        return 0
    s = budget_raw.strip()
    if s in BUDGET_MAP:
        return BUDGET_MAP[s][1]
    s_clean = s.replace("\u2009","").replace("\xa0","").replace(" ", "").replace("₸","")
    s_clean = re.sub(r"[–—−]", "-", s_clean)
    m = re.match(r".*?(\d+)\D+(\d+).*", s_clean)
    if m:
        try:
            a = int(m.group(1)); b = int(m.group(2))
            return max(a,b)
        except: pass
    m2 = re.match(r".*до\D*(\d+).*", s.lower())
    if m2:
        return _safe_int(m2.group(1))
    m3 = re.match(r".*?(\d+)\+.*", s_clean)
    if m3:
        return _safe_int(m3.group(1))
    m4 = re.search(r"(\d+)", s_clean)
    if m4:
        return _safe_int(m4.group(1))
    return 0

# -------------------------
# Главная функция build_pc (очень важно: интерфейс не менять)
# -------------------------
def build_pc(data: Dict[str,Any]) -> Dict[str,Any]:
    """
    Input:
      data = {"budget": label|string|int, "usage": "игры"/"работа"/"универсальный", "preferences": str (optional)}
    Output:
      {"build": final_components_dict, "total_price": int, "explain": str}
    """
    # 1) parse budget & usage
    budget = parse_budget_label(data.get("budget", 0))
    if budget <= 0:
        # fallback minimal budget
        budget = 100_000
    usage_raw = (data.get("usage") or "работа").lower()
    prefs = (data.get("preferences") or "").lower()

    # determine usage profile
    if "игр" in usage_raw or "game" in usage_raw:
        profile = USAGE_PROFILES["games"]
        preset = "gaming_low" if budget < 200_000 else ("gaming_mid" if budget < 400_000 else "gaming_high")
    elif "универс" in usage_raw or "универсал" in usage_raw:
        profile = USAGE_PROFILES["universal"]
        preset = "universal"
    else:
        profile = USAGE_PROFILES["work"]
        preset = "office"

    # 2) load components
    components = load_all_components()
    # ensure categories exist
    for cat in ("cpu","motherboard","ram","gpu","ssd","psu","case","coolers"):
        components.setdefault(cat, [])

    # 3) compute part budgets
    dist = BUDGET_DISTRIBUTION.get(preset, BUDGET_DISTRIBUTION["office"])
    part_budgets = {k: int(budget * v) for k,v in dist.items()}

    explain = []
    build = {}
    total = 0

    # 4) CPU
    cpu = pick_best(components.get("cpu",[]), part_budgets.get("cpu",0), "cpu", profile)
    build["cpu"] = cpu; total += cpu.get("price",0)
    explain.append(f"CPU chosen: {cpu.get('name')} ({cpu.get('price')}) budget part {part_budgets.get('cpu')}")

    # 5) GPU (consider integrated)
    cpu_name = cpu.get("name","").lower()
    cpu_has_integrated = bool(re.search(r"\b(apu|integrat|vega|graphics|g\d{1,2})\b", cpu_name))
    if preset == "office" or cpu_has_integrated:
        if "игр" in prefs or "gpu" in prefs:
            gpu = pick_best(components.get("gpu",[]), part_budgets.get("gpu",0), "gpu", profile)
        else:
            gpu = {"name":"Встроенная графика (integrated)","price":0}
    else:
        gpu = pick_best(components.get("gpu",[]), part_budgets.get("gpu",0), "gpu", profile)
    build["gpu"] = gpu; total += gpu.get("price",0)
    explain.append(f"GPU chosen: {gpu.get('name')} ({gpu.get('price')}) budget part {part_budgets.get('gpu')}")

    # 6) Motherboard (compatible with CPU)
    mobo = pick_best(components.get("motherboard",[]), part_budgets.get("motherboard",0), "motherboard", profile)
    # prefer socket-compatible boards if possible: try to select one from matched list
    mb_candidates = [m for m in components.get("motherboard",[]) if cpu.get("specs",{}).get("socket") and cpu.get("specs",{}).get("socket").lower() in m.get("name","").lower()]
    if mb_candidates:
        mobo = pick_best(mb_candidates, part_budgets.get("motherboard",0), "motherboard", profile)
    build["motherboard"] = mobo; total += mobo.get("price",0)
    explain.append(f"Motherboard chosen: {mobo.get('name')} ({mobo.get('price')})")

    # 7) RAM
    desired_ram = 16 if preset!="gaming_high" else 32
    ram = pick_best(components.get("ram",[]), part_budgets.get("ram",0), "ram", profile)
    # prefer capacity >= desired
    rams_with_cap = [r for r in components.get("ram",[]) if (r.get("specs",{}).get("ram_capacity") or 0) >= desired_ram]
    if rams_with_cap:
        ram = pick_best(rams_with_cap, part_budgets.get("ram",0), "ram", profile)
    build["ram"] = ram; total += ram.get("price",0)
    explain.append(f"RAM chosen: {ram.get('name')} ({ram.get('price')}) target {desired_ram}GB")

    # 8) SSD
    prefer_cap = 500 if preset.startswith("gaming") else 256
    ssd = pick_best(components.get("ssd",[]), part_budgets.get("ssd",0), "ssd", profile)
    build["ssd"]=ssd; total += ssd.get("price",0)
    explain.append(f"SSD chosen: {ssd.get('name')} ({ssd.get('price')})")

    # 9) Coolers, Case
    cool = pick_best(components.get("coolers",[]), part_budgets.get("coolers",0), "coolers", profile)
    build["coolers"]=cool; total += cool.get("price",0)
    case = pick_best(components.get("case",[]), part_budgets.get("case",0), "case", profile)
    build["case"] = case; total += case.get("price",0)
    explain.append(f"Cooler: {cool.get('name')} ({cool.get('price')}); Case: {case.get('name')} ({case.get('price')})")

    # 10) PSU
    # estimate required watt
    gpu_t = 1
    try:
        gpu_t =  detect_gpu_tier(gpu.get("name","")) if isinstance(gpu, dict) else 1
    except:
        gpu_t = 1
    gpu_power = estimate_gpu_power_by_tier(gpu_t)
    cpu_power = cpu.get("specs",{}).get("tdp") or estimate_cpu_tdp_by_name(cpu.get("name",""))
    required_watt = int(cpu_power + gpu_power + 200)
    psu = pick_best(components.get("psu",[]), part_budgets.get("psu",0), "psu", profile)
    # if psu not sufficient, try to find one with watt >= required
    psu_candidates = [p for p in components.get("psu",[]) if (p.get("specs",{}).get("psu_watt") or 0) >= required_watt or re.search(r"(\d{3,4})\s*w", p.get("name","").lower())]
    if psu_candidates:
        psu = pick_best(psu_candidates, part_budgets.get("psu",0), "psu", profile)
    build["psu"]=psu; total += psu.get("price",0)
    explain.append(f"PSU chosen: {psu.get('name')} ({psu.get('price')}) required watt ~{required_watt}")

    # 11) final check: if over budget -> degrade
    if total > budget:
        pre = total
        build, total = degrade_to_budget(build, components, budget)
        explain.append(f"Total {pre} exceeded budget {budget}. After degrade -> {total}")

    # 12) final unify ensure ints and name fields
    for k,v in build.items():
        if isinstance(v, dict):
            v["price"] = int(v.get("price",0))
            v["name"] = v.get("name","Нет данных")

    explain_text = "\n".join(explain)
    return {"build": build, "total_price": int(total), "explain": explain_text}


# -------------------------
# Small helper functions re-used above (fallbacks). These are minimal but copied here:
# -------------------------
def detect_gpu_tier(name: str) -> int:
    s = (name or "").lower()
    if "4090" in s or "4080" in s: return 5
    if "4070" in s or "3080" in s or "3070" in s: return 4
    if "4060" in s or "3060" in s or "6700" in s: return 3
    if "3060 ti" in s or "2060" in s or "1650" in s: return 2
    return 1

def estimate_gpu_power_by_tier(tier: int) -> int:
    mapping = {1:50,2:125,3:200,4:300,5:450}
    return mapping.get(tier,150)

def estimate_cpu_tdp_by_name(name:str)->int:
    s = (name or "").lower()
    if any(x in s for x in ["ryzen 9", "i9"]): return 125
    if any(x in s for x in ["ryzen 7", "i7"]): return 95
    if any(x in s for x in ["ryzen 5", "i5"]): return 65
    return 65
