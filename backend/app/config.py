import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str = ""
    ADMIN_TG_IDS: str = ""
    ADMIN_USERNAMES: str = ""
    WEBAPP_URL: str = "http://localhost:3000"
    PAYPAL_ME_URL: str = "https://paypal.me"
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

    @property
    def live_webapp_url(self) -> str:
        """
        Returns the most up-to-date HTTPS WebApp URL.
        First checks ./data/webapp_url.txt (written dynamically by tunnel-sync),
        falling back to the WEBAPP_URL environment variable.
        """
        for candidate_path in ("./data/webapp_url.txt", "/app/data/webapp_url.txt"):
            try:
                if os.path.exists(candidate_path):
                    with open(candidate_path, "r", encoding="utf-8") as f:
                        url = f.read().strip()
                    if url.startswith("https://"):
                        return url
            except Exception:
                pass
        return self.WEBAPP_URL.strip()


@lru_cache()
def get_settings() -> Settings:
    return Settings()
