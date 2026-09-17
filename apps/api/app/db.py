"""Databaseadgang: SQLAlchemy mod standard PostgreSQL (Supabase i drift).

DDL ejes af supabase/migrations — modellerne afspejler migrations, de
genererer dem ikke (undtagen i unit tests, hvor SQLite bruges).
"""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url)


def get_db() -> Generator[Session, None, None]:
    factory = sessionmaker(bind=get_engine())
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
