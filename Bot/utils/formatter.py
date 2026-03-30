from typing import Any

_NICE_NAMES: dict[str, str] = {
    "cpu":         "🖥 Процессор",
    "motherboard": "🧩 Мат. плата",
    "gpu":         "🎮 Видеокарта",
    "ram":         "💾 Оперативка",
    "ssd":         "⚡ SSD",
    "hdd":         "📀 HDD",
    "psu":         "🔌 Блок питания",
    "cooler":      "❄️ Охлаждение",
    "coolers":     "❄️ Охлаждение",
    "case":        "🧱 Корпус",
}

_ORDER = ["cpu", "motherboard", "gpu", "ram", "ssd", "hdd", "psu", "cooler", "case"]


def _fmt(price: Any) -> str:
    try:
        return f"{int(price):,} ₸".replace(",", " ")
    except (ValueError, TypeError):
        return "— ₸"


def format_build_message(
    result: Any,
    budget: int = 0,
    usage: str | None = None,
) -> str:
    if not result or not isinstance(result, dict):
        return "❌ Не удалось подобрать сборку."

    build = {k: v for k, v in result.items() if isinstance(v, dict)}
    total = sum(int(v.get("price", 0)) for v in build.values())

    usage_nice = {"gaming": "🎮 Игры", "work": "💼 Работа", "universal": "🔄 Универсальный"}
    lines: list[str] = []

    # ── Шапка ──
    lines.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
    lines.append("┃    🛒 *СБОРКА ПК*    ┃")
    lines.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
    lines.append("")

    if budget:
        lines.append(f"💰 Бюджет: *{_fmt(budget)}*")
    if usage:
        lines.append(f"🎯 Назначение: *{usage_nice.get(usage, usage)}*")
    lines.append("")

    # ── Компоненты ──
    if not build:
        lines.append("Компоненты не найдены.")
        return "\n".join(lines)

    seen: set[str] = set()
    for key in _ORDER:
        if key in seen:
            continue
        item = build.get(key)
        if not item or not isinstance(item, dict):
            continue
        seen.add(key)
        if key in ("cooler", "coolers"):
            seen.update({"cooler", "coolers"})

        nice = _NICE_NAMES.get(key, key)
        name = item.get("name", "—")
        price = item.get("price", 0)

        lines.append(f"*{nice}*")
        lines.append(f"  _{name}_")
        lines.append(f"  💵 {_fmt(price)}")
        lines.append("")

    # ── Итого ──
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"💵 *Итого: {_fmt(total)}*")

    if budget and budget > 0:
        remaining = budget - total
        if remaining > 0:
            lines.append(f"✅ Остаток: {_fmt(remaining)}")
        elif remaining == 0:
            lines.append("✅ Точно в бюджет!")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")

    # ── Дисклеймер ──
    lines.append("")
    lines.append(
        "ℹ️ _Это автоматический подбор. "
        "Любую комплектующую можно заменить "
        "на другую — обратись к менеджеру для уточнения._"
    )

    return "\n".join(lines)