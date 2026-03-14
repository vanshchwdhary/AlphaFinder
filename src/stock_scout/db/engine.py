from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def _connect_args(database_url: str) -> dict:
    if database_url.startswith("sqlite:"):
        return {"check_same_thread": False}
    return {}

def _normalize_database_url(database_url: str) -> str:
    # Many managed Postgres providers still emit `postgres://...` URLs.
    # SQLAlchemy expects `postgresql://...`.
    if database_url.startswith("postgres://"):
        database_url = "postgresql://" + database_url[len("postgres://") :]

    # Prefer psycopg3 if available (Render installs `psycopg[binary]` in `requirements-render.txt`).
    # If psycopg isn't installed, keep the URL unchanged so environments using psycopg2 can still work.
    if database_url.startswith("postgresql://"):
        try:
            import psycopg  # noqa: F401
        except Exception:
            return database_url
        return "postgresql+psycopg://" + database_url[len("postgresql://") :]

    return database_url


@lru_cache(maxsize=4)
def get_engine(database_url: str) -> Engine:
    database_url = _normalize_database_url(database_url)
    return create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
        connect_args=_connect_args(database_url),
    )


def SessionLocal(database_url: str) -> sessionmaker[Session]:
    engine = get_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def session_scope(database_url: str) -> Iterator[Session]:
    SessionMaker = SessionLocal(database_url)
    session = SessionMaker()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
