#!/usr/bin/env python3
"""
AI PC Builder — 5-шаговый конвейер подбора компонентов.

Шаг 1: Анализ рынка  → ИИ видит мин/макс/среднюю цену + кол-во позиций
                        → распределяет бюджет по категориям
Шаг 2: Выбор сборки  → фильтруем топ-5 под его бюджет
                        → ИИ выбирает лучшие компоненты
Шаг 3: Проверка      → ИИ оценивает баланс сборки (да/нет)
Шаг 4: Доработка     → если нет — даём ещё 5 альтернатив (макс 2 раза)
Шаг 5: Финал         → ИИ пишет описание → отправляем клиенту
"""

import json
import logging
import statistics
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─── Константы ───────────────────────────────────────────────────────────────

CATEGORIES = ["cpu", "motherboard", "ram", "gpu", "ssd", "psu", "coolers", "case"]

SKIP_GPU = {"GT 710", "GT 730", "GT 1030"}
SKIP_CPU = {"CELERON", "PENTIUM"}
SKIP_MB  = {"H610", "A320", "A520"}

MAX_REVISION_ROUNDS = 2

DEFAULT_WEIGHTS = {
    "gaming":    {"cpu": 0.20, "gpu": 0.35, "ram": 0.08, "motherboard": 0.10,
                  "ssd": 0.08, "psu": 0.07, "coolers": 0.06, "case": 0.06},
    "work":      {"cpu": 0.28, "gpu": 0.00, "ram": 0.15, "motherboard": 0.15,
                  "ssd": 0.15, "psu": 0.10, "coolers": 0.10, "case": 0.07},
    "universal": {"cpu": 0.23, "gpu": 0.22, "ram": 0.10, "motherboard": 0.12,
                  "ssd": 0.10, "psu": 0.09, "coolers": 0.07, "case": 0.07},
}


# ─── Утилиты ─────────────────────────────────────────────────────────────────

def escape_md(text: str) -> str:
    """Экранирует спецсимволы Telegram Markdown (не V2)."""
    return str(text).translate(str.maketrans({
        "_": "\\_", "*": "\\*", "[": "\\[", "`": "\\`",
    }))


def _price(item: dict) -> int:
    return item.get("price", 0)


def _name(item: dict) -> str:
    return item.get("name", "").upper()


def _has(text: str, tokens) -> bool:
    return any(t in text for t in tokens)


def _integrated_gpu() -> dict:
    return {"name": "Встроенная графика", "price": 0, "code": ""}


# ─── Фильтрация ──────────────────────────────────────────────────────────────

def _hard_filter(items: List[dict], category: str, preferences: dict) -> List[dict]:
    """Жёсткая фильтрация мусора и несовместимых компонентов."""
    cpu_brand = preferences.get("cpu_brand", "").upper()
    gpu_brand = preferences.get("gpu_brand", "").upper()

    result = []
    for item in items:
        n = _name(item)
        p = _price(item)

        if p < 5_000:
            continue

        if category == "cpu":
            if _has(n, SKIP_CPU):
                continue
            if cpu_brand == "INTEL" and "AMD" in n:
                continue
            if cpu_brand == "AMD" and _has(n, {"INTEL", "CORE I"}):
                continue

        elif category == "gpu":
            if _has(n, SKIP_GPU):
                continue
            if gpu_brand == "NVIDIA" and _has(n, {"RADEON", " RX "}):
                continue
            if gpu_brand in ("RADEON", "AMD") and _has(n, {"GTX", "RTX"}):
                continue

        elif category == "ram":
            if _has(n, {"4GB", "8GB", " 4 GB", " 8 GB"}):
                continue

        elif category == "ssd":
            if _has(n, {"120GB", "128GB", "240GB", "256GB", "480GB"}):
                continue

        elif category == "motherboard":
            if _has(n, SKIP_MB):
                continue

        result.append(item)

    return result


def _pick_around_price(items: List[dict], target: int, count: int = 5) -> List[dict]:
    """Выбирает count компонентов близко к целевой цене."""
    if not items:
        return []

    sorted_items = sorted(items, key=_price)
    idx   = min(range(len(sorted_items)), key=lambda i: abs(_price(sorted_items[i]) - target))
    start = max(0, idx - count // 2)
    end   = min(len(sorted_items), start + count)
    start = max(0, end - count)

    seen, result = set(), []
    for item in sorted_items[start:end]:
        key = _name(item)[:45]
        if key not in seen:
            seen.add(key)
            result.append(item)

    return result


def _pick_alternatives(
    items: List[dict], exclude_names: List[str], target: int, count: int = 5
) -> List[dict]:
    """Выбирает альтернативы, исключая уже показанные."""
    exclude_set = {n[:45].upper() for n in exclude_names}
    candidates  = [i for i in items if _name(i)[:45] not in exclude_set]
    return _pick_around_price(candidates, target, count)


# ─── Статистика рынка ────────────────────────────────────────────────────────

def _market_stats(items: List[dict]) -> dict:
    """Считает статистику цен для категории."""
    prices = [_price(i) for i in items if _price(i) > 0]
    if not prices:
        return {"count": 0, "min": 0, "max": 0, "median": 0,
                "cheap": {}, "mid": {}, "top": {}}

    prices_s = sorted(prices)

    def _short(item):
        return {"name": item["name"][:55], "price": _price(item)}

    items_s = sorted(items, key=_price)
    return {
        "count":  len(prices),
        "min":    prices_s[0],
        "max":    prices_s[-1],
        "median": int(statistics.median(prices_s)),
        "cheap":  _short(items_s[0]),
        "mid":    _short(items_s[len(items_s) // 2]),
        "top":    _short(items_s[-1]),
    }


# ─── Промпты ─────────────────────────────────────────────────────────────────

def _prompt_budget_distribution(
    budget: int, preset: str, market: dict, preferences: dict
) -> str:
    pref = []
    if preferences.get("cpu_brand"):
        pref.append(f"CPU={preferences['cpu_brand']}")
    if preferences.get("gpu_brand"):
        pref.append(f"GPU={preferences['gpu_brand']}")
    if preferences.get("need_gpu") is False:
        pref.append("GPU=не нужна")
    pref_str = f" | {', '.join(pref)}" if pref else ""

    rows = []
    for cat, s in market.items():
        if s["count"] == 0:
            rows.append(f"{cat}: нет позиций")
            continue
        rows.append(
            f"{cat}({s['count']}шт): "
            f"{s['min']//1000}k-{s['max']//1000}k₸ медиана={s['median']//1000}k | "
            f"дешевле={s['cheap'].get('name','')[:40]} {s['cheap'].get('price',0)//1000}k | "
            f"среднее={s['mid'].get('name','')[:40]} {s['mid'].get('price',0)//1000}k | "
            f"топ={s['top'].get('name','')[:40]} {s['top'].get('price',0)//1000}k"
        )

    no_gpu_note = "\nGPU=0 (встроенная графика)" if preferences.get("need_gpu") is False else ""
    priority    = "GPU 30-40% CPU 18-22%" if preset == "gaming" else "CPU 25-30% RAM+SSD 30%"
    schema      = "{" + ",".join(f'"{c}":0' for c in CATEGORIES) + "}"

    return (
        f"Эксперт по ПК. Распредели бюджет {budget//1000}k ₸ | {preset}{pref_str}\n\n"
        f"Рынок:\n" + "\n".join(rows) +
        f"\n\nПравила: сумма=бюджет±5%. {priority}. Совместимость сокетов обязательна.{no_gpu_note}\n"
        f"JSON суммы в тенге: {schema}"
    )


def _prompt_select_components(
    budget: int, preset: str, allotment: dict, options: dict, preferences: dict
) -> str:
    pref = []
    if preferences.get("cpu_brand"):
        pref.append(preferences["cpu_brand"])
    if preferences.get("gpu_brand"):
        pref.append(preferences["gpu_brand"])
    pref_str = f" ({', '.join(pref)})" if pref else ""

    budgets   = " | ".join(f"{c}:{v//1000}k" for c, v in allotment.items() if v > 0)
    opts_rows = []
    for cat, items in options.items():
        if not items:
            continue
        names = " / ".join(f"{i['name'][:50]}({_price(i)//1000}k)" for i in items)
        opts_rows.append(f"{cat}: {names}")

    schema = (
        '{"cpu":{"name":"","price":0},"motherboard":{"name":"","price":0},'
        '"ram":{"name":"","price":0},"gpu":{"name":"","price":0},'
        '"ssd":{"name":"","price":0},"psu":{"name":"","price":0},'
        '"coolers":{"name":"","price":0},"case":{"name":"","price":0}}'
    )

    return (
        f"ПК{pref_str} | {preset} | бюджет {budget//1000}k ₸\n"
        f"Бюджет по категориям: {budgets}\n\n"
        f"Выбери по 1 из каждой категории:\n" + "\n".join(opts_rows) +
        f"\n\nСовместимость: сокет CPU = сокет MB, тип RAM совместим с MB.\n"
        f"JSON: {schema}"
    )


def _prompt_check_balance(build: dict, budget: int, preset: str) -> str:
    total = sum(_price(v) for v in build.values() if v)
    rows  = " | ".join(
        f"{cat}:{comp['name'][:40]}({_price(comp)//1000}k)"
        for cat, comp in build.items() if comp and _price(comp) > 0
    )
    return (
        f"Оцени сборку {preset} {budget//1000}k ₸:\n{rows}\nИтого:{total//1000}k\n\n"
        f"Сбалансирована? CPU и GPU подходят? Нет бутылочных горлышек?\n"
        f'JSON: {{"balanced":true/false,"weak_categories":[],"reason":"кратко"}}'
    )


def _prompt_revise(
    build: dict, budget: int, preset: str,
    weak_cats: List[str], alternatives: dict
) -> str:
    current = " | ".join(
        f"{cat}:{build[cat]['name'][:40]}({_price(build[cat])//1000}k)"
        for cat in weak_cats if cat in build and build[cat]
    )
    alt_rows = []
    for cat, items in alternatives.items():
        names = " / ".join(f"{i['name'][:50]}({_price(i)//1000}k)" for i in items)
        alt_rows.append(f"{cat}: {names}")

    schema = "{" + ",".join(f'"{c}":{{"name":"","price":0}}' for c in weak_cats) + "}"

    return (
        f"Улучши слабые компоненты сборки {preset} {budget//1000}k ₸:\n"
        f"Текущие: {current}\n\nАльтернативы:\n" + "\n".join(alt_rows) +
        f"\n\nВыбери лучшую замену.\nJSON: {schema}"
    )


def _prompt_final_description(build: dict, budget: int, preset: str) -> str:
    total = sum(_price(v) for v in build.values() if v)
    rows  = "\n".join(
        f"- {cat.upper()}: {comp['name'][:60]} — {_price(comp):,} ₸"
        for cat, comp in build.items() if comp and _price(comp) > 0
    )
    return (
        f"Напиши клиенту описание сборки ПК для {preset}, бюджет {budget:,} ₸.\n\n"
        f"Сборка:\n{rows}\nИтого: {total:,} ₸\n\n"
        f"3-4 предложения: для чего подходит, почему эти компоненты, "
        f"чего ожидать от производительности.\n"
        f"Без markdown, без списков, обычный текст."
    )


# ─── Основной класс ──────────────────────────────────────────────────────────

class AIPcBuilder:
    """5-шаговый конвейер сборки ПК с ИИ."""

    def __init__(self, ai_service):
        self.ai = ai_service

    def _step1_distribute_budget(
        self, budget: int, preset: str, all_parts: dict, preferences: dict
    ) -> Optional[dict]:
        """Шаг 1: ИИ анализирует рынок и распределяет бюджет."""
        market = {}
        for cat in CATEGORIES:
            items = _hard_filter(all_parts.get(cat, []), cat, preferences)
            market[cat] = _market_stats(items)

        if preferences.get("need_gpu") is False:
            market["gpu"] = {"count": 0, "min": 0, "max": 0, "median": 0,
                             "cheap": {}, "mid": {}, "top": {}}

        prompt = _prompt_budget_distribution(budget, preset, market, preferences)
        raw    = self.ai.get_completion(prompt)
        if not raw:
            return None

        try:
            data      = json.loads(raw)
            allotment = {cat: int(data.get(cat, 0)) for cat in CATEGORIES}
            total     = sum(allotment.values())
            if total == 0:
                return None

            # Масштабируем если ИИ промахнулся по сумме
            if abs(total - budget) / budget > 0.15:
                scale     = budget / total
                allotment = {k: int(v * scale) for k, v in allotment.items()}

            logger.info(f"Шаг 1 — распределение: {allotment}")
            return allotment

        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.error(f"Шаг 1 — ошибка: {e}")
            return None

    def _step2_select_components(
        self, budget: int, preset: str, all_parts: dict,
        allotment: dict, preferences: dict,
        exclude: Optional[Dict[str, List[str]]] = None
    ) -> Optional[dict]:
        """Шаг 2: ИИ выбирает компоненты из топ-5 вариантов."""
        if preferences.get("need_gpu") is False:
            allotment["gpu"] = 0

        options = {}
        for cat in CATEGORIES:
            if allotment.get(cat, 0) == 0:
                if cat == "gpu":
                    options[cat] = [_integrated_gpu()]
                continue

            items  = _hard_filter(all_parts.get(cat, []), cat, preferences)
            target = allotment[cat]

            if exclude and cat in exclude:
                candidates = _pick_alternatives(items, exclude[cat], target, count=5)
            else:
                candidates = _pick_around_price(items, target, count=5)

            if candidates:
                options[cat] = candidates

        prompt = _prompt_select_components(budget, preset, allotment, options, preferences)
        raw    = self.ai.get_completion(prompt)
        if not raw:
            return None

        try:
            data  = json.loads(raw)
            build = {}
            for cat in CATEGORIES:
                if cat == "gpu" and preferences.get("need_gpu") is False:
                    build[cat] = _integrated_gpu()
                    continue
                comp = data.get(cat)
                if (isinstance(comp, dict)
                        and comp.get("name")
                        and isinstance(comp.get("price"), (int, float))):
                    build[cat] = {"name": comp["name"], "price": int(comp["price"]), "code": ""}
                else:
                    logger.warning(f"Шаг 2 — нет компонента {cat}: {comp}")
                    return None

            total = sum(_price(v) for v in build.values())
            logger.info(f"Шаг 2 — итого {total:,} / {budget:,} ₸")
            return build

        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Шаг 2 — ошибка: {e}")
            return None

    def _step3_check_balance(
        self, build: dict, budget: int, preset: str
    ) -> Tuple[bool, List[str], str]:
        """Шаг 3: ИИ оценивает баланс сборки."""
        prompt   = _prompt_check_balance(build, budget, preset)
        raw      = self.ai.get_completion(prompt)
        if not raw:
            return True, [], ""

        try:
            data     = json.loads(raw)
            balanced = bool(data.get("balanced", True))
            weak     = [c for c in data.get("weak_categories", []) if c in CATEGORIES]
            reason   = str(data.get("reason", ""))
            logger.info(f"Шаг 3 — balanced={balanced} weak={weak} reason={reason}")
            return balanced, weak, reason

        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Шаг 3 — ошибка: {e}")
            return True, [], ""

    def _step4_revise(
        self, build: dict, budget: int, preset: str,
        all_parts: dict, allotment: dict, preferences: dict,
        weak_cats: List[str], shown_names: Dict[str, List[str]]
    ) -> dict:
        """Шаг 4: Даём альтернативы для слабых категорий и просим заменить."""
        if not weak_cats:
            return build

        alternatives = {}
        for cat in weak_cats:
            items  = _hard_filter(all_parts.get(cat, []), cat, preferences)
            target = allotment.get(cat, budget // 8)
            alts   = _pick_alternatives(items, shown_names.get(cat, []), target, count=5)
            if alts:
                alternatives[cat] = alts
                shown_names.setdefault(cat, []).extend(i["name"] for i in alts)

        if not alternatives:
            return build

        prompt = _prompt_revise(build, budget, preset, weak_cats, alternatives)
        raw    = self.ai.get_completion(prompt)
        if not raw:
            return build

        try:
            data = json.loads(raw)
            for cat in weak_cats:
                comp = data.get(cat)
                if (isinstance(comp, dict)
                        and comp.get("name")
                        and isinstance(comp.get("price"), (int, float))):
                    build[cat] = {"name": comp["name"], "price": int(comp["price"]), "code": ""}
                    logger.info(f"Шаг 4 — заменён {cat}: {comp['name']}")

        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Шаг 4 — ошибка: {e}")

        return build

    def _step5_describe(self, build: dict, budget: int, preset: str) -> str:
        """Шаг 5: ИИ пишет финальное описание для клиента."""
        prompt = _prompt_final_description(build, budget, preset)
        text   = self.ai.get_completion(prompt, use_json_format=False) or ""
        text   = text.strip().replace("**", "").replace("##", "")
        return text[:600] if text else ""

    # ── Главный метод ────────────────────────────────────────────────────────

    def build_pc(
        self,
        budget: int,
        preset: str,
        all_parts: dict,
        preferences: Optional[dict] = None,
    ) -> Tuple[dict, bool, str]:
        """
        Запускает 5-шаговый конвейер.
        Возвращает (build, used_ai=True, explanation).
        """
        preferences = preferences or {}
        preset      = preset if preset in DEFAULT_WEIGHTS else "universal"

        logger.info(f"=== AI сборка | {preset} | {budget:,} ₸ ===")

        # Шаг 1: Распределение бюджета
        allotment = self._step1_distribute_budget(budget, preset, all_parts, preferences)
        if not allotment:
            logger.warning("Шаг 1 провалился — дефолтные веса")
            weights   = DEFAULT_WEIGHTS[preset]
            allotment = {cat: int(budget * w) for cat, w in weights.items()}

        # Шаг 2: Первичный выбор
        shown_names: Dict[str, List[str]] = {}

        build = self._step2_select_components(
            budget, preset, all_parts, allotment, preferences
        )
        if not build:
            logger.error("Шаг 2 провалился")
            return {}, False, "Ошибка при подборе компонентов."

        for cat, comp in build.items():
            shown_names.setdefault(cat, []).append(comp.get("name", ""))

        # Шаги 3-4: Проверка и доработка (макс 2 раза)
        for revision in range(MAX_REVISION_ROUNDS):
            balanced, weak_cats, reason = self._step3_check_balance(build, budget, preset)

            if balanced:
                logger.info(f"Сборка сбалансирована (итерация {revision + 1})")
                break

            logger.info(f"Несбалансировано: {weak_cats} — {reason}")
            build = self._step4_revise(
                build, budget, preset, all_parts,
                allotment, preferences, weak_cats, shown_names
            )

        # Шаг 5: Финальное описание
        explanation = self._step5_describe(build, budget, preset)

        total = sum(_price(v) for v in build.values())
        logger.info(f"=== Готово | {total:,} ₸ ===")

        return build, True, explanation


# ─── Фабрика и точка входа ────────────────────────────────────────────────────

def get_ai_builder() -> Optional[AIPcBuilder]:
    try:
        from Bot.config.ai_config import ENABLE_AI
        from Bot.services.ai_service import AIService

        if not ENABLE_AI:
            return None
        svc = AIService()
        if svc.is_available():
            return AIPcBuilder(ai_service=svc)

    except Exception as e:
        logger.error(f"Не удалось создать AI builder: {e}")

    return None


def build_pc_with_ai(
    budget: int,
    preset: str,
    all_parts: dict,
    preferences: Optional[dict] = None,
    enable_ai: bool = True,
) -> Tuple[dict, bool, str]:
    """
    Точка входа для хендлеров.

    Args:
        budget      — бюджет в тенге
        preset      — "gaming" | "work" | "universal"
        all_parts   — результат load_components()
        preferences — {"cpu_brand": "AMD", "gpu_brand": "NVIDIA", "need_gpu": bool}
        enable_ai   — использовать ли ИИ

    Returns:
        (build, used_ai, explanation)
        build: {category: {"name": str, "price": int, "code": str}}
    """
    if enable_ai:
        builder = get_ai_builder()
        if builder:
            try:
                return builder.build_pc(budget, preset, all_parts, preferences)
            except Exception as e:
                logger.error(f"AI конвейер упал: {e}", exc_info=True)

    logger.info("Fallback: стандартный алгоритм")
    try:
        from Bot.services.pc_builder import build_pc as std_build
        return std_build(budget, preset, all_parts), False, "Сборка по стандартному алгоритму."
    except Exception as e:
        logger.error(f"Стандартный алгоритм упал: {e}")
        return {}, False, "Ошибка при сборке ПК."