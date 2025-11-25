import asyncio

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.filters import Command
from aiogram.types import Message
from config import TOKEN

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("👋 Привет! Я бот для подбора комплектующих ПК.\n"
        "Введите /build чтобы начать сборку ПК.")

async def main():
    await dp.start_polling(bot)



if __name__ == '__main__':
    asyncio.run(main())