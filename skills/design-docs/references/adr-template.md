# ADR Template

Default format is Michael Nygard's. If the repo already uses MADR or another format, follow the repo.

## Template

```markdown
# ADR-NNNN: <Short noun phrase naming the decision>

- Status: Proposed | Accepted | Deprecated | Superseded by [ADR-NNNN](NNNN-title.md)
- Date: YYYY-MM-DD
- Deciders: <names or team>
- Related: <links to design doc, issue, previous ADRs>

## Context

<The forces at play: technical, product, organizational, deadlines. Neutral tone.
State the constraints and what problem needs a decision. No solution yet.>

## Decision

We will <decision, in active voice>.

<Key details of the decision that implementers need: scope, boundaries, what it does
not cover.>

## Consequences

Positive:
- <what becomes easier or better>

Negative:
- <what becomes harder, new costs, new risks>

Follow-up:
- <work this decision creates, with owner if known>
```

## Optional section for contested decisions (MADR style)

Add between Context and Decision when several options were seriously debated:

```markdown
## Considered options

1. <Option A> — <one-line summary>
2. <Option B> — <one-line summary>
3. Do nothing

| Criterion | Option A | Option B | Do nothing |
|---|---|---|---|
| <criterion> | | | |
```

## Worked example

```markdown
# ADR-0007: Use PostgreSQL for the orders service

- Status: Accepted
- Date: 2026-03-14
- Deciders: Orders team, Platform team
- Related: RFC-0012 Orders service extraction

## Context

The orders module is being extracted from the monolith into its own service.
Orders need multi-row transactions (order, line items, payment intent), ad-hoc
reporting queries from the finance team, and roughly 50 GB of data growing
about 2 GB per month (estimate from the last 12 months). The team runs
PostgreSQL in production for two other services and has on-call experience
with it. A managed PostgreSQL offering is available on our cloud provider.

## Decision

We will use the managed PostgreSQL service as the primary datastore for the
orders service. The orders service exclusively owns its schema; other services
access order data only through the orders API or published events.

## Consequences

Positive:
- Transactions across order, line items and payment intent are simple.
- Finance can query a read replica with SQL.
- Reuses existing operational knowledge, backups and monitoring.

Negative:
- Vertical scaling limits will need revisiting if write volume grows 10x.
- Reporting queries on the replica can lag the primary.

Follow-up:
- Set up a read replica for reporting (Platform team).
- Revisit this ADR if sustained write rate exceeds the threshold in RFC-0012.
```

## Superseding an ADR

1. Create the new ADR with the next number. In its Context, explain what changed since the old decision.
2. In the new ADR's header: `Related: supersedes [ADR-0007](0007-use-postgresql-for-orders.md)`.
3. In the old ADR, change only the status line: `Status: Superseded by [ADR-0019](0019-....md)`. Leave the rest untouched as history.

## Index

If the repo has many ADRs, keep a `docs/adr/README.md` listing number, title and status, newest first, and update it in the same change as each new ADR.
