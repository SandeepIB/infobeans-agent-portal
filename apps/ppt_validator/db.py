"""FROZEN — Legacy database access for the `runs` table.
Do not modify. New code uses db/session.py and db/repository.py.
"""
import os
import sqlite3
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///platform.db")
_DB_PATH = DATABASE_URL.replace("sqlite:///", "")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def legacy_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_legacy_db() -> None:
    """Create the legacy `runs` table if it doesn't exist."""
    with legacy_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                filename   TEXT NOT NULL,
                status     TEXT NOT NULL DEFAULT 'queued',
                score      INTEGER,
                result     TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
