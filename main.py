import asyncio

from aiogram import Bot, Dispatcher
from Bot.handlers.start import register_start_handlers
from Bot.handlers.help import register_help_handlers
from Bot.handlers.about import register_about_handlers
from config import TOKEN

bot = Bot(token=TOKEN)
dp = Dispatcher()

def register_all_handlers(disp: Dispatcher):
    register_start_handlers(dp)
    register_help_handlers(dp)
    register_about_handlers(dp)

async def main():
    register_all_handlers(dp)
    await dp.start_polling(bot)



if __name__ == '__main__':
    asyncio.run(main())