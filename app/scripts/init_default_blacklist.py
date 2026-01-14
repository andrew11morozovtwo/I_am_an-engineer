"""
Скрипт для инициализации предварительного черного списка
"""
import asyncio
from app.infrastructure.db.session import get_async_session
from app.infrastructure.db.repositories import BlacklistRepository
from app.infrastructure.db.models import BlacklistItem

# Предварительный черный список запрещенных слов и выражений
# При обнаружении этих фраз сообщение будет удалено, а пользователю выдан варн
DEFAULT_BLACKLIST = [
    # Мат и оскорбления (базовые примеры - добавьте актуальные)
    "идиот",
    "дурак",
    "тупой",
    "гондон",
    "гандон",
    
    # Английские матерные слова и выражения
    "fuck",
    "fuck off",
    "fuck you",
    "shit",
    "damn",
    "bitch",
    "asshole",
    "bastard",
    "crap",
    "piss off",
    
    # Спам и реклама
    "бесплатно подписчики",
    "раскрутка канала",
    "накрутка подписчиков",
    "купить подписчиков",
    "реклама без согласования",
    "промокод на бесплатно",
    
    # Короткие ссылки (часто используются для спама)
    "bit.ly",
    "tinyurl.com",
    "short.link",
    "t.co",
    "goo.gl",
    
    # Мошенничество и обман
    "заработок без вложений",
    "легкие деньги",
    "быстрый заработок",
    "пассивный доход",
    "работа на дому",
    
    # Запрещенные темы (примеры)
    "незаконная деятельность",
    "наркотики",
    "купить наркотики",
    
    # Конкурентная реклама (примеры)
    "переходите на наш канал",
    "лучше чем этот канал",
    "подписывайтесь на конкурента",
    
    # Другие запрещенные фразы
    "реклама",
    "спам",
]

async def init_default_blacklist():
    """Добавить предварительный черный список в БД"""
    async with get_async_session() as session:
        existing = await BlacklistRepository.get_all(session)
        existing_phrases = {item.phrase.lower() for item in existing}
        
        added_count = 0
        for phrase in DEFAULT_BLACKLIST:
            if phrase.lower() not in existing_phrases:
                item = BlacklistItem(phrase=phrase)
                await BlacklistRepository.add(session, item)
                added_count += 1
                print(f"✅ Добавлено в blacklist: {phrase}")
        
        print(f"\n[BLACKLIST INIT] Добавлено фраз: {added_count}, всего в БД: {len(existing) + added_count}")

if __name__ == "__main__":
    asyncio.run(init_default_blacklist())
