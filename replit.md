# InsightPilot AI

Autonomous business analytics platform that transforms raw CSV/Excel data into executive-level insights using AI.

## Architecture

**Monorepo** managed with pnpm workspaces.

### Services

| Service | Stack | Path | Port |
|---|---|---|---|
| Frontend | React + Vite + Tailwind | `artifacts/insightpilot/` | 23874 |
| AI Backend | Python FastAPI + Pandas | `artifacts/insightpilot/backend/` | 8001 |
| Legacy API | Node.js Express | `artifacts/api-server/` | 22729 |

### Shared Libraries

- `lib/api-spec/` — OpenAPI spec (source of truth for API contracts)
- `lib/api-client-react/` — Generated React Query hooks (from codegen)
- `lib/api-zod/` — Generated Zod schemas (from codegen)
- `lib/db/` — Drizzle ORM + PostgreSQL schema

## How to Run

The app starts automatically via Replit workflows:
- **InsightPilot AI (Frontend)**: `artifacts/insightpilot: web`
- **Python AI Backend**: `artifacts/insightpilot: api`

## Key Features

- **CSV/Excel Upload**: Upload datasets via the `/api/upload` endpoint
- **Autonomous Analysis**: AI profiles datasets, extracts KPIs, generates charts — `/api/analyze`
- **AI Copilot**: Natural-language Q&A about datasets — `/api/copilot`
- **CEO Briefing**: Executive-level summary with health score, risks, and recommendations
- **Chart Insights**: AI-generated business explanations for each chart

## AI Provider

Uses Google Gemini (primary) or OpenRouter as fallback. Configured via `GEMINI_API_KEY` or `OPENROUTER_API_KEY` environment secrets.

## Python Backend

Located at `artifacts/insightpilot/backend/`. Dependencies managed by pip into `.pythonlibs/`.

To add a new Python package:
```
pnpm run installLanguagePackages  # use the package-management skill
```

## Codegen

After modifying `lib/api-spec/openapi.yaml`:
```bash
pnpm --filter @workspace/api-spec run codegen
```

## Database

PostgreSQL via Replit's built-in database. Schema in `lib/db/src/schema/`. Push schema changes with:
```bash
pnpm --filter @workspace/db run push
```

## User Preferences

- Keep the existing Python FastAPI backend structure — don't migrate to Node.js
