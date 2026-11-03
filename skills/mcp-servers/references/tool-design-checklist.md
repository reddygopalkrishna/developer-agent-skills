# MCP tool design checklist

Run every tool through this before shipping. Check the current MCP specification for exact field names; they are noted here where they matter.

## Scope

- [ ] The tool maps to a task a user would ask for, not a single internal endpoint.
- [ ] It doesn't overlap with another tool on this server. If it might, the descriptions say exactly when to use each.
- [ ] The server's total tool count is small. Each new tool earns its place.
- [ ] Read-only and write operations are separate tools.

## Name

- [ ] Short, verb-first, `snake_case` or another consistent style: `search_tickets`, `get_ticket`, `add_ticket_comment`.
- [ ] Unique and recognizable when the client shows tools from many servers together (consider a service prefix).

## Description

- [ ] First sentence: what the tool does and what it returns.
- [ ] When to use it and when not to (name the alternative tool).
- [ ] Side effects stated plainly ("Creates a comment visible to the customer").
- [ ] Limits: max results, rate limits, which data it can see.
- [ ] No secrets, internal hostnames or instructions aimed at manipulating the model.

## Input schema

- [ ] JSON Schema object with `type`, `properties`, `required`.
- [ ] Every property has a description and, if helpful, an example.
- [ ] Enums for fixed choices; `format` for dates, emails, URIs; min/max for numbers and lengths.
- [ ] Uses identifiers the model can know (names, emails, URLs, paths). Resolve internal IDs inside the tool, or return candidates when ambiguous.
- [ ] Pagination via a `cursor` (or page) parameter and a `limit` with a sensible default and maximum.
- [ ] The server validates input again in code and returns a clear error on violation.

## Result

- [ ] Concise: only the fields the model needs, readable labels alongside IDs.
- [ ] Bounded: large lists are paginated with a next cursor and a total or "more available" note; long text is truncated with a note on how to get the rest.
- [ ] Consistent shape across calls and across related tools.
- [ ] If clients consume it programmatically and the targeted spec version supports it, an output schema with structured content is provided as well as readable text.
- [ ] Untrusted third-party content is returned as data, clearly separated from the server's own text.

## Errors

- [ ] Execution failures come back as a tool result with the error flag set (`isError: true`) and a message that tells the model how to fix the call ("status must be one of: open, pending, closed").
- [ ] Not-found and permission-denied cases are distinguishable and explained.
- [ ] Downstream timeouts and rate limits produce a clear, retryable message; the tool doesn't hang.
- [ ] No stack traces, secrets or internal details leak in error messages.

## Safety

- [ ] Annotations set honestly (read-only, destructive, idempotent, open-world hints) so clients can ask for confirmation. The server still enforces safety itself.
- [ ] Destructive or outward-facing tools are narrow, support a preview/dry-run where practical, and are idempotent (idempotency key) when retries could duplicate effects.
- [ ] Authorization checked per call against the authenticated user, not against arguments.
- [ ] Inputs that reach SQL, shells, file paths or URLs are parameterized, confined or allowlisted.
- [ ] Each call is logged (to stderr or a log sink, never stdout on stdio) with tool name, user, duration and outcome, without logging secrets.

## Testing

- [ ] Called in the MCP Inspector with valid input, each kind of invalid input, empty results, and large results.
- [ ] Tried with a real client and model on several realistic requests; the model picks this tool at the right time with correct arguments.
- [ ] Automated tests cover handlers directly (unit tests) and at least one end-to-end session through the SDK's client.
