from __future__ import annotations

import argparse
from pathlib import Path

import psycopg2


def _read_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _split_statements(sql: str) -> list[str]:
    parts = [part.strip() for part in sql.split(";")]
    return [part for part in parts if part]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--schema", default=None)
    parser.add_argument(
        "--schema-sql",
        default=str(Path(__file__).resolve().parents[1] / "schema.sql"),
    )
    args = parser.parse_args()

    schema_sql_path = Path(args.schema_sql).resolve()
    schema_sql = _read_sql(schema_sql_path)
    statements = _split_statements(schema_sql)

    conn = psycopg2.connect(args.database_url)
    try:
        with conn:
            with conn.cursor() as cur:
                if args.schema:
                    cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{args.schema}"')
                    cur.execute(f'SET search_path TO "{args.schema}"')
                for stmt in statements:
                    cur.execute(stmt)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
