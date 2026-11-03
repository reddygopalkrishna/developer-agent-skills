# Design Doc / RFC Template

Copy this into the repo's design doc folder and fill every section. Delete the guidance in *italics*. If a section does not apply, keep the heading and write one line saying why.

```markdown
# RFC-NNNN: <Short title that names the change>

| | |
|---|---|
| Author(s) | <names> |
| Status | Draft / In review / Accepted / Rejected / Superseded by RFC-NNNN |
| Created | YYYY-MM-DD |
| Last updated | YYYY-MM-DD |
| Reviewers | <names or teams, with the area each one covers> |
| Decision maker | <one name> |
| Review deadline | YYYY-MM-DD |

## Summary

*3-5 sentences. The problem, what you propose, what it costs, and what you need from reviewers.*

## Context

*Current state of the system. Why this matters now. Evidence: metrics, incidents, customer requests, deadlines (for example an end-of-life date). Link sources.*

## Goals

*Measurable outcomes. Each goal should be testable after launch.*

- G1: <e.g. p99 latency of checkout under 300 ms at 2,000 req/s>
- G2: ...

## Non-goals

*Things a reader might reasonably expect that this work will not do.*

- NG1: ...

## Proposal

### Overview

*One paragraph and one diagram (C4 context or container level).*

### Components and responsibilities

*Each new or changed component, what it owns, who operates it.*

### Interfaces

*APIs, events, schemas. Show request/response or event shapes. Note versioning and backward compatibility.*

### Data model

*New or changed tables, indexes, retention, ownership. Who is the source of truth for each entity?*

### Key flows

*Sequence diagrams for the main paths and at least one failure path.*

### Failure modes

| Failure | Effect | Detection | Handling |
|---|---|---|---|
| <dependency X slow/down> | ... | ... | ... |

### Capacity and performance

*Back-of-envelope math: request rate (average and peak), data size and growth, fan-out, latency budget per hop. Mark estimates.*

## Alternatives considered

| Criterion | Proposal | Alternative A | Alternative B | Do nothing |
|---|---|---|---|---|
| <criterion> | | | | |

*For each alternative, two or three sentences on why it was not chosen.*

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|

## Security, privacy and compliance

- Data classification of data handled:
- Authentication and authorization model:
- PII or secrets: where they flow, are stored, are logged (they should not be):
- New attack surface and main threats:
- Compliance requirements (e.g. retention, residency, audit):

## Rollout and migration

1. Phase 1: ... (behind flag `<name>`, internal users only)
2. Phase 2: ... (percentage ramp, success criteria to proceed)
3. Phase 3: ... (remove old path)

- Backward compatibility:
- Data migration and backfill:
- **Rollback plan** (for each phase, including data):

## Observability and operations

- Metrics and SLOs:
- Alerts (condition, severity, who is paged):
- Dashboards:
- Runbook link:
- Operating team / on-call:

## Cost

*Infrastructure (monthly, with assumptions), build effort, ongoing maintenance.*

## Open questions

| Question | Owner | Due |
|---|---|---|

## Appendix

*Detailed calculations, benchmarks, prior art, glossary.*
```

## Filling tips

- Write **Summary** last, but put it first.
- If **Alternatives** has only one column besides the proposal, you have not looked hard enough.
- Every **Goal** should have a matching metric in **Observability**.
- Every **Risk** rated high impact should have a matching step in **Rollout** or **Failure modes**.
- If the **Rollback plan** says "restore from backup", estimate how long that takes and how much data is lost.
