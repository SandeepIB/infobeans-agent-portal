# Database — NOW

## Purpose

Document DB migration rules, schema conventions, and how to add new tables.

## Core Rules

1. All migrations are `CREATE TABLE IF NOT EXISTS` — additive and idempotent.
2. The existing `runs` table (legacy) is never altered, migrated, or dropped.
3. Every migration must be safe to run multiple times (idempotent).
4. Never use `ALTER TABLE` on an existing table with data.
5. To add a column: add it to a new table, or create a new table.

## Running Migrations

```bash
python db/migrate.py
```

This runs all migration files in `db/migrations/` in order.
Already-applied migrations are skipped. Safe to re-run anytime.

## Adding a New Table

1. Create `db/migrations/NNN_add_my_table.sql`:

```sql
-- Migration NNN: Add my_table
-- Additive, idempotent

CREATE TABLE IF NOT EXISTS my_table (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    review_run_id TEXT NOT NULL,
    some_field   TEXT NOT NULL,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Add index if needed
CREATE INDEX IF NOT EXISTS idx_my_table_review_run_id ON my_table(review_run_id);
```

2. Test: run `python db/migrate.py` twice — second run must produce no errors.

## DB Configuration

```dotenv
DATABASE_URL=sqlite:///platform.db     # Phase 1 default
# DATABASE_URL=postgresql://user:pass@localhost/platform  # Production
```

Use `DATABASE_URL` env var everywhere. Never hard-code `sqlite:///` in service code.

## Schema Conventions

| Convention | Rule |
|-----------|------|
| Primary key | `id INTEGER PRIMARY KEY AUTOINCREMENT` |
| Foreign key naming | `{table}_id` |
| Timestamps | `DATETIME DEFAULT CURRENT_TIMESTAMP` |
| JSON fields | Stored as `TEXT NOT NULL` (JSON string) |
| Enum fields | Stored as `TEXT NOT NULL` with constraint in application layer |
| Soft delete | Use `deleted_at DATETIME` (never hard delete audit data) |

## Legacy Tables

| Table | Status | Notes |
|-------|--------|-------|
| `runs` | FROZEN | Legacy; never alter; new code reads but does not write |

## v2 Tables

All new tables use `CREATE TABLE IF NOT EXISTS`. See [../architecture/10-versioning-audit.md](../architecture/10-versioning-audit.md) for the full audit table list.

## Related Documents

- See: [../architecture/10-versioning-audit.md](../architecture/10-versioning-audit.md) for audit tables
- See: [../architecture/12-scalability.md](../architecture/12-scalability.md) for PostgreSQL migration path
