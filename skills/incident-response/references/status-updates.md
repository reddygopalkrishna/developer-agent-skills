# Status Update Templates

Draft these for a human to send. Never post them yourself.

Rules for every update:

- Lead with **impact** in plain language: who is affected and how.
- Say what is being done, not guesses about the cause. Do not name a root cause externally until it is confirmed.
- Always give the **time of the next update**, and keep that promise even if there is no news.
- Use UTC (add the local time zone of the main audience if helpful).
- Never include internal hostnames, customer names, secrets or personal data in external updates.

## Internal updates (incident channel or email)

### Initial

```
[SEV2] Checkout errors — INVESTIGATING
Impact: ~8% of checkout requests failing with 5xx since 14:02 UTC. All regions.
Status: Investigating. Recent deploy of checkout at 13:58 UTC is the lead suspect.
IC: <name>   Ops lead: <name>   Comms: <name>
Channel: #inc-<name>   Doc: <link>
Next update: 14:35 UTC
```

### Progress

```
[SEV2] Checkout errors — MITIGATING
Impact: error rate down from 8% to 1% after rollback at 14:15 UTC.
Status: Rollback complete; monitoring. Root cause investigation ongoing.
Actions in progress: <what, who>
Next update: 15:00 UTC
```

### Resolved

```
[SEV2] Checkout errors — RESOLVED
Impact: 14:02-14:24 UTC, up to 8% of checkout requests failed.
Resolution: rolled back checkout to the previous version. Error rate at baseline since 14:24 UTC.
Follow-up: postmortem by <date>, owner <name>. Tickets: <links>
```

## External updates (status page or customers)

Use the status page's standard states. A common set is Investigating, Identified, Monitoring, Resolved.

### Investigating

```
Title: Elevated errors during checkout
We are investigating reports of errors when completing checkout. Some customers
may be unable to place orders. We will provide an update by 14:35 UTC.
```

### Identified

```
We have identified the cause of the checkout errors and are applying a fix.
Some customers may still see errors when placing orders. Next update by 15:00 UTC.
```

### Monitoring

```
A fix has been applied and checkout error rates have returned to normal levels.
We are monitoring to make sure the issue is fully resolved. Next update by 15:30 UTC.
```

### Resolved

```
This incident has been resolved. Between 14:02 and 14:24 UTC, some customers were
unable to complete checkout. Orders placed outside this window were not affected.
We apologize for the disruption and will share a summary of what happened and the
steps we are taking to prevent it.
```

## Executive summary (for SEV1)

```
What happened: <one sentence>
Customer impact: <who, how many, how long>
Current state: <mitigated / resolved / ongoing>
Business impact: <orders, revenue, SLA credits — only if known>
Next steps: <postmortem date, key actions>
```
