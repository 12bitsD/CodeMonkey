from __future__ import annotations

import os
import re
from contextlib import contextmanager
from threading import Lock
from typing import Any, Callable, Generator, Optional, Sequence

import psycopg2
from psycopg2 import pool as psycopg2_pool
from psycopg2.extras import Json, RealDictCursor

from config import settings

_VALID_SCHEMA_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$", re.IGNORECASE)
_CONNECTION_POOL: Optional["psycopg2_pool.ThreadedConnectionPool"] = None
_POOL_LOCK = Lock()


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


def _get_database_schema() -> str:
    return (os.environ.get("DATABASE_SCHEMA") or settings.DATABASE_SCHEMA).strip()


def _validate_schema_name(schema: str) -> None:
    if schema and not _VALID_SCHEMA_RE.match(schema):
        raise ValueError(f"Invalid DATABASE_SCHEMA name: {schema!r}")


def _configure_connection(conn: "psycopg2.extensions.connection") -> None:
    schema = _get_database_schema()
    _validate_schema_name(schema)
    if not schema:
        return
    with conn.cursor() as cur:
        cur.execute(f'SET search_path TO "{schema}"')
    conn.commit()


def get_connection_pool() -> "psycopg2_pool.ThreadedConnectionPool":
    global _CONNECTION_POOL

    if not settings.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required")

    with _POOL_LOCK:
        if _CONNECTION_POOL is None:
            min_size = max(1, settings.DB_POOL_MIN_SIZE)
            max_size = max(min_size, settings.DB_POOL_MAX_SIZE)
            _CONNECTION_POOL = psycopg2_pool.ThreadedConnectionPool(
                minconn=min_size,
                maxconn=max_size,
                dsn=settings.DATABASE_URL,
            )
        return _CONNECTION_POOL


def close_connection_pool() -> None:
    global _CONNECTION_POOL

    with _POOL_LOCK:
        if _CONNECTION_POOL is not None:
            _CONNECTION_POOL.closeall()
            _CONNECTION_POOL = None


def _acquire_connection() -> "psycopg2.extensions.connection":
    conn = get_connection_pool().getconn()
    _configure_connection(conn)
    return conn


def _release_connection(conn: "psycopg2.extensions.connection") -> None:
    if getattr(conn, "closed", 0):
        return
    try:
        conn.rollback()
    except Exception:
        pass
    get_connection_pool().putconn(conn)


class DbSession:
    def __init__(
        self,
        conn: "psycopg2.extensions.connection",
        close_connection: Optional[Callable[["psycopg2.extensions.connection"], None]] = None,
    ):
        self._conn = conn
        self._close_connection = close_connection or (lambda connection: connection.close())
        self._closed = False

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None):
        cur = self._conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(_convert_placeholders(sql), _adapt_params(params))
        return cur

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._close_connection(self._conn)


def get_db() -> Generator[DbSession, None, None]:
    session = DbSession(_acquire_connection(), _release_connection)
    try:
        yield session
    finally:
        session.close()


@contextmanager
def get_db_context() -> Generator[DbSession, None, None]:
    session = DbSession(_acquire_connection(), _release_connection)
    try:
        yield session
    finally:
        session.close()


def init_database(*args: Any, **kwargs: Any) -> None:
    message = "Database schema is managed via Supabase migrations"
    raise NotImplementedError(message)
