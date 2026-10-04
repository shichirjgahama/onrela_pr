from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _normalize_database_url(url: str) -> str:
    """Render/Heroku отдают postgres:// — SQLAlchemy ожидает postgresql://."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


DATABASE_URL = _normalize_database_url(
    os.environ.get("DATABASE_URL", "sqlite:///./isp_erp.db")
)

_connect_args: dict = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
    # Для файловой SQLite гарантируем, что каталог существует
    # (важно при монтировании persistent disk, напр. sqlite:////data/isp_erp.db).
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = DATABASE_URL[len("sqlite:///") :]
        if db_path and db_path != ":memory:":
            Path(db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    """
    SQLite по умолчанию не включает enforcement внешних ключей.
    Для учебного проекта это важно.
    """
    if not DATABASE_URL.startswith("sqlite"):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
