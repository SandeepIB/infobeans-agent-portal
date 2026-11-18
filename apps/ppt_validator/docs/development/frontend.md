# Frontend — NOW

## Purpose

React/Vite frontend serving the review UI, admin UI, and observability dashboards.

## Stack

- React 18 + TypeScript (strict mode)
- Vite (build tool)
- Served at `/app` (from `frontend/dist` after build)
- Legacy UI at `/` (from `static/index.html` — frozen)

## Commands

```bash
cd frontend
npm install           # install dependencies
npm run dev           # dev server (hot reload)
npm run build         # production build → frontend/dist
npm run type-check    # TypeScript type check only
```

## Key Pages / Routes

| Route | Purpose |
|-------|---------|
| `/app/` | New review: upload PPT, select profile |
| `/app/review/:id` | Review results: score, findings, proposal coverage |
| `/app/history` | Review history |
| `/app/admin/prompts` | Prompt management (list, edit, activate) |
| `/app/admin/rules` | Rule Library management |
| `/app/admin/agents` | Agent Registry view |
| `/app/admin/profiles` | Review Profile management |
| `/app/admin/observability` | Observability dashboards |
| `/app/admin/cost` | Cost and token usage dashboard |

## Legacy UI

`static/index.html` — frozen, never modified. Served by legacy routes in `app.py`.

## API Communication

Frontend communicates with the backend at `/api/v2/*`. Use `api/client.ts` for all API calls.
Do not make `fetch`/`axios` calls directly in components.

## Proposal Coverage UI

The Proposal Context Agent returns a Coverage Matrix. Display in a dedicated tab:

| Requirement | Slides | Coverage | Confidence |
|-------------|--------|----------|-----------|
| REQ-001 Cloud migration | 12–14 | COVERED | 95% |
| REQ-003 Security architecture | 18 | PARTIAL | 81% |
| REQ-004 Training | — | MISSING | 99% |

## Design Match UI

Slides excluded by Slide Design Match show a "Design Matched" badge.
Tooltip: "This slide matches the approved reference template. Design agents were not applied."

## Related Documents

- See: [backend.md](backend.md) for API conventions
- See: [../operations/observability.md](../operations/observability.md) for dashboard content
