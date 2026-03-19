"""
PostgreSQL database access layer for the PathFinder API.

This module provides a thin wrapper around ``psycopg2`` that handles two
adaptations transparently so routers never import psycopg2 directly:

1. **Placeholder conversion** — SQL written with ``?`` markers is rewritten
   to ``%s`` so the same query strings remain compatible with psycopg2.
2. **JSON parameter adaptation** — Python ``dict`` and ``list`` values are
   automatically wrapped in ``psycopg2.extras.Json`` before binding,
   enabling seamless storage into PostgreSQL ``JSONB`` columns.

Usage patterns
--------------
**FastAPI dependency injection** (preferred in routers)::

    from fastapi import Depends
    from database import DbSession, get_db

    @router.get("/example")
    def my_endpoint(db: DbSession = Depends(get_db)):
        cur = db.execute("SELECT * FROM plans WHERE user_id = ?", [user_id])
        return cur.fetchall()

**Context manager** (for background tasks or scripts)::

    from database import get_db_context

    with get_db_context() as db:
        db.execute("UPDATE nodes SET status = ? WHERE id = ?", ["learned", node_id])
        db.commit()

Notes
-----
- Schema management is intentionally absent; the database schema is managed
  via Supabase migrations, not by this application.
- Each request opens and closes its own connection. For high-traffic
  deployments, consider adding ``psycopg2-pool`` or migrating to ``asyncpg``.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator, Optional, Sequence

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from config import settings


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _convert_placeholders(sql: str) -> str:
    """Rewrite ``?`` parameter markers to ``%s`` for psycopg2 compatibility.

    This allows query strings to use the database-agnostic ``?`` style
    while still working with psycopg2, which requires ``%s`` markers.

    Args:
        sql: A SQL string potentially containing ``?`` placeholders.

    Returns:
        The same SQL with every ``?`` replaced by ``%s``.
    """
    return sql.replace("?", "%s")


def _adapt_params(params: Optional[Sequence[Any]]) -> Optional[list[Any]]:
    """Wrap Python dicts and lists in ``Json`` for psycopg2 JSONB binding.

    Without this adaptation, passing a Python ``dict`` to psycopg2 raises a
    type error when binding to a ``JSONB`` column.  All other types are
    passed through unchanged.

    Args:
        params: The sequence of values to bind to SQL placeholders,
                or ``None`` for parameter-free queries.

    Returns:
        A new list where ``dict`` and ``list`` values are wrapped in
        ``psycopg2.extras.Json``, or ``None`` if ``params`` was ``None``.
    """
    if params is None:
        return None
    adapted: list[Any] = []
    for value in params:
        if isinstance(value, (dict, list)):
            adapted.append(Json(value))
        else:
            adapted.append(value)
    return adapted


# ---------------------------------------------------------------------------
# Session wrapper
# ---------------------------------------------------------------------------


class DbSession:
    """Lightweight wrapper around a raw psycopg2 connection.

    Exposes ``execute``, ``commit``, ``rollback``, and ``close`` so that
    callers never need to import or interact with psycopg2 directly.

    Do not instantiate this class directly; obtain one via ``get_db()`` or
    ``get_db_context()``.
    """

    def __init__(self, conn: "psycopg2.extensions.connection"):
        """Initialise the session around an existing psycopg2 connection.

        Args:
            conn: An open psycopg2 connection.  The session wraps it as-is;
                  it does not open a new connection.
        """
        self._conn = conn

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None):
        """Execute a SQL statement and return the cursor for result fetching.

        Applies placeholder conversion (``?`` → ``%s``) and JSON adaptation
        automatically.  Results are returned as ``RealDictRow`` objects
        (dict-like), so columns can be accessed by name.

        Args:
            sql: SQL statement with optional ``?`` or ``%s`` placeholders.
            params: Positional bind values. ``dict`` and ``list`` values are
                    automatically converted to PostgreSQL JSON.

        Returns:
            A psycopg2 cursor whose rows behave like dicts.  Call
            ``.fetchone()``, ``.fetchall()``, or iterate directly.
        """
        cur = self._conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(_convert_placeholders(sql), _adapt_params(params))
        return cur

    def commit(self) -> None:
        """Persist all changes made in the current transaction.

        Must be called explicitly after any INSERT, UPDATE, or DELETE
        to avoid changes being rolled back when the connection closes.
        """
        self._conn.commit()

    def rollback(self) -> None:
        """Discard all changes made in the current transaction.

        Call this in an exception handler to ensure the database is left
        in a consistent state after a failed write operation.
        """
        self._conn.rollback()

    def close(self) -> None:
        """Close the underlying psycopg2 connection and release its resources.

        After calling this method the session must not be used again.  In
        normal usage the ``get_db`` / ``get_db_context`` providers close the
        connection automatically via ``finally`` blocks.
        """
        self._conn.close()


# ---------------------------------------------------------------------------
# Connection factory
# ---------------------------------------------------------------------------


def _connect() -> "psycopg2.extensions.connection":
    """Open a new psycopg2 connection using the configured DATABASE_URL.

    Optionally sets the PostgreSQL ``search_path`` to ``DATABASE_SCHEMA``
    so that unqualified table names resolve to the correct schema — useful
    when a single PostgreSQL instance hosts multiple tenants or environments.

    Returns:
        An open psycopg2 connection with auto-commit disabled (psycopg2 default).

    Raises:
        RuntimeError: If ``DATABASE_URL`` is not configured.
    """
    if not settings.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required")
    if settings.DATABASE_SCHEMA:
        return psycopg2.connect(
            settings.DATABASE_URL,
            options=f"-c search_path={settings.DATABASE_SCHEMA}",
        )
    return psycopg2.connect(settings.DATABASE_URL)


# ---------------------------------------------------------------------------
# Public access patterns
# ---------------------------------------------------------------------------


def get_db() -> Generator[DbSession, None, None]:
    """Yield a ``DbSession`` for use as a FastAPI dependency.

    Opens a new connection, yields the session, then closes the connection
    in a ``finally`` block regardless of whether an exception was raised.

    Intended usage::

        @router.get("/plans")
        def list_plans(db: DbSession = Depends(get_db)):
            ...

    Yields:
        A ``DbSession`` wrapping a fresh psycopg2 connection.
    """
    conn = _connect()
    try:
        yield DbSession(conn)
    finally:
        conn.close()


@contextmanager
def get_db_context() -> Generator[DbSession, None, None]:
    """Context-manager version of ``get_db`` for use outside FastAPI.

    Suitable for background tasks, CLI scripts, or any code that cannot
    use dependency injection.

    Usage::

        with get_db_context() as db:
            db.execute("INSERT INTO plans ...")
            db.commit()

    Yields:
        A ``DbSession`` wrapping a fresh psycopg2 connection.
    """
    conn = _connect()
    try:
        yield DbSession(conn)
    finally:
        conn.close()


def init_database(*args: Any, **kwargs: Any) -> None:
    """Stub signalling that schema management is handled externally.

    The database schema is managed via Supabase migrations, not by this
    application.  This function exists only to make the intent explicit and
    to prevent accidental calls to an in-process schema initialiser.

    Raises:
        NotImplementedError: Always, with an explanatory message.
    """
    message = "Database schema is managed via Supabase migrations"
    raise NotImplementedError(message)
