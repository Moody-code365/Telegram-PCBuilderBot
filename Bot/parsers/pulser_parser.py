import pandas as pd
import json
import re
from pathlib import Path

CATEGORY_MAP = {
    "100_Процессоры": "cpu.json",
    "150_Модули оперативной памяти": "ram.json",
    "170_Видеокарты": "gpu.json",
    "182_Твердотельные накопители": "ssd.json",
    "180_Жесткие диски": "hdd.json",
    "140_Материнские платы": "motherboard.json",
    "570_Блоки питания ATX": "psu.json",
    "560_Корпуса": "case.json",
    "110_Кулеры для процессоров": "coolers.json",
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "components"


def load_excel(path: str):
    return pd.read_excel(path, header=None, dtype=str)


def is_category(cell: str) -> bool:
    if not isinstance(cell, str):
        return False
    return bool(re.match(r"^\d+_", cell))


def normalize_category(cat: str) -> str:
    return cat.split("(")[0].strip()


def parse_item(row) -> dict:
    try:
        return {
            "code": row[1],             # B
            "name": row[2],             # C
            "price_retail": row[3],     # D
            "price_wholesale": row[4],  # E
            "price_reseller": row[5],   # F
            "warranty": row[6],         # G
            "status": row[7],           # H
        }
    except:
        return None


def save_category(category: str, items: list):
    for key, filename in CATEGORY_MAP.items():
        if category.startswith(key):
            out_path = DATA_DIR / filename
            break
    else:
        print(f"[WARN] Категория '{category}' не найдена — пропускаем")
        return

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=4)

    print(f"[OK] {category} → {filename} ({len(items)} items)")


def parse_xls_to_json(xls_path: str):
    df = load_excel(xls_path)

    current_category = None
    items_buffer = []

    for _, row in df.iterrows():
        first_cell = row[2]  # <<<<<< ВАЖНО! Категории в колонке C → row[2]

        if is_category(first_cell):
            print("CATEGORY FOUND:", first_cell)

            if current_category and items_buffer:
                save_category(current_category, items_buffer)
                items_buffer = []

            current_category = normalize_category(first_cell)
            continue

        if current_category:
            # строки товаров фильтруем — у товаров ВСЕГДА есть код (row[1])
            if pd.notna(row[1]):
                item = parse_item(row)
                if item:
                    items_buffer.append(item)

    if current_category and items_buffer:
        save_category(current_category, items_buffer)
