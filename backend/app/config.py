import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str = ""
    ADMIN_TG_IDS: str = ""
    ADMIN_USERNAMES: str = "leorapatskiy"
    WEBAPP_URL: str = "http://localhost:3000"
    PAYPAL_ME_URL: str = "https://paypal.me/Rapatskiy"
    MONTHLY_TARGET: float = 150.0
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/coffee.db"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
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

    @property
    def admin_usernames_list(self) -> List[str]:
        if not self.ADMIN_USERNAMES:
            return []
        return [u.strip().lower().lstrip("@") for u in self.ADMIN_USERNAMES.split(",") if u.strip()]

    def is_admin(self, tg_id: int, username: str | None = None) -> bool:
        if tg_id in self.admin_id_list:
            return True
        if username and username.lower().lstrip("@") in self.admin_usernames_list:
            return True
        return False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
