# Codebase Map Template

Fill this in after the onboarding workflow. Keep it to about one page. Every claim should point to a file path so a reader can check it. Write "unknown" rather than guessing.

```markdown
# Codebase map: <repo name>

_Last verified: <date>, at commit <short sha>_

## What it is
One or two sentences: what the system does and who uses it.

## Stack
- Language / runtime: <e.g. TypeScript on Node 22> (source: `.nvmrc`)
- Frameworks: <e.g. NestJS, Prisma>
- Package manager / build tool: <e.g. pnpm 9, Turborepo> (source: `pnpm-lock.yaml`, `turbo.json`)
- Data stores and external services: <e.g. PostgreSQL, Redis, S3, Stripe>

## Commands (verified)
| Task | Command | Notes |
| --- | --- | --- |
| Install | `...` | |
| Build | `...` | |
| Test (fast) | `...` | unit only, no services |
| Test (full) | `...` | needs `docker compose up db` |
| Lint / format | `...` | |
| Type-check | `...` | |
| Run locally | `...` | port, required env vars |

Baseline: <all tests pass | N known failures: list>

## Layout
| Path | Contains |
| --- | --- |
| `src/api/` | HTTP handlers |
| `src/domain/` | business logic |
| `src/db/` | repositories, migrations |
| `tests/` | ... |

## Entry points
- HTTP server: `src/main.ts`
- Background workers: `src/worker.ts`
- CLI / scripts: `scripts/`

## Request trace: <feature name>
1. `src/api/orders.controller.ts` `create()` - validates input with `CreateOrderDto`
2. `src/domain/orders.service.ts` `placeOrder()` - applies pricing rules
3. `src/db/orders.repo.ts` - writes `orders` and `order_items` in one transaction
4. Publishes `OrderPlaced` to queue `orders` (`src/events/publisher.ts`)

## Conventions
- Errors: <e.g. throw domain errors, mapped to HTTP in `src/api/error-filter.ts`>
- Logging: <logger and required fields>
- Tests: <framework, naming, fixtures location>
- Do not edit: <generated paths and how to regenerate>

## Config and environments
- Config loading: <file>
- Required env vars: see `.env.example` (names only, never values)
- Feature flags: <system>

## How changes ship
- Branching / PR rules: <...>
- Required CI checks: <...>
- Deploy: <e.g. merge to main deploys staging; tag deploys production>

## Open questions
- <things the repo could not answer; ask the user>
```

## Tips

- Prefer a table or list to prose; the map is for scanning.
- If the repo is a monorepo, add a "Packages" table (name, path, purpose, owner) and map only the packages relevant to the task.
- Re-verify the "Commands" section if the map is older than the last change to CI config.
