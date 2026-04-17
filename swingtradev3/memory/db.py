from __future__ import annotations

import os
from contextlib import contextmanager
from functools import lru_cache
from threading import Lock
from typing import Iterator

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from paths import PROJECT_ROOT


DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@db:5432/swingtradev3"
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"

_migration_lock = Lock()
_migrations_applied = False


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL).strip() or DEFAULT_DATABASE_URL


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(
        get_database_url(),
        pool_pre_ping=True,
        future=True,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def build_alembic_config() -> AlembicConfig:
    config = AlembicConfig(str(ALEMBIC_INI_PATH))
    config.set_main_option("sqlalchemy.url", get_database_url())
    config.set_main_option("script_location", str(PROJECT_ROOT / "memory" / "migrations"))
    return config


def ensure_database_ready() -> None:
    global _migrations_applied
    if _migrations_applied:
        return

    with _migration_lock:
        if _migrations_applied:
            return
        command.upgrade(build_alembic_config(), "head")
        _migrations_applied = True


@contextmanager
def session_scope() -> Iterator[Session]:
    ensure_database_ready()
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
