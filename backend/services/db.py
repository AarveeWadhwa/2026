"""SQLite/PostgreSQL connection helpers for BidPilot.

Set DATABASE_URL to a PostgreSQL URI in hosted environments. If absent, local
SQLite behavior is retained. PostgreSQL connections use psycopg 3.
"""
from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any


def postgres_enabled() -> bool:
    return bool(os.getenv("DATABASE_URL", "").strip())


def _pg_sql(sql: str) -> str:
    # Convert the small SQLite dialect subset used by BidPilot.
    sql = re.sub(r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b", "BIGSERIAL PRIMARY KEY", sql, flags=re.I)
    # In SQL expressions, SQLite accepts double-quoted string literals; PostgreSQL
    # interprets them as identifiers.
    sql = sql.replace('"urgent"', "'urgent'").replace('"high"', "'high'").replace('"medium"', "'medium'").replace('"done"', "'done'")
    sql = sql.replace("?", "%s")
    return sql


class Connection:
    def __init__(self, raw: Any, is_pg: bool):
        self.raw = raw
        self.is_pg = is_pg
        self.row_factory = None

    def execute(self, sql: str, params=()):
        if self.is_pg:
            return self.raw.execute(_pg_sql(sql), params)
        return self.raw.execute(sql, params)

    def commit(self):
        return self.raw.commit()

    def rollback(self):
        return self.raw.rollback()

    def close(self):
        return self.raw.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


def connect(path: str | Path) -> Connection:
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("DATABASE_URL is set but psycopg is not installed; install requirements.txt") from exc
        raw = psycopg.connect(url, row_factory=dict_row, connect_timeout=10)
        return Connection(raw, True)
    raw = sqlite3.connect(str(path))
    raw.row_factory = sqlite3.Row
    return Connection(raw, False)


@contextmanager
def connection(path: str | Path):
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
