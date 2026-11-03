# Security

## What this pack contains

Every skill is plain Markdown. There are no scripts, binaries, install hooks or network calls inside `skills/`, and CI rejects any non-Markdown file there. The only code in the repo is [`scripts/validate_skills.py`](scripts/validate_skills.py), a standard-library Python checker that is never installed with the skills.

Skills tell an agent what to do, so a harmful instruction is a security issue even without code. Examples:

- advice that would leak secrets or weaken security (for example disabling TLS checks or logging tokens),
- a destructive command without a "stop and ask the user first" gate,
- hidden or misleading instructions.

## Reporting a problem

- **Sensitive issues:** use GitHub's private vulnerability reporting on this repository (Security tab, then "Report a vulnerability").
- **Everything else:** open a normal issue.

Please include the skill name, the line, and what an agent could do wrong because of it. Confirmed issues are fixed before any other work.
