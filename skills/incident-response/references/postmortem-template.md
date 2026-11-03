# Postmortem Template

Blameless format. Describe systems, signals and decisions, not individual fault. Redact secrets and personal data.

```markdown
# Postmortem: <short title> (<YYYY-MM-DD>)

| | |
|---|---|
| Severity | SEV1 / SEV2 / SEV3 |
| Status | Draft / In review / Final |
| Authors | <names> |
| Incident commander | <name> |
| Date of incident | YYYY-MM-DD |
| Duration | <start UTC> to <end UTC> (<total>) |

## Summary

<3-5 sentences: what happened, impact, how it was resolved, the main cause.>

## Impact

- Users or customers affected: <number or percentage, which segments>
- Requests or transactions failed: <number or rate>
- Duration of user-visible impact: <minutes>
- Data loss or corruption: <none / details>
- SLO error budget consumed: <if known>
- Revenue, SLA credits or support tickets: <if known>

## Timeline (UTC)

| Time | Event |
|---|---|
| HH:MM | Triggering change or event |
| HH:MM | First alert / first customer report (detection) |
| HH:MM | Incident declared, IC assigned |
| HH:MM | Key observation or hypothesis |
| HH:MM | Mitigation applied |
| HH:MM | Impact ended |
| HH:MM | Incident resolved |

Time to detect: <detection - start>
Time to mitigate: <mitigation - start>
Time to resolve: <resolved - start>

## Root cause

<The technical chain of events, step by step, from trigger to user impact.
Precise enough that an engineer on another team could understand it.>

## Contributing factors

<Everything that made it possible, worse, or slower to fix. Examples:>
- Why the change was not caught before production (tests, review, staging gaps).
- Why detection took as long as it did (missing or noisy alerts).
- Why mitigation took as long as it did (no rollback path, missing runbook, access).

## What went well

- <Things to keep doing.>

## What went poorly

- <Without naming individuals.>

## Where we got lucky

- <Factors that limited impact by chance; these hide future risk.>

## Action items

| # | Action | Type | Owner | Due | Ticket |
|---|---|---|---|---|---|
| 1 | <specific, verifiable action> | Prevent / Detect / Mitigate / Process | <name> | YYYY-MM-DD | <link> |

## Supporting material

<Links to dashboards, graphs, log queries, chat transcript, related incidents.>
```

## Writing guidance

- **Specific action items.** "Add an alert on checkout 5xx above 2% for 5 minutes, paging checkout on-call" instead of "improve monitoring".
- **Balance the action types.** At least one item should prevent recurrence and one should make detection or mitigation faster.
- **Keep the count manageable.** A few items that will actually be done beat a long list that will not.
- **Ask "why" past the first answer.** "The deploy had a bug" leads to "why did tests and the canary not catch it?"
- **Separate the trigger from the root cause.** The trigger is the change or event; the root cause is the weakness that let the trigger cause user impact.
- **Review it** with the people involved before marking it final, and share it widely; postmortems are for learning.
