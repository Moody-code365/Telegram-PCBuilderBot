import asyncio
import logging

from aiogram import Bot, Dispatcher
from config import TOKEN

from Bot.handlers.start import router as start_router
from Bot.handlers.help import router as help_router
from Bot.handlers.about import router as about_router
from Bot.handlers.build import router as build_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

bot = Bot(token=TOKEN)
dp = Dispatcher()


def register_all_routers() -> None:
    dp.include_router(start_router)
    dp.include_router(help_router)
    dp.include_router(about_router)
    dp.include_router(build_router)


async def main() -> None:
    register_all_routers()
    logging.info("Бот запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())