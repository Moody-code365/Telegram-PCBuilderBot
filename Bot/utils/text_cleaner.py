import re

def remove_emoji(text: str) -> str:

    return re.sub(r"[^\w\sёЁ]+", "", text).strip()

def normalize(text: str) -> str:
    cleaned = remove_emoji(text).strip().lower()
    return cleaned

