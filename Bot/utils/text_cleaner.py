import re

def remove_emoji(text: str) -> str:
   
    return re.sub(r"[^\w\sёЁ]+", "", text).strip()
