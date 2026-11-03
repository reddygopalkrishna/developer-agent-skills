# Agent tool design checklist

Go through this for every tool the agent can call. Most agent failures trace back to a tool that was confusing, too broad, or returned too much.

## Purpose

- [ ] The tool does one task a person would describe in a sentence ("find open invoices for a customer"), not one raw API endpoint.
- [ ] No other tool overlaps with it. If two tools could both plausibly fit a request, merge them or make the descriptions say exactly when to use each.
- [ ] The total tool count is as small as the task allows. Every extra tool makes selection harder.

## Name

- [ ] Verb-first, specific, consistent across tools: `search_orders`, `get_order`, `refund_order`.
- [ ] Related tools share a prefix or namespace (`github_create_issue`, `github_list_issues`) when the agent has tools from several systems.

## Description

- [ ] Says what the tool does, when to use it, and when not to (and which tool to use instead).
- [ ] Explains non-obvious behavior: limits, ordering, what "not found" looks like, side effects.
- [ ] Includes an example call when parameters are tricky.
- [ ] Written for someone with no knowledge of your internal systems; no unexplained internal jargon or abbreviations.

## Parameters

- [ ] JSON Schema with types, `required`, `enum` for fixed choices, formats for dates/emails/URLs, min/max for numbers.
- [ ] Each parameter has a description with an example value.
- [ ] Accepts identifiers the model will naturally have (names, emails, file paths) and resolves internal IDs itself, or returns candidates when ambiguous.
- [ ] Few parameters, sensible defaults. No parameters the model can't possibly know.
- [ ] Dates and times have an explicit format and time zone.

## Results

- [ ] Returns only what the agent needs for the next step: relevant fields, not whole records.
- [ ] Large results are paginated or truncated, with the total count and how to get more ("showing 20 of 312; pass page=2").
- [ ] Optional `detail` / `verbosity` parameter when the agent sometimes needs more.
- [ ] Human-readable text or compact JSON. Readable names alongside IDs.
- [ ] Very large artifacts (files, logs, datasets) are stored outside the context and returned as a handle plus a summary.

## Errors

- [ ] Errors say what went wrong and how to fix it: "date must be YYYY-MM-DD, got '03/15'", "no project named 'web'; available: web-app, web-site".
- [ ] Errors are returned to the model as tool results, not raised as crashes that end the run.
- [ ] Transient failures (timeouts, rate limits) are retried inside the tool with a bound, or reported as retryable.

## Safety

- [ ] Read and write operations are separate tools.
- [ ] Write tools are idempotent where possible (idempotency key, upsert) so retries don't duplicate effects.
- [ ] Destructive or outward-facing tools (delete, send, pay, deploy, change permissions) require human approval before running, enforced in code.
- [ ] Authorization is checked server-side against the real user; the tool never trusts a user ID or role the model passes in.
- [ ] Inputs are validated: paths stay inside allowed directories, queries are parameterized, URLs are on an allowlist if the tool fetches them.
- [ ] Results from untrusted sources are marked as such; content in them is not treated as instructions.
- [ ] Every call is logged with arguments, result size, duration and outcome.

## Test

- [ ] A few eval tasks exercise the tool, including ambiguous inputs and error paths.
- [ ] Read trajectories after changing a description: does the agent now pick it at the right time and pass correct arguments?
