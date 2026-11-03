# API Review Checklist

Use this when reviewing an API pull request or finishing a design. Report each failed item with the endpoint, the problem, and the fix. Mark items "n/a" rather than skipping them silently.

## Consistency

- [ ] Naming, casing and URL style match the existing API (read two existing endpoints before judging).
- [ ] Error format is the same problem-details shape used everywhere else.
- [ ] Pagination style matches other collection endpoints.
- [ ] Auth scheme and scopes follow the existing pattern.

## Resources and methods

- [ ] Paths are plural nouns; no verbs except deliberate action sub-resources.
- [ ] Nesting is at most one level and reflects real ownership.
- [ ] GET, HEAD and OPTIONS have no side effects.
- [ ] PUT replaces the whole resource; PATCH declares its format (merge patch or JSON Patch).
- [ ] DELETE is idempotent.
- [ ] POST that creates returns 201 with `Location`.

## Requests

- [ ] Every field has a type, a format where relevant (date-time, uuid, email), and a documented required/optional status.
- [ ] String lengths, numeric ranges and array sizes are bounded.
- [ ] Unknown fields: the behavior (ignore or reject) is defined and consistent.
- [ ] Money uses minor units or decimal strings plus a currency code.
- [ ] Timestamps are RFC 3339 with an explicit offset (prefer UTC).
- [ ] Request body size is limited at the server or gateway.

## Responses

- [ ] Status codes are specific (no blanket 200 or blanket 400).
- [ ] No internal fields leak (database IDs that are not public, password hashes, internal flags, hostnames).
- [ ] Enums are strings and documented as extensible; clients are told to tolerate unknown values.
- [ ] Nullable vs absent is defined for each optional field.
- [ ] Large or sensitive fields are only returned when needed (consider `fields=` or `expand=` parameters).

## Errors

- [ ] All 4xx/5xx use `application/problem+json` with `type`, `title`, `status`.
- [ ] Each `type` is a stable, documented identifier.
- [ ] Validation errors list every failing field with a JSON pointer or field path.
- [ ] 5xx responses contain no stack traces, SQL or internal details; they include a correlation or trace ID.
- [ ] 401 vs 403 vs 404 is chosen deliberately (404 when the resource's existence is itself sensitive).

## Collections

- [ ] Every list endpoint paginates; `limit` has a default and a maximum.
- [ ] Sort order is deterministic (ID as tiebreaker).
- [ ] Sortable and filterable fields are allowlisted.
- [ ] Empty results return 200 with an empty array, not 404.

## Safety under retries and concurrency

- [ ] Non-idempotent POSTs with real-world effects (payments, messages, orders) accept an `Idempotency-Key` (an IETF draft header, widely adopted).
- [ ] The idempotency record is written atomically with the side effect.
- [ ] Updates that can race use `ETag` + `If-Match` (412 on mismatch).
- [ ] Long-running work returns 202 and a status resource instead of blocking.

## Limits and abuse

- [ ] Rate limits exist per credential; 429 responses include `Retry-After`.
- [ ] Rate-limit headers follow the existing convention (`RateLimit`/`RateLimit-Policy` are an IETF draft; `X-RateLimit-*` is the common legacy form).
- [ ] Expensive endpoints (search, export, bulk) have tighter limits or async processing.

## Security

- [ ] Every endpoint enforces authorization on the specific object (no IDOR: changing an ID in the path must not expose another tenant's data).
- [ ] Request bodies bind only allowlisted fields (no mass assignment of `role`, `ownerId`, `price`).
- [ ] Sensitive data is never in URLs or query strings (they end up in logs).
- [ ] CORS is restricted to known origins when cookies are used.
- [ ] Webhook payloads are signed and receivers are told how to verify them.

## Compatibility

- [ ] A breaking-change diff was run against the previous spec (for example `oasdiff breaking`).
- [ ] No field, endpoint or enum value was removed or renamed in the same version.
- [ ] No optional field became required; no validation got stricter; no default changed.
- [ ] Deprecations are marked in the spec and announced, with a sunset date.

## Contract and docs

- [ ] OpenAPI is updated in the same PR as the code, with request and response examples.
- [ ] Every error response is listed per operation.
- [ ] The spec passes the repo's linter.
- [ ] Contract tests or schema validation in tests check responses against the spec.

## Tests

- [ ] Happy path, validation failure, unauthenticated, unauthorized, not found.
- [ ] Pagination: first page, last page, empty, invalid cursor.
- [ ] Idempotent retry returns the same response; conflicting reuse of a key is rejected.
- [ ] Conditional update with a stale ETag returns 412.
