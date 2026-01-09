"""
Entry point for the AdminBot project.
"""
import asyncio
from aiogram import Bot, Dispatcher
from app.config.settings import settings
from app.presentation.routers.user_router import user_router
from app.presentation.routers.channel_router import channel_router

async def main():
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    # Register routers
    dp.include_router(user_router)
    dp.include_router(channel_router)

    print("Bot initialized. Ready to start polling.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
