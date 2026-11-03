# Contributing

Thanks for helping. This pack has one promise to its users: **every skill is something a senior engineer would trust an agent to follow in a real codebase.** The rules below exist to keep that promise.

## Ground rules

1. **Plain Markdown only.** Skills are instructions, not code. No executable scripts, no network calls, no install hooks. Anyone must be able to audit a skill by reading it. (If a skill truly needs a script, open an issue first.)
2. **Correct beats complete.** Every command, flag, threshold and API in a skill must be real and current. If you are not sure, leave it out or say how to check (`--help`, official docs).
3. **Portable.** Skills must work in any agent that reads the open Agent Skills format (Claude Code, Codex, Cursor, Copilot, Gemini CLI, Antigravity, ...). Do not mention tools that exist only in one agent. Say "run", "search the codebase", "read the file".
4. **Safe by default.** Anything destructive or outward-facing (dropping data, force-pushing, deploying, deleting resources, sending messages) must tell the agent to stop and get explicit confirmation first.
5. **No marketing.** Don't recommend a paid product unless the skill is about it. Name the category first ("a profiler such as ...").

## Skill layout

```
skills/<skill-name>/
├── SKILL.md              # required, 120-300 lines, hard limit 450
└── references/           # optional deep material, one level deep
    └── <topic>.md        # each file under ~300 lines
```

- The folder name and the `name` field must match.
- Names: lowercase letters, digits and single hyphens, at most 64 characters.
- Link every reference file from `SKILL.md` with a relative link, and say *when* to open it ("Read [references/postgres.md](references/postgres.md) when the database is PostgreSQL").

## Frontmatter

Exactly these three fields, each on one line:

```yaml
---
name: database-migrations
description: Plans and writes zero-downtime database schema migrations (expand/contract, safe indexes, batched backfills, rollback). Use when adding, renaming or dropping columns or tables, changing types or constraints, adding indexes, or backfilling data on a live database.
license: MIT
---
```

The `description` is the most important line in the skill: agents read only this to decide whether to load it.

- Third person. First say what the skill does, then `Use when ...` with concrete triggers and the words users actually type.
- Optionally add `Not for ...` to stop it firing on nearby tasks.
- Aim for 200-500 characters. Hard limit 1024. No `<` or `>` characters.

## Body structure

Write to the agent, in the imperative. Use this order and drop sections that add nothing:

```markdown
# <Title>

<1-3 sentences: the core principle the agent must not violate.>

## When to use / when not to
## Workflow            <- numbered steps, each one concrete and checkable
## <Decision tables, checklists, rules specific to the topic>
## Anti-patterns       <- the mistakes agents and humans actually make
## Done when           <- objective exit criteria
## References          <- links to references/*.md with when to read each
```

Style:

- Concrete over generic. "Run `EXPLAIN (ANALYZE, BUFFERS)` and look for Seq Scan on large tables" beats "check the query plan".
- Cover the common ecosystems (JS/TS, Python, Java/Kotlin, Go, C#/.NET, Rust) where commands differ. Put long per-stack tables in `references/`.
- Prefer decision tables and checklists over prose.
- Cite standards by name where they settle a question (WCAG 2.2, RFC 9457, OpenTelemetry, Core Web Vitals).
- No invented statistics.

## Checks

Run before opening a PR:

```bash
python scripts/validate_skills.py
```

On Windows, use `py -3 scripts/validate_skills.py` if `python` is not on your PATH. It checks the frontmatter, name rules, length limits, broken reference links, and that each skill is listed in `.claude-plugin/marketplace.json` and the README. CI runs the same script.

## Adding a skill

1. Copy `template/SKILL.template.md` to `skills/<your-skill>/SKILL.md`. (The template is not named `SKILL.md` so installers don't pick it up as a real skill.)
2. Write it following the rules above.
3. Add it to the right plugin in `.claude-plugin/marketplace.json` and to the table in `README.md`.
4. Run the validator, then test the skill on at least two real tasks in at least one agent. Say in the PR which tasks and agents you used.
