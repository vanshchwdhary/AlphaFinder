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


@lru_cache(maxsize=4)
def get_engine(database_url: str) -> Engine:
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

