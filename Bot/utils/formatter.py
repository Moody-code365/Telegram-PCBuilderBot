from typing import Dict, Any


def _human_name(key: str) -> str:
    nice = {
        "cpu": "🖥️ Процессор (CPU)",
        "gpu": "🎮 Видеокарта (GPU)",
        "ram": "💾 Оперативная память (RAM)",
        "ssd": "⚡ SSD-накопитель",
        "hdd": "📀 HDD",
        "psu": "🔌 Блок питания (PSU)",
        "motherboard": "🧩 Материнская плата",
        "case": "🧱 Корпус",
        "coolers": "🌀 Кулер / Система охлаждения",
    }
    return nice.get(key, key.capitalize())


def _fmt_price(p) -> str:
    try:
        p = int(p)
        return f"{p:,} ₸".replace(",", " ")
    except Exception:
        return "—"


def normalize_result(result: Any):
    """
    Поддерживает разные форматы:
     - {'build': {...}, 'total_price': 123}
     - {'cpu': {...}, 'gpu': {...}, ...}
     - None / {}
    Возвращает (build_dict, total_price:int)
    """
    if not result:
        return {}, 0

    if isinstance(result, dict) and "build" in result and "total_price" in result:
        build = result.get("build") or {}
        total = result.get("total_price") or 0
        return build, int(total)

    # if dict with components directly
    if isinstance(result, dict):
        # try to detect numbers inside -> assume it's total_price or something else
        # build elements should be dicts, so keep only those
        build = {k: v for k, v in result.items() if isinstance(v, dict)}
        # try to find a total_price key if exists
        total = result.get("total_price") or result.get("total") or 0
        # if total is 0, compute from items
        if not total:
            s = 0
            for v in build.values():
                price = None
                if isinstance(v, dict):
                    price = v.get("price") or v.get("price_retail") or v.get("price_reseller")
                try:
                    s += int(price or 0)
                except:
                    continue
            total = s
        return build, int(total)

    return {}, 0


def format_build_message(result: Any, budget: Any = None, usage: str = None, prefs: str = None) -> str:
    """
    Возвращает готовый к отправке Markdown-текст.
    Параметры:
      - result: то, что возвращает build_pc
      - budget/usage/prefs: дополнительные поля для шапки (можно передать None)
    """
    build, total = normalize_result(result)

    lines = []
    # header
    header = "🧩 *Ваша итоговая сборка:*\n"
    if budget is not None:
        header = f"💸 *Бюджет:* {budget}\n" + header
    if usage:
        header = f"🎯 *Назначение:* {usage}\n" + header
    if prefs:
        header = f"✨ *Предпочтения:* {prefs}\n\n" + header
    lines.append(header)

    if not build:
        lines.append("🔍 *Компоненты не найдены или не корректны.*\n")
        lines.append(f"💰 *Итого:* {_fmt_price(total)}")
        return "\n".join(lines)

    # body: по порядку — удобный порядок
    order = ["cpu", "motherboard", "gpu", "ram", "ssd", "hdd", "psu", "coolers", "case"]
    for key in order:
        item = build.get(key)
        if not item or not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("title") or "Не указано"
        # цена — нормализуем
        price = item.get("price") or item.get("price_retail") or item.get("price_reseller") or 0
        lines.append(f"{_human_name(key)}:\n• {name}\n• Цена: *{_fmt_price(price)}*\n")

    # если есть другие ключи в build, покажем их тоже
    extras = [k for k in build.keys() if k not in order]
    for k in extras:
        item = build.get(k)
        if not item or not isinstance(item, dict):
            continue
        name = item.get("name") or "Не указано"
        price = item.get("price") or 0
        lines.append(f"{_human_name(k)}:\n• {name}\n• Цена: *{_fmt_price(price)}*\n")

    lines.append(f"💰 *Итого:* *{_fmt_price(total)}*")

    return "\n".join(lines)
