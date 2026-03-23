from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Generator, Optional, Sequence

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from config import settings


def _convert_placeholders(sql: str) -> str:
    return sql.replace("?", "%s")


def _adapt_params(params: Optional[Sequence[Any]]) -> Optional[list[Any]]:
    if params is None:
        return None
    adapted: list[Any] = []
    for value in params:
        if isinstance(value, (dict, list)):
            adapted.append(Json(value))
        else:
            adapted.append(value)
    return adapted


class DbSession:
    def __init__(self, conn: "psycopg2.extensions.connection"):
        self._conn = conn

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None):
        cur = self._conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(_convert_placeholders(sql), _adapt_params(params))
        return cur

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()


def _connect() -> "psycopg2.extensions.connection":
    if not settings.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required")
    conn = psycopg2.connect(settings.DATABASE_URL)
    schema = os.environ.get("DATABASE_SCHEMA") or settings.DATABASE_SCHEMA
    if schema:
        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {schema}")
        conn.commit()
    return conn


def get_db() -> Generator[DbSession, None, None]:
    conn = _connect()
    try:
        yield DbSession(conn)
    finally:
        conn.close()


@contextmanager
def get_db_context() -> Generator[DbSession, None, None]:
    conn = _connect()
    try:
        yield DbSession(conn)
    finally:
        conn.close()


def init_database(*args: Any, **kwargs: Any) -> None:
    message = "Database schema is managed via Supabase migrations"
    raise NotImplementedError(message)
