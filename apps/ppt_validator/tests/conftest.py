"""Pytest configuration — test environment setup."""
import os

os.environ["LLM_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "sqlite:///test_platform.db"
os.environ["LLM_CACHE_TTL_HOURS"] = "0"


def pytest_sessionstart(session):
    from db.migrate import run as run_migrations
    run_migrations()


def pytest_sessionfinish(session, exitstatus):
    import pathlib
    db = pathlib.Path("test_platform.db")
    if db.exists():
        db.unlink()
