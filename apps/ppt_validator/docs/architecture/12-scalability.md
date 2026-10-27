# Scalability — FUTURE

## Status: FUTURE

This document describes design compatibility for future scale. Do not implement these features until
explicitly required. The architecture must not foreclose them.

## Current Scale Target

Phase 1: single-instance deployment, SQLite, synchronous review pipeline.

## Design Compatibility Requirements

The Phase 1 architecture must support future transition to:

- **Distributed agent execution** — agents running in separate workers/containers
- **Message queue** — review requests enqueued; workers pull and process
- **Shared object storage** — PPT files in S3/GCS instead of local filesystem
- **PostgreSQL** — replace SQLite for production multi-user workloads
- **Multi-tenant isolation** — per-customer data separation
- **Horizontal scaling** — multiple ReviewService instances

## Design Decisions That Enable Future Scale

| Decision | Why it enables scale |
|---------|---------------------|
| Agent Contract is pure JSON | Agents can run anywhere and return results over a queue |
| LLMProvider is abstract | Provider can be remote or behind a proxy |
| Agent Registry is data, not code | Can be loaded from a distributed config store |
| Review Profile is data | Can be stored in any database |
| All state in DB (not in-process) | Allows stateless workers |
| Additive-only migrations | Safe to run against PostgreSQL |

## What NOT to Do in Phase 1

- Do not use in-process state that would break with multiple workers.
- Do not use filesystem paths for PPT storage in a way that assumes single-node.
- Do not hard-code `sqlite:///` in service code — use `DATABASE_URL` env var.

## Related Documents

- See: [01-system-overview.md](01-system-overview.md) for current architecture
- See: [execution-controls.md](execution-controls.md) for current concurrency model
