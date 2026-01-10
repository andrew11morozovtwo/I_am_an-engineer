"""
App settings.
Использует pydantic для type-safe настроек и dotenv для .env загрузки.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    BOT_TOKEN: str = Field(..., env="BOT_TOKEN")
    ADMIN_IDS: str = Field(default="", env="ADMIN_IDS")  # строка через запятую
    DB_URL: str = Field("sqlite+aiosqlite:///app.db", env="DB_URL")

    @staticmethod
    def parse_admin_ids(admin_ids_str: str) -> List[int]:
        """Парсит ADMIN_IDS из строки через запятую"""
        if not admin_ids_str:
            return []
        ids = [int(uid.strip()) for uid in admin_ids_str.split(",") if uid.strip().isdigit()]
        return ids

    def get_admin_ids_list(self) -> List[int]:
        """Возвращает список admin_id как числа"""
        return self.parse_admin_ids(self.ADMIN_IDS)

    class Config:
        env_file = ".env"

settings = Settings()
