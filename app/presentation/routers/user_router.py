"""
Handlers for user (public) commands: /start, /help, /faq etc.
"""
from aiogram import Router, types, F
from aiogram.filters import Command
from app.infrastructure.db.session import get_async_session
from app.infrastructure.db.models import User
from app.infrastructure.db.repositories import UserRepository

user_router = Router()

@user_router.message(Command("start"))
async def start_handler(message: types.Message):
    async with get_async_session() as session:
        user = await UserRepository.get_by_id(session, user_id=message.from_user.id)
        if not user:
            user = User(id=message.from_user.id, username=message.from_user.username, full_name=message.from_user.full_name)
            await UserRepository.add(session, user)
            greeting = "Привет! Ты зарегистрирован в системе 😊"
        else:
            greeting = "С возвращением!"
        await message.answer(greeting)
