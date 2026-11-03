# Detailed review checklist

Use this as a question bank, not a form to fill in. Go deep on the areas the change actually touches.

## Correctness

- Does the code do what the PR description and the issue say? Is anything in the description missing from the code?
- What happens with: empty collections, null/None/undefined, empty strings, whitespace-only strings, zero, negative numbers, maximum values, very long inputs, duplicates, non-ASCII text?
- Off-by-one: inclusive vs exclusive ranges, pagination boundaries, last element, fence posts in loops.
- Time: time zones, DST transitions, month-end, leap years, clock skew between machines, timestamps stored without zone.
- Money and numbers: floating point used for currency, rounding mode, integer overflow, division by zero, unit mismatches (ms vs s, cents vs units).
- Ordering: does the code assume an order that is not guaranteed (hash map iteration, database rows without `ORDER BY`, parallel results, message delivery)?
- State: can the object be in a state the code does not handle? Are state transitions validated?
- Feature flags: does the code behave correctly with the flag on, off, and while it flips?

## Error handling and resilience

- Are errors caught at a level that can do something useful? Are they rethrown or wrapped with context, not swallowed?
- Are resources (files, connections, locks, transactions) released on every path, including errors?
- If step 3 of 5 fails, is the system left consistent? Is there a transaction, a compensating action, or an idempotent retry?
- Do retries have a limit, backoff and jitter? Is the retried operation safe to repeat?
- Do outbound calls have timeouts?
- Are error messages to users free of internals (stack traces, SQL, file paths)?

## Concurrency

- Shared mutable state accessed from multiple threads, goroutines, requests or workers?
- Check-then-act sequences (read, decide, write) without a lock, transaction or atomic operation?
- Unique constraints enforced in the database, not just in application code?
- Async functions called without `await`, or promises/tasks not handled?
- Locks acquired in a consistent order? Held while doing I/O?
- Background jobs: what happens if two instances run at once, or a job runs twice?

## Security

- Every new endpoint or handler: is authentication required, and is authorization checked for the specific object (not just "is logged in")?
- Inputs validated for type, length, range and format at the boundary?
- SQL built with parameters, never string concatenation? Shell commands built with argument arrays, never interpolated strings?
- File paths from user input normalized and confined to an allowed directory?
- HTML output escaped by the template engine; any "raw"/"unsafe" rendering justified?
- Server-side fetching of user-supplied URLs restricted (SSRF)?
- Deserialization of untrusted data with safe formats and libraries?
- Secrets: none in code, config committed to the repo, logs, error messages or client bundles?
- Cryptography: standard libraries, no home-made schemes, no MD5/SHA-1 for security purposes, secure random for tokens?
- New dependencies: maintained, widely used, license compatible, pinned in the lockfile?
- Logs and analytics: no passwords, tokens, full card numbers or unnecessary personal data?

## Data and migrations

- Is the schema change backward compatible with the previous version of the code, which keeps running during a rolling deploy?
- Does the migration lock or rewrite a large table? Is an index created without blocking writes where the database supports it?
- Are backfills batched and resumable?
- Are destructive changes (drop column/table, delete rows) separated from the code change and reversible or backed up?
- Are new columns' nullability and defaults correct for existing rows?
- Is there a rollback plan, and does the down migration actually work?

## API and compatibility

- Removed or renamed fields, endpoints, parameters or enum values?
- Changed defaults, status codes, error shapes, pagination behavior or sort order?
- Changed event, message or file formats that other services consume?
- Library or SDK changes: public method signatures, exceptions thrown, semantic versioning?
- Is the change documented (changelog, API docs, migration notes) when it affects others?

## Performance

- Database or network calls inside loops (N+1)?
- Unbounded queries or responses (missing `LIMIT`, pagination, or streaming)?
- New queries supported by indexes? Check the filter, join and sort columns.
- Large in-memory collections, repeated serialization, or quadratic algorithms on input that can grow?
- Blocking I/O on an event loop, UI thread or async path?
- Caching: correct key (includes tenant, user, locale, version), invalidation, TTL, stampede protection?

## Tests

- Is the new behavior tested, including error paths and the edge cases above?
- Would the tests fail if the implementation were wrong? (Mentally break the code: does a test catch it?)
- Do tests assert outcomes rather than internal calls?
- Are tests deterministic: no real network, fixed clocks, no dependence on order, no sleeps?
- For bug fixes: is there a regression test that reproduces the original bug?

## Observability and operations

- Can an on-call engineer tell from logs and metrics that this feature is failing?
- Are errors logged once (not at every layer) with identifiers that allow tracing a request?
- New configuration: has defaults, is documented, and fails fast when invalid?
- Rollout: feature flag, gradual rollout, or a way to turn it off?

## Readability and maintainability

- Do names describe behavior? Would a newcomer understand the code without the PR description?
- Is there dead code, commented-out code, or leftover debug output?
- Is duplicated logic a real duplication worth extracting, or coincidentally similar code?
- Do comments explain *why* (constraints, decisions), not *what*?

## Language-specific gotchas

### JavaScript / TypeScript

- Missing `await` on a promise-returning call; floating promises whose rejection is never handled.
- `forEach` with an `async` callback does not wait; use `for...of` with `await` or `Promise.all`.
- `==` instead of `===`; truthiness checks that treat `0` or `""` as missing (use `??` instead of `||` for defaults).
- Mutating arrays or objects that are shared or held in framework state (`sort()` and `reverse()` mutate in place).
- TypeScript: `any`, non-null assertions (`!`) and `as` casts that hide real nullability; unvalidated `JSON.parse` results typed as trusted.
- Dates: `new Date("2024-01-02")` parses as UTC while other formats may parse as local time.

### Python

- Mutable default arguments (`def f(items=[])`).
- Late-binding closures in loops (lambdas capturing the loop variable).
- `is` used for value comparison instead of `==` (fine only for `None`, `True`, `False`).
- Bare `except:` or `except Exception:` that swallows errors, including in cleanup code.
- Naive vs timezone-aware `datetime` mixed.
- Blocking calls inside `async def` functions.

### Java / Kotlin

- `equals` overridden without `hashCode` (or vice versa).
- Resources not closed: use try-with-resources (Java) or `use {}` (Kotlin).
- `Optional.get()` without a presence check; `Optional` used for fields or parameters.
- Checked exceptions wrapped and lost without the cause.
- Mutable static state; non-thread-safe classes (such as `SimpleDateFormat`) shared across threads.
- Kotlin: `!!` on platform types from Java APIs.

### Go

- Ignored errors (`_ =` or unchecked returns), and errors wrapped without `%w` so callers cannot use `errors.Is`/`errors.As`.
- Writes to a nil map panic.
- Goroutines that can block forever (leak) because nobody reads their channel or the context is not respected.
- `defer` inside a loop delays every release until the function returns.
- Loop variable capture: before Go 1.22, closures in `for` loops shared one variable; from Go 1.22 (when the module's `go` directive is 1.22 or later) each iteration has its own. Check the module's Go version.
- Missing `ctx` propagation to outbound calls, so timeouts and cancellation do not apply.

### C# / .NET

- `async void` methods (except event handlers): exceptions crash the process and cannot be awaited.
- `.Result` or `.Wait()` on tasks, which can deadlock and blocks threads.
- `IDisposable` objects not disposed (`using`); `HttpClient` created per request instead of reused or created via `IHttpClientFactory`.
- `DateTime.Now` vs `DateTime.UtcNow`; prefer `DateTimeOffset` or an injected `TimeProvider`.
- LINQ queries enumerated multiple times, or evaluated client-side by accident in Entity Framework.

### SQL

- `= NULL` instead of `IS NULL`; `NOT IN` with a subquery that can return NULL (returns no rows).
- Implicit type conversions that prevent index use (comparing a string column to a number).
- Missing `ORDER BY` when the result order matters, especially with `LIMIT`/`OFFSET`.
- `SELECT *` in application code that breaks when columns change.
- Read-modify-write without row locks or optimistic concurrency.
