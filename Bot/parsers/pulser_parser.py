# Bot/parsers/pulser_parser.py
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


def _safe_int(v):
    try:
        if v is None: return 0
        s = str(v).strip().replace("\xa0", "").replace(" ", "").replace(",", "")
        if s == "" or not any(ch.isdigit() for ch in s): return 0
        filtered = "".join(ch for ch in s if ch.isdigit() or ch == "-")
        return int(filtered) if filtered else 0
    except:
        return 0


def load_excel(path: str):
    return pd.read_excel(path, header=None, dtype=str)


def is_category(cell: str) -> bool:
    if not isinstance(cell, str):
        return False
    return bool(re.match(r"^\d+_", cell))


def normalize_category(cat: str) -> str:
    return cat.split("(")[0].strip()


def _clean_name(name: str) -> str:
    if not isinstance(name, str):
        return str(name or "")
    # remove urls, repeated spaces, control chars
    name = re.sub(r"http\S+", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _is_bad_name(name: str) -> bool:
    if not name: return True
    low = name.lower()
    # строки вида "Память для серверов смотрите в разделе..."
    if "смотрите в разделе" in low or "для серверов" in low or "сервер" in low and "серверные" in low:
        return True
    if "http" in low or "http:" in low:
        return True
    # убрать явно б/у позиции
    if "б/у" in low or "used" in low:
        return True
    # любой короткий мусор
    if len(low) < 3:
        return True
    return False


def parse_item(row) -> dict:
    try:
        code = row[1]
        raw_name = row[2]
        name = _clean_name(raw_name)
        price_retail = _safe_int(row[3])
        price_wholesale = _safe_int(row[4])
        price_reseller = _safe_int(row[5])
        warranty = row[6] if not pd.isna(row[6]) else ""
        status = row[7] if not pd.isna(row[7]) else ""

        # Если в названии есть подсказка "смотрите в разделе..." или url — считаем мусором
        if _is_bad_name(name):
            return None

        # выберем приоритет цены: reseller -> retail -> wholesale
        price = price_reseller or price_retail or price_wholesale or 0
        if price == 0:
            # если нет цены — пропускаем (можно включить, если нужно)
            return None

        return {
            "code": str(code).strip() if not pd.isna(code) else "",
            "name": name,
            "price_retail": price_retail,
            "price_wholesale": price_wholesale,
            "price_reseller": price_reseller,
            "price": price,
            "warranty": warranty,
            "status": status
        }
    except Exception:
        return None


def save_category(category: str, items: list):
    for key, filename in CATEGORY_MAP.items():
        if category.startswith(key):
            out_path = DATA_DIR / filename
            break
    else:
        print(f"[WARN] Категория '{category}' не найдена — пропускаем")
        return

    # сохраняем список объектов
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=4)
    print(f"[OK] {category} → {filename} ({len(items)} items)")


def parse_xls_to_json(xls_path: str):
    df = load_excel(xls_path)

    current_category = None
    items_buffer = []

    for _, row in df.iterrows():
        first_cell = row[2]  # категории в колонке C

        if is_category(first_cell):
            print("CATEGORY FOUND:", first_cell)
            if current_category and items_buffer:
                save_category(current_category, items_buffer)
                items_buffer = []
            current_category = normalize_category(first_cell)
            continue

        if current_category:
            # товар — есть код в колонке B (row[1]) и имя в C (row[2])
            if pd.notna(row[1]) and pd.notna(row[2]):
                item = parse_item(row)
                if item:
                    items_buffer.append(item)

    if current_category and items_buffer:
        save_category(current_category, items_buffer)
