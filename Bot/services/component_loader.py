import json
import os
import re

COMPONENT_TYPES = {
    "cpu": "cpu",
    "gpu": "gpu",
    "ram": "ram",
    "motherboard": "motherboard",
    "psu": "psu",
    "ssd": "ssd",
    "hdd": "hdd",
    "case": "case",
    "coolers": "cooler",
}

# Мусор, который НИКОГДА нельзя считать комплектующими
BANNED_KEYWORDS = [
    "holder", "stand", "bracket", " крепёж", "крепеж", "mount",
    "adapter", "pole", "frame", "extension", "plate", ""
]


def is_trash(item_name: str) -> bool:
    """
    Отбраковка аксессуаров и мусорных товаров.
    """
    name = item_name.lower()

    for word in BANNED_KEYWORDS:
        if word in name:
            return True

    # Дополнительные фильтры по форм-фактору RAM
    if "so-dimm" in name:
        return True

    return False


def normalize_item(item: dict, comp_type: str) -> dict:
    """
    Приводим все данные к чистой структуре.
    """
    clean = {
        "type": comp_type,
        "name": item.get("name", "").strip(),
        "price": int(item.get("price", 0) or 0),
    }

    # CPU
    if comp_type == "cpu":
        clean["socket"] = item.get("socket")
        clean["tdp"] = int(item.get("tdp", 65))
        clean["cores"] = int(item.get("cores", 0))
        clean["threads"] = int(item.get("threads", 0))

    # Motherboard
    if comp_type == "motherboard":
        clean["socket"] = item.get("socket")
        clean["ddr"] = item.get("ddr", "").upper()

    # RAM
    if comp_type == "ram":
        clean["ddr"] = item.get("ddr", "").upper()
        clean["size"] = int(item.get("size", 0))
        clean["mhz"] = int(item.get("mhz", 0))

    # GPU
    if comp_type == "gpu":
        clean["vram"] = int(item.get("vram", 0))
        clean["power"] = int(item.get("power", 120))

    # PSU
    if comp_type == "psu":
        clean["watt"] = int(item.get("watt", 0))

    # SSD / HDD
    if comp_type in ("ssd", "hdd"):
        clean["capacity"] = int(item.get("capacity", 0))

    return clean


def load_components(components_path="Bot/data/components"):
    """
    Загружает ВСЕ компоненты, полностью исключая мусор.
    """
    result = {
        "cpu": [],
        "gpu": [],
        "ram": [],
        "motherboard": [],
        "psu": [],
        "ssd": [],
        "hdd": [],
        "cooler": [],
        "case": []
    }

    for filename in os.listdir(components_path):
        if not filename.endswith(".json"):
            continue

        comp_key = filename.replace(".json", "")
        comp_type = COMPONENT_TYPES.get(comp_key)

        if comp_type is None:
            continue

        full_path = os.path.join(components_path, filename)

        with open(full_path, "r", encoding="utf-8") as f:
            items = json.load(f)

        for raw_item in items:
            name = raw_item.get("name", "").lower()

            # Отбрасываем мусор
            if is_trash(name):
                continue

            item = normalize_item(raw_item, comp_type)
            result[comp_type].append(item)

    return result
