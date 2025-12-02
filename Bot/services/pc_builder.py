import json
import os
from typing import Dict, Any, List

COMPONENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "components")


def _safe_int(v):
    """Попытаться привести к int, иначе вернуть 0."""
    try:
        if v is None:
            return 0
        # если уже число
        if isinstance(v, (int, float)):
            return int(v)
        # убрать пробелы, пробивные символы, точки тысяч, запятые
        s = str(v).strip().replace("\xa0", "").replace(" ", "").replace(",", "")
        # если пусто или non-digit
        if s == "" or not any(ch.isdigit() for ch in s):
            return 0
        # оставим только цифры (и минус)
        filtered = "".join(ch for ch in s if ch.isdigit() or ch == "-")
        return int(filtered) if filtered else 0
    except Exception:
        return 0


def _normalize_item(raw: dict) -> dict:
    """
    Вход: произвольный dict, полученный из JSON (наш парсер).
    Выход: {'name': str, 'price': int}
    Порядок источников цены: price -> price_reseller -> price_wholesale -> price_retail -> price_opt -> last numeric field
    """
    if not isinstance(raw, dict):
        return {"name": str(raw), "price": 0}

    # Популярные поля для имени
    name = raw.get("name") or raw.get("title") or raw.get("product") or raw.get("Наименование") or ""

    # Популярные поля для цены (в порядке приоритета)
    for key in ("price", "price_reseller", "price_wholesale", "price_retail", "price_opt", "price_rrp"):
        if key in raw and raw[key] not in (None, ""):
            return {"name": name, "price": _safe_int(raw[key])}

    # Если явных полей нет — пробуем найти первое числовое поле
    for k, v in raw.items():
        if k.lower().find("price") != -1 and v not in (None, ""):
            return {"name": name, "price": _safe_int(v)}

    # Иначе ищем любое числовое значение в словаре
    for v in raw.values():
        if isinstance(v, (int, float)) or (isinstance(v, str) and any(ch.isdigit() for ch in v)):
            return {"name": name, "price": _safe_int(v)}

    # fallback
    return {"name": name, "price": 0}


def load_all_components() -> Dict[str, List[dict]]:
    """
    Загружает все json-файлы из Bot/data/components и нормализует элементы.
    Возвращает словарь: ключ = имя файла без .json, значение = список элементов {'name','price'}.
    """
    base_path = COMPONENTS_DIR
    result = {}
    if not os.path.isdir(base_path):
        return result

    for fn in os.listdir(base_path):
        if not fn.endswith(".json"):
            continue
        key = fn[:-5]  # имя файла без .json
        path = os.path.join(base_path, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            result[key] = []
            continue

        normalized = []
        # Если файл — словарь {code: {...}}, поддержим и этот формат
        if isinstance(raw, dict):
            for sub in raw.values():
                normalized.append(_normalize_item(sub))
        elif isinstance(raw, list):
            for sub in raw:
                normalized.append(_normalize_item(sub))
        else:
            # неизвестный формат
            result[key] = []
            continue

        # удалить дубликаты по name (если нужно) и отсортировать по цене
        # (сначала убираем пустые имена)
        normalized = [x for x in normalized if x["name"]]
        normalized = sorted(normalized, key=lambda i: i["price"])
        result[key] = normalized

    return result


# ------------------ пресеты (тревиально) ------------------
BUILD_PRESETS = {
    "office": {
        "cpu": "cpu",
        "gpu": "gpu",
        "ram": "ram",
        "ssd": "ssd",
        "psu": "psu",
    },
    "gaming_low": {
        "cpu": "cpu",
        "gpu": "gpu",
        "ram": "ram",
        "ssd": "ssd",
        "psu": "psu",
    },
    "gaming_mid": {
        "cpu": "cpu",
        "gpu": "gpu",
        "ram": "ram",
        "ssd": "ssd",
        "psu": "psu",
    },
    "gaming_high": {
        "cpu": "cpu",
        "gpu": "gpu",
        "ram": "ram",
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


def pick_preset(budget: int, usage: str) -> Dict[str, str]:
    if usage == "работа":
        return BUILD_PRESETS["office"]
    if usage == "игры":
        if budget < 200_000:
            return BUILD_PRESETS["gaming_low"]
        elif budget < 400_000:
            return BUILD_PRESETS["gaming_mid"]
        else:
            return BUILD_PRESETS["gaming_high"]
    if usage == "универсальный":
        if budget < 300_000:
            return BUILD_PRESETS["gaming_low"]
        else:
            return BUILD_PRESETS["gaming_mid"]
    return BUILD_PRESETS["office"]


def pick_best_component(components: Dict[str, list], category: str, part_budget: int = None) -> dict:
    """
    components — словарь: key -> список элементов {'name','price',...}
    category — имя файла без .json (например 'cpu','gpu' и т.д.)
    part_budget — если указано, выбираем наиболее подходящий <= part_budget (максимум из подходящих).
    """
    items = components.get(category, [])
    if not items:
        return {"name": "Нет данных", "price": 0}

    # гарантируем, что у каждого есть поле price (нормализовано парсером)
    items = [i for i in items if isinstance(i.get("price", None), (int, float)) and i["price"] > 0]
    if not items:
        return {"name": "Нет данных", "price": 0}

    # если нет ограничения — просто самый дешёвый подходящий (или можно выбрать середину)
    if not part_budget or part_budget <= 0:
        return items[0]

    # фильтруем все, <= part_budget
    under = [i for i in items if i["price"] <= part_budget]
    if under:
        # берём максимально дорогой из тех, что укладываются — ближе к бюджету
        best = sorted(under, key=lambda x: x["price"], reverse=True)[0]
        return best

    # если ничего не попало под бюджет — берём самый дешёвый (минимум)
    return items[0]

BUDGET_DISTRIBUTION = {
    # офис: cpu 30%, ram 20%, ssd 15%, psu 10%, gpu 0% (встроенная)
    "office": {"cpu": 0.30, "ram": 0.20, "ssd": 0.15, "psu": 0.10, "gpu": 0.00},
    "gaming_low": {"cpu": 0.25, "gpu": 0.35, "ram": 0.15, "ssd": 0.15, "psu": 0.10},
    "gaming_mid": {"cpu": 0.25, "gpu": 0.40, "ram": 0.15, "ssd": 0.10, "psu": 0.10},
    "gaming_high": {"cpu": 0.30, "gpu": 0.45, "ram": 0.10, "ssd": 0.05, "psu": 0.10},
}


def build_pc(data: Dict[str, Any]) -> Dict[str, Any]:
    # budget — число (мы используем normalize_budget как раньше)
    budget = normalize_budget(data.get("budget", 0))
    usage = data.get("usage", "работа")
    preset = pick_preset(budget, usage)  # возвращает mapping part->category (например 'cpu'->'cpu')
    components = load_all_components()    # функция из текущего pc_builder.py, которая нормализует данные

    # определяем ключ пресета (office / gaming_low и т.д.) для распределения
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

    dist = BUDGET_DISTRIBUTION.get(preset_key, BUDGET_DISTRIBUTION["office"])

    final = {}
    total = 0

    for part, cat in preset.items():
        # рассчитать часть бюджета (целое)
        share = int(budget * dist.get(part, 0))
        comp = pick_best_component(components, cat, part_budget=share)
        final[part] = comp
        total += comp.get("price", 0)

    return {"build": final, "total_price": total}
