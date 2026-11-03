# Developer Agent Skills

**61 Agent Skills for every kind of developer**: frontend, backend, databases, DevOps and cloud, security, architecture and AI engineering.

They work in **Claude Code, Cursor, OpenAI Codex, GitHub Copilot, Gemini CLI, Google Antigravity** and any other agent that reads the open [Agent Skills](https://agentskills.io) `SKILL.md` format.

[![Validate skills](https://github.com/reddygopalkrishna/developer-agent-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/reddygopalkrishna/developer-agent-skills/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Skills: 61](https://img.shields.io/badge/skills-61-brightgreen)

```bash
npx skills add reddygopalkrishna/developer-agent-skills
```

---

## Why Developer Agent Skills?

- **Concrete, not generic.** Real commands, decision tables, thresholds from standards (WCAG 2.2, RFC 9457, Core Web Vitals, OpenTelemetry), common mistakes, and clear "done when" criteria.
- **Works in any agent.** Claude Code, Cursor, Codex, Copilot, Gemini CLI and more. Only portable fields, no agent-specific tool names.
- **Reusable instructions, loaded only when needed.** Write once, use in every project. Your agent reads a skill only when the task matches, so there are no long prompts to paste and no wasted context.
- **Safe by default.** Anything that touches data, git history, infrastructure or production makes the agent stop and ask you first.
- **Plain Markdown you can read.** No scripts, no install hooks, no network calls.
- **Checked on every push.** CI runs [`scripts/validate_skills.py`](scripts/validate_skills.py) on every skill: format, naming, size limits and links.

## Install

### Any AI coding agent (recommended)

The [`skills` CLI](https://github.com/vercel-labs/skills) detects your agents and installs into each one:

```bash
npx skills add reddygopalkrishna/developer-agent-skills
```

Useful options:

```bash
# See every skill in the pack
npx skills add reddygopalkrishna/developer-agent-skills --list

# Install only the skills you want
npx skills add reddygopalkrishna/developer-agent-skills --skill database-migrations --skill code-review-changes

# Install for globally (all projects) instead of the current project
npx skills add reddygopalkrishna/developer-agent-skills -g
```

### Claude Code plugin marketplace

Run these inside Claude Code, then install only the categories you want:

```text
/plugin marketplace add reddygopalkrishna/developer-agent-skills
/plugin install engineering-core@developer-agent-skills
/plugin install frontend@developer-agent-skills
```

Plugins: `engineering-core`, `architecture`, `frontend`, `backend`, `security`, `data`, `devops-cloud`, `ai-engineering`, `meta`.

### Manual copy

Clone the repo and copy the skill folders you want into your project:

```bash
git clone https://github.com/reddygopalkrishna/developer-agent-skills.git
cp -r developer-agent-skills/skills/code-review-changes your-project/.agents/skills/
```

| Agent | Project folder |
| --- | --- |
| Most agents (Codex, Cursor, Gemini CLI, Antigravity, Copilot, ...) | `.agents/skills/` |
| Claude Code | `.claude/skills/` |
| GitHub Copilot | `.github/skills/` (also reads `.agents/skills/`) |

Folder support changes quickly. If a skill doesn't show up, check your agent's docs for where it reads skills from.

## How to use them

You don't need to call a skill. Each agent reads the skill descriptions and automatically loads the right one when your task matches. Just work normally:

- *"Design the REST endpoints for orders"* loads **api-design**
- *"Create the tables for the new billing feature"* loads **database-schema-design**
- *"Add a non-null `region` column to the orders table"* loads **database-migrations**
- *"Make this settings page accessible for keyboard and screen-reader users"* loads **web-accessibility**
- *"This test fails randomly in CI"* loads **test-strategy**
- *"Review this PR"* loads **code-review-changes**

If you want a specific skill, ask for it by name:

- *"Use the **api-design** skill to design the endpoints for orders."*
- *"Use the **database-schema-design** skill to design the tables for this feature."*
- *"Use **api-design** and **database-schema-design** together to plan the orders service."*
- *"Use the **security-audit** skill to run a security audit on this code."*
- *"Use the **test-strategy** skill to decide how we should test the checkout flow."*
- *"Use the **unit-testing** skill to add tests for the code I just changed."*
- *"Use **verify-before-done** before you tell me it's finished."*

Either way works. Installed skills load automatically when they match, and naming one just makes sure it's used.

## Skills

### Engineering core

| Skill | What it does |
| --- | --- |
| [verify-before-done](skills/verify-before-done/SKILL.md) | Run build, typecheck, lint and tests (plus a browser check for UI) before calling work done |
| [root-cause-debugging](skills/root-cause-debugging/SKILL.md) | Reproduce, isolate, bisect and fix the actual cause, with a regression test |
| [code-review-changes](skills/code-review-changes/SKILL.md) | Review PRs and diffs by severity with concrete, verified findings |
| [unit-testing](skills/unit-testing/SKILL.md) | Write unit tests for changed code, run with coverage, fix failures honestly |
| [test-strategy](skills/test-strategy/SKILL.md) | Choose what and how to test; fix flaky tests |
| [legacy-refactoring](skills/legacy-refactoring/SKILL.md) | Change untested legacy code safely in small steps |
| [git-workflow](skills/git-workflow/SKILL.md) | Clean commits, safe history edits, recovery from mistakes |
| [design-docs](skills/design-docs/SKILL.md) | Write RFCs, design docs and ADRs reviewers can decide on |
| [performance-profiling](skills/performance-profiling/SKILL.md) | Measure, profile and fix real bottlenecks in any stack |
| [dependency-upgrades](skills/dependency-upgrades/SKILL.md) | Upgrade libraries and frameworks safely, one step at a time |
| [large-scale-migrations](skills/large-scale-migrations/SKILL.md) | Run framework, language and platform migrations incrementally |
| [incident-response](skills/incident-response/SKILL.md) | Mitigate production incidents first, then write a blameless postmortem |
| [codebase-onboarding](skills/codebase-onboarding/SKILL.md) | Map an unfamiliar repository before changing it |
| [monorepo-management](skills/monorepo-management/SKILL.md) | Workspace boundaries, affected-only builds, ownership |

### Architecture

| Skill | What it does |
| --- | --- |
| [system-design](skills/system-design/SKILL.md) | Requirements, capacity estimates, components and tradeoffs |
| [domain-driven-design](skills/domain-driven-design/SKILL.md) | Bounded contexts, aggregates and context maps, and when DDD is overkill |
| [event-driven-architecture](skills/event-driven-architecture/SKILL.md) | Events, schema evolution, ordering, idempotent consumers, outbox |
| [caching-strategies](skills/caching-strategies/SKILL.md) | Where and how to cache, invalidation, stampede protection |
| [concurrency-patterns](skills/concurrency-patterns/SKILL.md) | Races, locking, async pitfalls per language, testing concurrent code |

### Frontend

| Skill | What it does |
| --- | --- |
| [typescript-patterns](skills/typescript-patterns/SKILL.md) | Strict, safe TypeScript: narrowing, unions, runtime validation |
| [react-patterns](skills/react-patterns/SKILL.md) | Modern React: effects, state, data fetching, Server Components |
| [web-performance](skills/web-performance/SKILL.md) | Hit Core Web Vitals (LCP, INP, CLS) using field data |
| [web-accessibility](skills/web-accessibility/SKILL.md) | Build and audit for WCAG 2.2 AA |
| [frontend-security](skills/frontend-security/SKILL.md) | XSS sinks, strict CSP, token storage, third-party scripts |
| [seo-and-ssr](skills/seo-and-ssr/SKILL.md) | Pick a rendering mode; metadata, structured data, crawlability |
| [micro-frontends](skills/micro-frontends/SKILL.md) | When to split a frontend, composition options, shared dependencies |
| [design-systems](skills/design-systems/SKILL.md) | Tokens, component APIs, every component state, theming and versioning |
| [internationalization](skills/internationalization/SKILL.md) | ICU messages, locale formatting, RTL, pseudo-localization |

### Backend

| Skill | What it does |
| --- | --- |
| [api-design](skills/api-design/SKILL.md) | REST conventions, errors (RFC 9457), pagination, versioning, idempotency |
| [graphql-apis](skills/graphql-apis/SKILL.md) | Schema design, batching, query limits, safe schema evolution |
| [grpc-services](skills/grpc-services/SKILL.md) | Proto compatibility rules, deadlines, streaming, load balancing |
| [realtime-apis](skills/realtime-apis/SKILL.md) | Choose SSE or WebSockets; auth, reconnects, scaling connections |
| [background-jobs](skills/background-jobs/SKILL.md) | Idempotent jobs, retries, scheduling, transactional enqueue |
| [file-storage-uploads](skills/file-storage-uploads/SKILL.md) | Presigned uploads, validation, scanning, serving files safely |
| [search-integration](skills/search-integration/SKILL.md) | Elasticsearch/OpenSearch mappings, sync, reindexing, relevance |
| [resilience-patterns](skills/resilience-patterns/SKILL.md) | Timeouts, retries with jitter, circuit breakers, outbox, sagas |
| [observability](skills/observability/SKILL.md) | Structured logs, metrics, OpenTelemetry tracing, SLO alerts |

### Security

| Skill | What it does |
| --- | --- |
| [security-audit](skills/security-audit/SKILL.md) | Concrete checks for the OWASP Top 10 risk categories |
| [threat-modeling](skills/threat-modeling/SKILL.md) | Data flow diagrams and STRIDE, turned into tracked mitigations |
| [auth-implementation](skills/auth-implementation/SKILL.md) | OAuth 2.0 / OIDC with PKCE, sessions, tokens, authorization |

### Data

| Skill | What it does |
| --- | --- |
| [database-migrations](skills/database-migrations/SKILL.md) | Zero-downtime schema changes for PostgreSQL and MySQL |
| [sql-optimization](skills/sql-optimization/SKILL.md) | Read query plans, design indexes, fix N+1 and slow queries |
| [orm-patterns](skills/orm-patterns/SKILL.md) | N+1, lazy loading and transactions in Prisma, Hibernate, EF Core, SQLAlchemy and more |
| [postgres-operations](skills/postgres-operations/SKILL.md) | Pooling, vacuum, replication, backups and tested restores |
| [database-schema-design](skills/database-schema-design/SKILL.md) | Schema design, keys, constraints, multi-tenancy, NoSQL modeling |
| [nosql-design](skills/nosql-design/SKILL.md) | MongoDB, DynamoDB and Redis designed from access patterns |
| [database-testing](skills/database-testing/SKILL.md) | Real-engine tests, isolation, fixtures, migration tests |
| [data-privacy-retention](skills/data-privacy-retention/SKILL.md) | PII inventory, encryption, retention, erasure, GDPR basics |
| [data-pipelines](skills/data-pipelines/SKILL.md) | Idempotent batch and streaming jobs, backfills, data quality |

### DevOps and cloud

| Skill | What it does |
| --- | --- |
| [dockerfiles](skills/dockerfiles/SKILL.md) | Small, secure, cache-friendly container images |
| [ci-cd-pipelines](skills/ci-cd-pipelines/SKILL.md) | Fast, secure pipelines and safe deployment strategies |
| [infrastructure-as-code](skills/infrastructure-as-code/SKILL.md) | Terraform/OpenTofu, Bicep, Pulumi with reviewed plans and safe state |
| [kubernetes-deployments](skills/kubernetes-deployments/SKILL.md) | Production-ready manifests: probes, resources, security context |
| [cloud-cost-optimization](skills/cloud-cost-optimization/SKILL.md) | Make cost visible, then cut it with the biggest levers first |

### AI engineering

| Skill | What it does |
| --- | --- |
| [llm-integration](skills/llm-integration/SKILL.md) | Ship LLM features: structured output, retries, cost, prompt injection |
| [rag-systems](skills/rag-systems/SKILL.md) | Chunking, hybrid search, reranking and retrieval evaluation |
| [llm-evals](skills/llm-evals/SKILL.md) | Build eval sets and calibrated LLM judges, run them in CI |
| [building-agents](skills/building-agents/SKILL.md) | Agent loops, tool design, guardrails, and when not to use an agent |
| [ml-experiments](skills/ml-experiments/SKILL.md) | Baselines, correct splits, leakage checks, reproducibility |
| [mcp-servers](skills/mcp-servers/SKILL.md) | Build Model Context Protocol servers with good tools and safe auth |

### Meta

| Skill | What it does |
| --- | --- |
| [writing-skills](skills/writing-skills/SKILL.md) | Write your own skills that trigger reliably and change agent behavior |

## Contributing

New skills and fixes are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) for the rules and start from [template/SKILL.template.md](template/SKILL.template.md). Every skill must be plain Markdown, portable, correct, and tested on real tasks.

Found a wrong command or outdated advice? [Open an issue](https://github.com/reddygopalkrishna/developer-agent-skills/issues/new/choose). Accuracy problems are fixed first.

## License

[MIT](LICENSE)
