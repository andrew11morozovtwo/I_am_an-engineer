"""
Скрипт для добавления конкретных слов в blacklist.
Можно использовать для добавления отдельных слов без перезапуска полной инициализации.
"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
from app.infrastructure.db.session import get_async_session
from app.infrastructure.db.repositories import BlacklistRepository
from app.infrastructure.db.models import BlacklistItem
# Слова для добавления (с заглавной и строчной буквы)
WORDS_TO_ADD = [
    "Гондон",
    "Гандон",
    "гондон",
    "гандон",
]

async def add_words_to_blacklist():
    """Добавить указанные слова в blacklist"""
    print("[INFO] Добавляем слова в blacklist...")
    
    async with get_async_session() as session:
        # Получаем существующие фразы
        existing = await BlacklistRepository.get_all(session)
        existing_phrases = {item.phrase.lower() for item in existing}
        
        added_count = 0
        skipped_count = 0
        
        for word in WORDS_TO_ADD:
            if word.lower() not in existing_phrases:
                try:
                    item = BlacklistItem(phrase=word)
                    await BlacklistRepository.add(session, item)
                    added_count += 1
                    existing_phrases.add(word.lower())  # Добавляем в множество для проверки дублей
                    print(f"[OK] Добавлено в blacklist: {word}")
                except Exception as e:
                    print(f"[ERROR] Ошибка при добавлении '{word}': {e}")
            else:
                skipped_count += 1
                print(f"[SKIP] Пропущено (уже есть в БД): {word}")
        
        print(f"\n[RESULT] Результат:")
        print(f"   [OK] Добавлено: {added_count}")
        print(f"   [SKIP] Пропущено (уже есть): {skipped_count}")
        print(f"   [INFO] Всего слов в blacklist: {len(existing) + added_count}")

if __name__ == "__main__":
    asyncio.run(add_words_to_blacklist())
