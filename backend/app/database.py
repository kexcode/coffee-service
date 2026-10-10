import os
from pathlib import Path
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

# Ensure SQLite directory exists if local file path
if settings.DATABASE_URL.startswith("sqlite+aiosqlite:///"):
    db_path_str = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    # strip query params if any
    db_path_clean = db_path_str.split("?")[0]
    db_path = Path(db_path_clean)
    if db_path.parent:
        db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
