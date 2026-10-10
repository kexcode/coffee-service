import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str = ""
    ADMIN_TG_IDS: str = ""
    WEBAPP_URL: str = "http://localhost:3000"
    PAYPAL_ME_URL: str = "https://paypal.me/officecoffee"
    MONTHLY_TARGET: float = 150.0
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/coffee.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def admin_id_list(self) -> List[int]:
        if not self.ADMIN_TG_IDS:
            return []
        ids = []
        for x in self.ADMIN_TG_IDS.split(","):
            cleaned = x.strip()
            if cleaned.isdigit():
                ids.append(int(cleaned))
        return ids

    def is_admin(self, tg_id: int) -> bool:
        return tg_id in self.admin_id_list


@lru_cache()
def get_settings() -> Settings:
    return Settings()
