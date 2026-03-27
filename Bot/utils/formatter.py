from typing import Any, Dict


# ── Человекочитаемые названия категорий ──
_NICE_NAMES: dict[str, str] = {
    "cpu":         "🖥 Процессор",
    "motherboard": "🧩 Материнская плата",
    "gpu":         "🎮 Видеокарта",
    "ram":         "💾 Оперативная память",
    "ssd":         "⚡ SSD-накопитель",
    "hdd":         "📀 HDD-накопитель",
    "psu":         "🔌 Блок питания",
    "cooler":      "❄️ Охлаждение",
    "coolers":     "❄️ Охлаждение",
    "case":        "🧱 Корпус",
}

# ── Порядок вывода ──
_ORDER = ["cpu", "motherboard", "gpu", "ram", "ssd", "hdd", "psu", "cooler", "case"]


def _fmt_price(price: Any) -> str:
    """Форматирует цену: 123456 → '123 456 ₸'."""
    try:
        p = int(price)
        return f"{p:,} ₸".replace(",", " ")
    except (ValueError, TypeError):
        return "— ₸"


def _normalize_build(result: Any) -> tuple[dict, int]:
    """
    Приводит результат build_pc к единому формату.
    Возвращает (build_dict, total_price).
    """
    if not result or not isinstance(result, dict):
        return {}, 0

    build = {k: v for k, v in result.items() if isinstance(v, dict)}

    total = 0
    for v in build.values():
        try:
            total += int(v.get("price", 0))
        except (ValueError, TypeError):
            pass

    return build, total


def format_build_message(
    result: Any,
    budget: Any = None,
    usage: str | None = None,
    prefs: str | None = None,
) -> str:
    """Форматирует результат сборки в Markdown-сообщение для Telegram."""

    build, total = _normalize_build(result)

    lines: list[str] = []

    # ── Шапка ──
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("🛒 *Ваша сборка ПК*")
    lines.append("━━━━━━━━━━━━━━━━━━━━\n")

    if budget is not None:
        lines.append(f"💰 *Бюджет:* {budget}")
    if usage:
        usage_nice = {"gaming": "🎮 Игры", "work": "🧪 Работа", "universal": "🎯 Универсальный"}
        lines.append(f"🎯 *Назначение:* {usage_nice.get(usage, usage)}")
    if prefs:
        lines.append(f"✨ *Предпочтения:* {prefs}")

    lines.append("")

    # ── Компоненты ──
    if not build:
        lines.append("🔍 Компоненты не найдены. Попробуй другой бюджет.")
        return "\n".join(lines)

    seen: set[str] = set()
    for key in _ORDER:
        if key in seen:
            continue

        item = build.get(key)
        if not item or not isinstance(item, dict):
            continue

        seen.add(key)
        # Алиасы cooler/coolers
        if key in ("cooler", "coolers"):
            seen.update({"cooler", "coolers"})

        name = item.get("name", "—")
        price = item.get("price", 0)
        nice = _NICE_NAMES.get(key, key.upper())

        lines.append(f"{nice}:")
        lines.append(f"  _{name}_")
        lines.append(f"  *{_fmt_price(price)}*")
        lines.append("")

    # Прочие категории (если вдруг есть)
    for key, item in build.items():
        if key in seen or not isinstance(item, dict):
            continue
        name = item.get("name", "—")
        price = item.get("price", 0)
        lines.append(f"{_NICE_NAMES.get(key, key)}:")
        lines.append(f"  _{name}_")
        lines.append(f"  *{_fmt_price(price)}*")
        lines.append("")

    # ── Итого ──
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"💵 *ИТОГО: {_fmt_price(total)}*")

    if budget is not None:
        try:
            b = int(budget) if isinstance(budget, (int, float)) else int("".join(c for c in str(budget) if c.isdigit()) or "0")
            if b > 0:
                saved = b - total
                if saved > 0:
                    lines.append(f"✅ Экономия: {_fmt_price(saved)}")
                elif saved == 0:
                    lines.append("✅ Точно в бюджет!")
        except (ValueError, TypeError):
            pass

    lines.append("━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines)