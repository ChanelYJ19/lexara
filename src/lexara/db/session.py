"""Engine and session-factory construction."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def make_engine(database_url: str) -> Engine:
    if database_url == "sqlite:///:memory:":
        # StaticPool: all connections share the same in-memory database —
        # required so test transactions written in one session are visible in the next.
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    if database_url.startswith("sqlite://"):
        return create_engine(database_url, connect_args={"check_same_thread": False})
    return create_engine(database_url)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
