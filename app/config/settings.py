"""
App settings.
Использует pydantic для type-safe настроек и dotenv для .env загрузки.
"""
import os
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Union
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    BOT_TOKEN: str = Field(..., env="BOT_TOKEN")
    ADMIN_IDS: str = Field(default="", env="ADMIN_IDS")  # строка через запятую
    DB_URL: str = Field("sqlite+aiosqlite:///app.db", env="DB_URL")

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: Union[str, List[int]]) -> str:
        """Парсит ADMIN_IDS из строки через запятую или оставляет как есть"""
        if isinstance(v, list):
            return ",".join(map(str, v))
        if isinstance(v, str):
            return v
        return ""

    def get_admin_ids_list(self) -> List[int]:
        """Возвращает список admin_id как числа"""
        if not self.ADMIN_IDS:
            return []
        # Убираем пробелы и разбиваем по запятой
        ids = [int(uid.strip()) for uid in self.ADMIN_IDS.split(",") if uid.strip().isdigit()]
        return ids

    class Config:
        env_file = ".env"

settings = Settings()
