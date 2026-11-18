"""DB migration runner — additive, idempotent, safe to re-run.
Supports SQLite (dev/test) and MySQL (production).
Uses raw drivers directly — never goes through _ConnWrapper — so DDL commits reliably.
"""
from __future__ import annotations
from pathlib import Path
from db.session import DATABASE_URL, IS_MYSQL

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def _split_sql(sql: str):
    """Strip comment lines then split on ';'."""
    lines = [ln for ln in sql.splitlines() if not ln.strip().startswith("--")]
    for stmt in "\n".join(lines).split(";"):
        stmt = stmt.strip()
        if stmt:
            yield stmt


def _is_ignorable(e: Exception) -> bool:
    msg = str(e).lower()
    return (
        "duplicate column" in msg
        or "already exists" in msg
        or "1060" in msg   # MySQL: duplicate column
        or "1061" in msg   # MySQL: duplicate key name
        or "1050" in msg   # MySQL: table already exists
    )


def _run_mysql() -> None:
    import re
    import pymysql

    m = re.match(r"mysql\+pymysql://([^:]*):([^@]*)@([^:/]+):?(\d*)/(.*)", DATABASE_URL)
    if not m:
        raise ValueError(f"Cannot parse MySQL URL: {DATABASE_URL}")
    user, pwd, host, port, db = m.groups()

    conn = pymysql.connect(
        host=host, port=int(port or 3306), user=user, password=pwd,
        database=db, charset="utf8mb4", autocommit=True,  # autocommit=True so DDL is instant
    )
    cur = conn.cursor(pymysql.cursors.DictCursor)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename   VARCHAR(255) PRIMARY KEY,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("SELECT filename FROM schema_migrations")
    applied = {row["filename"] for row in cur.fetchall()}

    migration_files = sorted((MIGRATIONS_DIR / "mysql").glob("*.sql"))

    for path in migration_files:
        if path.name in applied:
            continue
        print(f"Applying {path.name}...")
        for stmt in _split_sql(path.read_text()):
            try:
                cur.execute(stmt)
            except Exception as e:
                if _is_ignorable(e):
                    continue
                cur.close()
                conn.close()
                raise RuntimeError(f"Migration failed on statement:\n{stmt}\nError: {e}") from e
        cur.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,))
        print(f"  ✓ {path.name}")

    cur.close()
    conn.close()
    print("Migrations complete.")


def _run_sqlite() -> None:
    import sqlite3

    path = DATABASE_URL.replace("sqlite:///", "")
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename   TEXT PRIMARY KEY,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    applied = {row[0] for row in conn.execute("SELECT filename FROM schema_migrations")}
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    for path in migration_files:
        if path.name in applied:
            continue
        print(f"Applying {path.name}...")
        for stmt in _split_sql(path.read_text()):
            try:
                conn.execute(stmt)
            except Exception as e:
                if _is_ignorable(e):
                    continue
                conn.close()
                raise
        conn.execute("INSERT INTO schema_migrations (filename) VALUES (?)", (path.name,))
        conn.commit()
        print(f"  ✓ {path.name}")

    conn.close()
    print("Migrations complete.")


def run() -> None:
    if IS_MYSQL:
        _run_mysql()
    else:
        _run_sqlite()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run()
