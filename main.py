import asyncio

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from Bot.handlers.start import register_start_handlers
from aiogram.types import Message
from config import TOKEN

bot = Bot(token=TOKEN)
dp = Dispatcher()

def register_all_handlers(dp: Dispatcher):
    register_start_handlers(dp)

async def main():
    register_all_handlers(dp)
    await dp.start_polling(bot)



if __name__ == '__main__':
    asyncio.run(main())