from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("TOKEN")
GROQ_API = os.getenv("GROQ_API")

if not TOKEN:
    raise ValueError("TOKEN не найден в .env! Добавь TOKEN=... в файл .env")