"""DB session — supports SQLite (tests) and MySQL (production).

DATABASE_URL is built from individual DB_* env vars if not explicitly set.
Provides a sqlite3-compatible API so all services stay unchanged.
"""
from __future__ import annotations
import os
import re
from contextlib import contextmanager


def _build_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if url:
        return url
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    if name:
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
    return "sqlite:///platform.db"


DATABASE_URL = _build_url()
IS_MYSQL = DATABASE_URL.startswith("mysql")


class _CursorWrapper:
    """Sqlite3-compatible cursor over pymysql DictCursor."""

    def __init__(self, cursor):
        self._cur = cursor

    def execute(self, sql: str, params=None):
        sql = sql.replace("?", "%s")
        self._cur.execute(sql, params or ())
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def lastrowid(self):
        return self._cur.lastrowid


class _ConnWrapper:
    """Sqlite3-compatible connection over pymysql connection."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql: str, params=None) -> _CursorWrapper:
        import pymysql.cursors
        cur = self._conn.cursor(pymysql.cursors.DictCursor)
        wrapper = _CursorWrapper(cur).execute(sql, params)
        # Auto-commit DDL statements so tables are visible immediately
        if sql.strip().upper().startswith(("CREATE", "DROP", "ALTER", "TRUNCATE")):
            self._conn.commit()
        return wrapper

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def _parse_mysql_url(url: str):
    m = re.match(r"mysql\+pymysql://([^:]*):([^@]*)@([^:/]+):?(\d*)/(.*)", url)
    if not m:
        raise ValueError(f"Cannot parse MySQL URL: {url}")
    user, pwd, host, port, db = m.groups()
    return user, pwd, host, int(port or 3306), db


def get_conn():
    if IS_MYSQL:
        import pymysql
        user, pwd, host, port, db = _parse_mysql_url(DATABASE_URL)
        conn = pymysql.connect(
            host=host, port=port, user=user, password=pwd, database=db,
            charset="utf8mb4", autocommit=False,
        )
        return _ConnWrapper(conn)
    else:
        import sqlite3
        path = DATABASE_URL.replace("sqlite:///", "")
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn


@contextmanager
def db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
