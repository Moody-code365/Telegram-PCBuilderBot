from typing import Dict, Any

BUDGER_MAP = (
    {
        "до 150 000 ₸": (0, 150_000),
        "150–200 000 ₸": (150_000, 200_000),
        "250–300 000 ₸": (250_000, 300_000),
        "400–600 000 ₸": (400_000, 600_000),
        "600 000 ₸+": (600_000, 10_000_000),
    }
)

BUILD_PRESETS = {
    "office": {
        "cpu": "Intel i3 / Ryzen 3",
        "gpu": "Встроенная графика",
        "ram": "8 GB",
        "ssd": "256 GB NVMe",
        "psu": "400W",
    },
    "gaming_low": {
        "cpu": "Ryzen 5 3600",
        "gpu": "GTX 1650 / RX 570",
        "ram": "16 GB",
        "ssd": "500 GB NVMe",
        "psu": "500W",
    },
    "gaming_mid": {
        "cpu": "Ryzen 5 5600",
        "gpu": "RTX 2060 / RX 6600",
        "ram": "16 GB",
        "ssd": "1 TB NVMe",
        "psu": "600W",
    },
    "gaming_high": {
        "cpu": "Ryzen 7 / i7",
        "gpu": "RTX 3070 / RX 6800",
        "ram": "32 GB",
        "ssd": "1 TB NVMe",
        "psu": "750W",
    },
}

def normalize_budget(budget: Any) -> int:
    if isinstance(budget, int):
        return budget
    if budget in BUDGER_MAP:
        return BUDGER_MAP[budget][1]
    return 0

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

    return {}

def build_pc(data: Dict[str, Any]) -> Dict[str, str]:
    budget = normalize_budget(data["budget"])
    usage = data["usage"]

    preset = pick_preset(budget, usage)
    return preset