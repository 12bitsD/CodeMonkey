from __future__ import annotations

import os
import re
from contextlib import contextmanager
from threading import Lock
from typing import Any, Callable, Generator, Mapping, Optional, Sequence

import psycopg2
from psycopg2 import pool as psycopg2_pool
from psycopg2.extras import Json, RealDictCursor

from config import settings

_VALID_SCHEMA_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$", re.IGNORECASE)
_CONNECTION_POOL: Optional["psycopg2_pool.ThreadedConnectionPool"] = None
_POOL_LOCK = Lock()


class SchemaNotReadyError(RuntimeError):
    def __init__(self, missing_columns: Sequence[str]):
        self.missing_columns = list(missing_columns)
        missing = ", ".join(self.missing_columns)
        super().__init__(f"Database schema is missing required columns: {missing}")


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
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout TO %s", (settings.DB_STATEMENT_TIMEOUT_MS,))
        cur.execute("SET lock_timeout TO %s", (settings.DB_LOCK_TIMEOUT_MS,))
        cur.execute(
            "SET idle_in_transaction_session_timeout TO %s",
            (settings.DB_IDLE_IN_TX_TIMEOUT_MS,),
        )
        if schema:
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
                connect_timeout=max(1, settings.DB_CONNECT_TIMEOUT),
            )
        return _CONNECTION_POOL


def close_connection_pool() -> None:
    global _CONNECTION_POOL

    with _POOL_LOCK:
        if _CONNECTION_POOL is not None:
            _CONNECTION_POOL.closeall()
            _CONNECTION_POOL = None


def _acquire_connection() -> "psycopg2.extensions.connection":
    connection_pool = get_connection_pool()
    last_error: Optional[Exception] = None

    for _attempt in range(2):
        conn = connection_pool.getconn()
        try:
            if getattr(conn, "closed", 0):
                raise psycopg2.OperationalError("pooled connection is closed")
            _configure_connection(conn)
            return conn
        except (psycopg2.InterfaceError, psycopg2.OperationalError) as error:
            last_error = error
            try:
                connection_pool.putconn(conn, close=True)
            except Exception:
                pass

    if last_error:
        raise last_error
    raise RuntimeError("Unable to acquire database connection")


def _release_connection(conn: "psycopg2.extensions.connection") -> None:
    close_connection = bool(getattr(conn, "closed", 0))
    try:
        if not close_connection:
            conn.rollback()
    except Exception:
        close_connection = True
    try:
        get_connection_pool().putconn(conn, close=close_connection)
    except TypeError:
        get_connection_pool().putconn(conn)
    except Exception:
        pass


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


def ensure_schema_columns(
    db: DbSession,
    required_columns: Mapping[str, Sequence[str]],
) -> None:
    missing: list[str] = []

    for table_name, columns in required_columns.items():
        rows = db.execute(
            (
                "SELECT column_name "
                "FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = ?"
            ),
            (table_name,),
        ).fetchall()
        present = {row["column_name"] for row in rows}
        for column in columns:
            if column not in present:
                missing.append(f"{table_name}.{column}")

    if missing:
        raise SchemaNotReadyError(missing)


@contextmanager
def transaction(db: DbSession) -> Generator[DbSession, None, None]:
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


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
