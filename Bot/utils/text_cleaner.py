import re


def remove_emoji(text: str) -> str:
    """Удаляет эмодзи и спецсимволы, оставляя буквы, цифры и пробелы."""
    return re.sub(r"[^\w\sёЁ]+", "", text).strip()


def normalize(text: str) -> str:
    """Нормализует текст: убирает эмодзи, лишние пробелы, приводит к lowercase."""
    return remove_emoji(text).strip().lower()