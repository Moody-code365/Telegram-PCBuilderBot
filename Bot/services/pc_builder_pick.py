# services/pc_builder_cpu.py

from typing import List, Dict


def pick_cpu(cpus: List[Dict], budget: int) -> Dict | None:
    """
    Выбирает оптимальный CPU в рамках бюджета.
    Критерии:
        1) Цена <= budget
        2) Больше ядер лучше
        3) Если равные — больше потоков
        4) Если равные — выше частота (если есть поле 'mhz')
        5) Если равные — цена ближе к 80–90% бюджета (не слишком дёшево и не топ)
    """

    candidates = [c for c in cpus if c["price"] <= budget]
    if not candidates:
        return None

    def score(cpu):
        attrs = cpu.get("attrs", {})
        cores = attrs.get("cores", 0)
        threads = attrs.get("threads", 0)
        freq = attrs.get("mhz", 0)
        price = cpu["price"]

        # Насколько хорошо цена вписывается в "идеал" (~85% бюджета)
        target_price = budget * 0.85
        price_penalty = abs(target_price - price)

        return (
            cores,
            threads,
            freq,
            -price_penalty  # ближе к целевой цене → лучше
        )

    candidates.sort(key=score, reverse=True)
    return candidates[0]



def pick_motherboard(mobos: List[Dict], cpu: Dict, max_budget: int | None = None) -> Dict | None:
    """
    Выбирает материнскую плату:
    - совместимую по сокету с CPU
    - с базовой оценкой качества (не шлак)
    - учитывает частичный бюджет, если он указан
    """

    if not cpu:
        return None

    cpu_socket = cpu["attrs"].get("socket")
    if not cpu_socket:
        return None

    # 1) Совместимость по сокету
    candidates = [
        m for m in mobos
        if m["attrs"].get("socket") == cpu_socket
    ]
    if not candidates:
        return None

    # 2) Отбрасываем слишком дешёвые платы (условно хлам)
    #    Материнка не должна стоить подозрительно дешево относительно CPU
    min_ok_price = cpu["price"] * 0.25
    candidates = [m for m in candidates if m["price"] >= min_ok_price]

    if not candidates:
        return None

    # 3) Учитываем бюджет сборки (если указан)
    if max_budget:
        candidates = [m for m in candidates if m["price"] <= max_budget]
        if not candidates:
            return None

    # 4) Сортировка по качеству:
    #   - ATX > mATX > ITX
    #   - Цена как индикатор качества
    def score(m):
        rating = 0

        form = m["attrs"].get("formfactor", "").lower()
        if form == "atx":
            rating += 3
        elif form == "matx":
            rating += 2
        elif form == "itx":
            rating += 1

        rating += m["price"] / 10000  # цена как мягкий показатель качества

        return rating

    candidates.sort(key=lambda m: score(m), reverse=True)

    return candidates[0]


def pick_ram(rams: List[Dict], mobo: Dict, budget_left: int) -> Dict | None:
    """
    Выбирает лучшую RAM в рамках бюджета.
    Критерии:
        1) Совместимость по типу RAM
        2) Цена <= бюджет
        3) Больше capacity_gb — лучше
        4) При равных — больше MHz
        5) При равных — дешевле
    """

    if not mobo:
        return None

    mobo_ram_type = mobo["attrs"].get("ram_type")
    if not mobo_ram_type:
        return None

    # Совместимые и вписывающиеся в бюджет
    candidates = [
        r for r in rams
        if r["attrs"].get("ddr") == mobo_ram_type and r["price"] <= budget_left
    ]

    if not candidates:
        return None

    # Сортировка по качеству RAM
    candidates.sort(
        key=lambda r: (
            -r["attrs"].get("capacity_gb", 0),   # больше памяти — лучше
            -r["attrs"].get("mhz", 0),           # больше частота — лучше
            r["price"]                           # но при равных — дешевле
        )
    )

    return candidates[0]

def pick_gpu(gpus: List[Dict], budget: int) -> Dict | None:
    """
    Выбирает лучшую видеокарту в рамках выделенного бюджета.
    Критерии:
        1) Цена <= бюджет
        2) Больше VRAM — лучше
        3) Более новое поколение GDDR — лучше
        4) Если производительность равна — дешевле
    """

    # GPU, которые помещаются в бюджет
    candidates = [g for g in gpus if g["price"] <= budget]
    if not candidates:
        return None

    def gpu_score(g):
        attrs = g.get("attrs", {})
        vram = attrs.get("vram_gb", 0)
        gddr = attrs.get("gddr", 0)

        return (
            vram,   # 1. Больше VRAM
            gddr    # 2. Новый GDDR
        )

    # Сортируем по:
    # - убыванию производительности
    # - цене по возрастанию
    candidates.sort(
        key=lambda g: (
            -gpu_score(g)[0],   # VRAM
            -gpu_score(g)[1],   # GDDR
            g["price"]          # цена — меньше лучше
        )
    )

    return candidates[0]

def pick_ssd(ssds: List[Dict], budget: int) -> Dict | None:

    candidates = [s for s in ssds if s["price"] <= budget]
    if not candidates:
        return None

    # приоритет интерфейсов
    iface_rank = {
        "sata": 1,
        "sata3": 1,
        "sata 6gb/s": 1,
        "m.2 sata": 1,
        "nvme": 2,
        "m.2 nvme": 2,
        "pcie": 2,
    }

    def ssd_score(s):
        attrs = s.get("attrs", {})
        interface = attrs.get("interface", "").lower()

        return (
            attrs.get("capacity_gb", 0),
            iface_rank.get(interface, 1)  # default = SATA
        )

    candidates.sort(
        key=lambda s: (
            -ssd_score(s)[0],   # capacity_gb
            -ssd_score(s)[1],   # interface rank
            s["price"]          # cheaper
        )
    )

    return candidates[0]

def estimate_gpu_tdp(gpu: Dict | None) -> int:
    if not gpu:
        return 0
    vram = gpu["attrs"].get("vram_gb", 0)
    if vram <= 2:
        return 50
    if vram <= 4:
        return 100
    if vram <= 8:
        return 180
    if vram <= 12:
        return 200
    if vram <= 16:
        return 250
    if vram <= 32:
        return 350
    return 250


def pick_psu(psus: List[Dict], cpu: Dict, gpu: Dict, budget: int) -> Dict | None:
    """
    Выбор блока питания по мощности и бюджету.
    """

    cpu_tdp = cpu["attrs"].get("tdp", 65)
    gpu_tdp = estimate_gpu_tdp(gpu)

    base_load = cpu_tdp + gpu_tdp + 50   # мать + SSD + кулеры
    required = int(base_load * 1.3)      # 30% запас

    # Фильтрация по мощности и бюджету
    candidates = [
        p for p in psus
        if p["attrs"].get("watt", 0) >= required and p["price"] <= budget
    ]

    if not candidates:
        return None

    # Самый дешёвый подходящий
    candidates.sort(key=lambda p: p["price"])
    return candidates[0]

def pick_cooler(coolers: List[Dict], cpu: Dict, budget: int) -> Dict | None:
    """
    Подбор кулера с более точной моделью вычисления тепловой нагрузки.
    """

    if not cpu:
        return None

    # === Извлекаем характеристики CPU ===
    cpu_tdp = cpu["attrs"].get("tdp", 65)
    cores = cpu["attrs"].get("cores", 4)
    threads = cpu["attrs"].get("threads", 4)

    # ====================================================
    #   🔥 Новая формула вычисления реальной нагрузки
    # ====================================================

    # рост тепла по ядрам ускоряется
    core_heat = cpu_tdp * (1 + max(0, cores - 4) * 0.12)

    # потоки добавляют чуть-чуть тепла
    thread_heat = cpu_tdp * (threads * 0.01)

    # итоговая тепловая нагрузка
    required_tdp = int((core_heat + thread_heat) * 1.10)  # turbo/boost overhead

    # ====================================================
    #   ЛОГИКА ВЫБОРА КУЛЕРА
    # ====================================================

    NEED_WATER_THRESHOLD = 260

    # --- Водянка ---
    if required_tdp > NEED_WATER_THRESHOLD:
        water_candidates = [
            c for c in coolers
            if c["price"] <= budget and c["attrs"].get("water", False)
        ]
        if not water_candidates:
            return None

        water_candidates.sort(key=lambda c: c["price"])
        return water_candidates[0]

    # --- Воздушные ---
    air_candidates = [
        c for c in coolers
        if c["price"] <= budget
        and not c["attrs"].get("water", False)
        and c["attrs"].get("tdp", 0) >= required_tdp
    ]

    if not air_candidates:
        return None

    air_candidates.sort(key=lambda c: c["price"])
    return air_candidates[0]

if __name__ == "__main__":
    print("\n=== EXTENDED COOLER PICKER TEST ===\n")

    TEST_CPUS = [
        {
            "name": "Intel Core i3-12100F",
            "attrs": {"tdp": 60, "cores": 4, "threads": 8}
        },
        {
            "name": "AMD Ryzen 5 5600",
            "attrs": {"tdp": 65, "cores": 6, "threads": 12}
        },
        {
            "name": "AMD Ryzen 7 5800X",
            "attrs": {"tdp": 105, "cores": 8, "threads": 16}
        },
        {
            "name": "Intel Core i7-13700K",
            "attrs": {"tdp": 125, "cores": 16, "threads": 24}
        },
    ]

    TEST_COOLERS = [
        {"name": "Deepcool CK-11508", "price": 6000, "attrs": {"tdp": 95}},
        {"name": "ID-Cooling SE-214", "price": 9500, "attrs": {"tdp": 180}},
        {"name": "Deepcool AK400", "price": 13500, "attrs": {"tdp": 220}},
        {"name": "Thermalright Peerless Assassin 120", "price": 19000, "attrs": {"tdp": 280}},
        {"name": "Deepcool Assassin IV", "price": 30000, "attrs": {"tdp": 320}},
        # Водянка для теста
        {"name": "ID-Cooling FrostFlow 360 AIO", "price": 25000, "attrs": {"water": True, "tdp": 350}},
    ]

    BUDGET = 30000

    def debug_required_tdp(cpu):
        tdp = cpu["attrs"]["tdp"]
        cores = cpu["attrs"]["cores"]
        threads = cpu["attrs"]["threads"]
        load_factor = (cores * 0.07) + (threads * 0.03)
        extra_boost = 1 + (cores + threads) / 40
        return int(tdp * load_factor * extra_boost)

    for cpu in TEST_CPUS:
        print(f"\n--- Testing CPU: {cpu['name']} ---")

        required = debug_required_tdp(cpu)
        print(f"Required cooler TDP: {required}")

        picked = pick_cooler(TEST_COOLERS, cpu, BUDGET)
        print(f"Picked: {picked}")

        if picked:
            cooler_tdp = picked["attrs"].get("tdp", 0)

            if cooler_tdp < required and not picked["attrs"].get("water", False):
                print("❌ ERROR: Cooler is too weak!")

            elif cpu["attrs"]["tdp"] < 70 and cooler_tdp > 200:
                print("⚠️ WARNING: Cooler seems too powerful for a low-TDP CPU")

            else:
                print("✅ OK: Cooler matches CPU class")

        else:
            print("❌ No suitable cooler found!")











