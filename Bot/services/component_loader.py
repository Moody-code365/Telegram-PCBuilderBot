# Bot/services/component_loader.py
# Component loader + lightweight feature extractor for Pulser-like JSONs.
# Purpose: normalize raw JSON entries into consistent Component dicts.

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

COMPONENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "components")

# categories expected (file names without .json)
CATEGORIES = {"cpu", "gpu", "ram", "motherboard", "psu", "ssd", "hdd", "case", "coolers"}

# keywords that indicate the item is NOT a real component (accessory / mount / bracket / holder)
TRASH_KEYWORDS = [
    "holder", "bracket", "mount", "pole", "stand", "frame", "plate",
    "крепеж", "крепёж", "кронштейн", "держатель", "переходник", "adapter",
    "holder", "rack", "panel", "Уц.", "серверн", "Cable", "райзер", "уц", "Уц", "cable"
]

def _safe_int(v: Any) -> int:
    try:
        if v is None: return 0
        if isinstance(v, bool): return 0
        if isinstance(v, (int, float)): return int(v)
        s = str(v)
        s = s.replace("\u2009","").replace("\xa0","").replace(" ", "").replace(",", "").replace("₸","")
        s = re.sub(r"[^\d\-]", "", s)
        return int(s) if s else 0
    except Exception:
        return 0

def _clean_name(n: Any) -> str:
    if n is None: return ""
    s = str(n)
    s = re.sub(r"http\S+", "", s)       # remove urls
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _is_trash_name(name: str) -> bool:
    if not name:
        return True
    name_l = name.lower()
    for kw in TRASH_KEYWORDS:
        if kw in name_l:
            return True
    # small heuristic: if name mentions "so-dimm" — likely laptop RAM (we filter desktop SO-DIMM out)
    if "so-dimm" in name_l or "so-dimm" in name_l.replace(" ", "-"):
        return True
    return False

# ----- Feature extractors -----
def extract_cpu_specs(name: str) -> Dict[str, Any]:
    s = name.lower()
    specs = {}
    # socket
    if "am5" in s: specs["socket"] = "AM5"
    elif "am4" in s: specs["socket"] = "AM4"
    elif re.search(r"\blga\s*1700\b", s) or "1700" in s: specs["socket"] = "LGA1700"
    elif re.search(r"\b(lga\s*1200|1200)\b", s): specs["socket"] = "LGA1200"
    # tdp (try find number + W)
    m = re.search(r"(\d{2,3})\s*w", s)
    if m: specs["tdp"] = int(m.group(1))
    # cores/threads (basic heuristics)
    m2 = re.search(r"(\d+)c\/(\d+)t", s)
    if m2:
        specs["cores"] = int(m2.group(1)); specs["threads"] = int(m2.group(2))
    # fallback try single number that looks like model
    return specs

def extract_mobo_specs(name: str) -> Dict[str, Any]:
    s = name.lower()
    specs = {}
    if "am5" in s: specs["socket"] = "AM5"
    elif "am4" in s: specs["socket"] = "AM4"
    elif "lga1700" in s or "1700" in s: specs["socket"] = "LGA1700"
    # ddr
    m = re.search(r"(ddr[345])", s)
    if m: specs["ram_type"] = m.group(1).upper()
    # form factor
    if "matx" in s or "m-atx" in s or "micro" in s: specs["formfactor"] = "mATX"
    elif "atx" in s: specs["formfactor"] = "ATX"
    return specs

def extract_ram_specs(name: str) -> Dict[str, Any]:
    s = name.lower()
    specs = {}
    # ddr
    m = re.search(r"(ddr[345])", s)
    if m: specs["ddr"] = m.group(1).upper()
    # capacity: either "24 gb" or "2x8" patterns
    m2 = re.search(r"(\d{1,3})\s*gb", s)
    if m2: specs["capacity_gb"] = int(m2.group(1))
    m3 = re.search(r"(\d+)\s*[xх]\s*(\d{1,3})\s*gb", s)
    if m3:
        try:
            specs["capacity_gb"] = int(m3.group(1)) * int(m3.group(2))
        except: pass
    # mhz
    m4 = re.search(r"(\d{3,5})\s*mhz", s)
    if m4: specs["mhz"] = int(m4.group(1))
    return specs

def extract_gpu_specs(name: str) -> Dict[str, Any]:
    s = name.lower()
    specs = {}

    # VRAM
    m = re.search(r"(\d{1,3})\s*gb", s)
    if m:
        specs["vram_gb"] = int(m.group(1))

    # GPU series: RTX / GTX / RX
    m2 = re.search(r"\b(rtx|gtx|rx)\s*([0-9]{3,4})\b", s)
    if m2:
        specs["gpu_series"] = m2.group(1).upper() + " " + m2.group(2)

    # GDDR type (GDDR3/5/6/7)
    m3 = re.search(r"gddr(\d)", s)
    if m3:
        specs["gddr"] = int(m3.group(1))

    return specs

def extract_psu_specs(name: str) -> Dict[str, Any]:
    s = name.lower()
    specs = {}
    m = re.search(r"(\d{3,4})\s*w", s)
    if m: specs["watt"] = int(m.group(1))
    return specs

def extract_ssd_specs(name: str) -> Dict[str, Any]:
    s = name.lower()
    specs = {}
    m = re.search(r"(\d{2,4})\s*gb", s)
    if m:
        specs["capacity_gb"] = int(m.group(1))
    if "nvme" in s:
        specs["interface"] = "NVMe"
    elif "sata" in s:
        specs["interface"] = "SATA"
    return specs

def extract_cooler_specs(name: str) -> Dict[str, Any]:
    # Detect if cooler is water cooling
    water_keywords = [
        "aio", "water", "liquid", "lss", "hydro",
        "водян", "жидк", "сво"
    ]
    lower_name = name.lower()
    is_water = any(k in lower_name for k in water_keywords)

    # Extract TDP if present
    tdp_match = re.search(r"(\d+)\s*W", name, re.IGNORECASE)
    tdp = int(tdp_match.group(1)) if tdp_match else None

    return {
        "tdp": tdp,
        "water": is_water
    }


# ----- Normalizer for a raw item -----
def normalize_raw_item(raw: Dict[str, Any], category: str) -> Optional[Dict[str, Any]]:
    """
    Returns normalized component dict or None if invalid/trash.
    Normalized format:
      {
        "name": str,
        "price": int,
        "category": category,
        "specs": {...},
        "_raw": raw
      }
    """
    name = _clean_name(raw.get("name") or raw.get("title") or raw.get("Наименование") or "")
    if not name:
        return None
    # drop trash by name heuristics
    if _is_trash_name(name):
        return None

    # price pick priority: price -> price_reseller -> price_wholesale -> ...
    price = 0
    for pk in ("price", "price_retail", "price_reseller", "price_wholesale", "price_opt"):
        if pk in raw and raw.get(pk) not in (None, ""):
            price = _safe_int(raw.get(pk))
            break
    if price <= 0:
        # fallback search any numeric field
        for v in raw.values():
            if isinstance(v, (int, float)) or (isinstance(v, str) and re.search(r"\d", v)):
                price = _safe_int(v)
                if price > 0:
                    break
    if price <= 0:
        return None

    # extract specs by category
    extractor_map = {
        "cpu": extract_cpu_specs,
        "motherboard": extract_mobo_specs,
        "ram": extract_ram_specs,
        "gpu": extract_gpu_specs,
        "psu": extract_psu_specs,
        "ssd": extract_ssd_specs,
        "hdd": extract_ssd_specs,
        "case": lambda _: {},
        "coolers": extract_cooler_specs
    }
    extractor = extractor_map.get(category, lambda _: {})
    specs = extractor(name)

    normalized = {
        "name": name,
        "price": int(price),
        "category": category,
        "specs": specs,
        "_raw": raw
    }
    return normalized

# ----- Main loader function -----
def load_components(path: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    if path is None:
        path = COMPONENTS_DIR
    out: Dict[str, List[Dict[str, Any]]] = {c: [] for c in CATEGORIES}
    p = Path(path)
    if not p.exists() or not p.is_dir():
        raise FileNotFoundError(f"components dir not found: {path}")

    for f in p.glob("*.json"):
        key = f.stem.lower()
        if key not in CATEGORIES:
            # skip unknown files but you may extend mapping if needed
            continue
        try:
            raw = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue

        # raw can be list or dict
        iterable = raw if isinstance(raw, list) else (list(raw.values()) if isinstance(raw, dict) else [])
        for item in iterable:
            norm = normalize_raw_item(item, key)
            if norm:
                out[key].append(norm)

    # sort each category by price ascending
    for k in out:
        out[k] = sorted(out[k], key=lambda x: x["price"])
    return out

# -----------------------------
# quick test helper (callable)
# -----------------------------
if __name__ == "__main__":
    comps = load_components()
    for cat, items in comps.items():
        print(f"=== {cat} ({len(items)}) ===")
        for i in items[:100]:
            print(i["name"], "-", i["price"], "-", i.get("specs"))
