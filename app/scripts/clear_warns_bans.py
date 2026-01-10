"""
Скрипт для очистки варнов и банов из базы данных.
Использовать для тестирования - очищает все варны и баны, сбрасывает счетчики варнов у пользователей.
Запуск: python -m app.scripts.clear_warns_bans
Или: python app/scripts/clear_warns_bans.py (из корня проекта)
"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
from sqlalchemy import delete, update, func
from sqlalchemy.future import select
from app.infrastructure.db.session import get_async_session
from app.infrastructure.db.models import Warn, Ban, User, UserStatus


async def clear_warns_and_bans():
    """Очистить все варны и баны, сбросить счетчики варнов"""
    print("🔄 Начинаем очистку варнов и банов...")
    
    async with get_async_session() as session:
        try:
            # 1. Подсчитываем количество записей перед удалением
            
            warns_count = await session.execute(select(func.count(Warn.id)))
            warns_total = warns_count.scalar() or 0
            
            bans_count = await session.execute(select(func.count(Ban.id)))
            bans_total = bans_count.scalar() or 0
            
            users_with_warns = await session.execute(
                select(func.count(User.id)).where(User.warn_count > 0)
            )
            users_with_warns_total = users_with_warns.scalar() or 0
            
            print(f"📊 Найдено:")
            print(f"   - Варнов: {warns_total}")
            print(f"   - Банов: {bans_total}")
            print(f"   - Пользователей с варнами: {users_with_warns_total}")
            
            if warns_total == 0 and bans_total == 0:
                print("✅ База данных уже чиста, нечего удалять.")
                return
            
            # 2. Удаляем все варны
            if warns_total > 0:
                await session.execute(delete(Warn))
                print(f"✅ Удалено варнов: {warns_total}")
            
            # 3. Удаляем все баны
            if bans_total > 0:
                await session.execute(delete(Ban))
                print(f"✅ Удалено банов: {bans_total}")
            
            # 4. Сбрасываем счетчики варнов и статусы у всех пользователей
            try:
                # Сначала пробуем с обновлением статуса
                await session.execute(
                    update(User).values(
                        warn_count=0,
                        is_banned=False,
                        status=UserStatus.ACTIVE
                    )
                )
                print(f"✅ Сброшены счетчики варнов и статусы у всех пользователей")
                print(f"   - warn_count = 0")
                print(f"   - is_banned = False")
                print(f"   - status = 'active'")
            except Exception as update_error:
                # Если колонка status не существует, обновляем без неё
                await session.execute(
                    update(User).values(
                        warn_count=0,
                        is_banned=False
                    )
                )
                print(f"✅ Сброшены счетчики варнов у всех пользователей")
                print(f"   - warn_count = 0")
                print(f"   - is_banned = False")
                print(f"ℹ️  Статусы не обновлены (колонка 'status' может отсутствовать)")
            
            # 5. Сохраняем изменения
            await session.commit()
            
            print(f"\n✅ Очистка завершена успешно!")
            print(f"   - Удалено варнов: {warns_total}")
            print(f"   - Удалено банов: {bans_total}")
            print(f"   - Сброшены счетчики у пользователей")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Ошибка при очистке: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(clear_warns_and_bans())
