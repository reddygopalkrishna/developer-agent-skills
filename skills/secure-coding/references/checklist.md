# Security Review Checklist by OWASP Top 10 Category

Categories are named rather than numbered because the numbering changes between OWASP Top 10 editions (2021, 2025). For example, SSRF is its own category in 2021 and part of broken access control in later editions. Check the current edition at owasp.org if you need the official numbering for a report.

For each finding record: **category, severity, file:line, how an attacker would exploit it, the fix, and the test that proves it.** Mark items that don't apply as "n/a".

## Broken access control

- [ ] Every route has an explicit auth requirement; unauthenticated access is opt-in per route, not opt-out.
- [ ] Each object fetch or update is scoped to the caller (`WHERE owner_id = :me` / tenant filter), including list, export, search and bulk endpoints.
- [ ] IDs in paths, query strings, bodies and headers are never trusted for authorization.
- [ ] Admin and internal endpoints check roles server-side and are not reachable from the public network unless intended.
- [ ] Request binding uses DTOs or allowlists; fields such as `role`, `isAdmin`, `tenantId`, `ownerId`, `price`, `status` cannot be set by clients that shouldn't set them.
- [ ] Field-level sensitivity is enforced in responses (no hidden fields "the UI doesn't show").
- [ ] Redirect targets and `returnUrl` parameters are validated against an allowlist.
- [ ] CORS allowlists exact origins; credentials are never combined with reflected or wildcard origins.
- [ ] File and object-storage access uses short-lived signed URLs scoped to one object.
- [ ] Tests: user A cannot read, update or delete user B's resources; a tenant cannot reach another tenant's data.

## Server-side request forgery

- [ ] Every server-side fetch of a user-influenced URL is listed.
- [ ] Scheme allowlist (`https`, optionally `http`); host allowlist where the feature allows it.
- [ ] The resolved IP is checked against private, loopback, link-local, metadata and IPv6 local ranges, and the connection goes to that validated IP.
- [ ] Redirects are disabled or each hop is re-validated.
- [ ] The fetcher runs without cloud credentials, with egress restrictions; IMDSv2 is enforced on AWS.
- [ ] Response bodies and errors from internal fetches are not reflected to users.

## Cryptographic failures

- [ ] Sensitive data is classified, and only what is needed is stored. Retention limits exist.
- [ ] TLS 1.2+ for all external and internal traffic; certificate validation is never disabled.
- [ ] Encryption at rest for sensitive stores; keys are kept in a KMS or secret manager, not next to the data.
- [ ] AEAD (AES-GCM, ChaCha20-Poly1305) with unique nonces; no ECB, no custom constructions, no homemade key derivation.
- [ ] Passwords are hashed with Argon2id, scrypt or bcrypt (PBKDF2 for FIPS) using current OWASP parameters.
- [ ] Tokens, IDs and secrets come from a CSPRNG; comparisons are constant-time.
- [ ] No sensitive data in URLs, query strings, logs, analytics events or client-side storage.

## Injection

- [ ] All SQL is parameterized; dynamic identifiers go through an allowlist.
- [ ] ORM raw-query APIs are reviewed individually (see the table in SKILL.md).
- [ ] No shell invocation with string-built commands; argument arrays only, with `--` before user arguments.
- [ ] NoSQL queries reject operator injection (type-checked inputs, schema validation).
- [ ] Templates never render user input as template source (server-side template injection).
- [ ] Output encoding matches the context: HTML body, attribute, URL, JavaScript, CSS.
- [ ] Every framework escape hatch (`dangerouslySetInnerHTML`, `v-html`, `|safe`, `Html.Raw`, ...) is justified, and its input is sanitized with a maintained sanitizer.
- [ ] User-supplied URLs in links and embeds are scheme-checked.
- [ ] HTTP header values and log lines strip or escape CR/LF.
- [ ] XML parsers have external entities and DTDs disabled.

## Insecure design

- [ ] There is a short threat model for new features that move money, change permissions, handle PII, or call out to user-supplied URLs.
- [ ] Business limits are enforced server-side: quantities, amounts, rate of actions, number of attempts.
- [ ] Workflows cannot be skipped or replayed (for example paying, then editing the cart; reusing a coupon; reusing a one-time token).
- [ ] Race conditions on balances, inventory and coupons are handled with transactions, row locks, or unique constraints.
- [ ] Tenant isolation is designed in (row-level security, scoped repositories), not left to each query author.

## Security misconfiguration

- [ ] Debug mode, stack traces, directory listing and sample apps are off in production.
- [ ] Default credentials are changed; admin consoles and metrics endpoints are not public.
- [ ] Security headers are set: HSTS, `nosniff`, CSP (including `frame-ancestors`), `Referrer-Policy`, `Permissions-Policy`.
- [ ] Cookies are `HttpOnly`, `Secure` and `SameSite`.
- [ ] Cloud storage buckets are private by default; IAM roles follow least privilege.
- [ ] Containers run as non-root with a read-only file system where possible; no secrets baked into images.
- [ ] IaC is scanned (for example `trivy config .`).

## Vulnerable components and software supply chain

- [ ] Lockfiles are committed; CI installs from them reproducibly.
- [ ] A vulnerability audit runs in CI for every ecosystem in the repo; there is a policy for which severities block a merge.
- [ ] New dependencies are reviewed: correct package name (no typosquatting), maintained, reasonable install scripts, license acceptable.
- [ ] CI actions and base images are pinned to SHAs or digests; automated update PRs (Dependabot/Renovate) are enabled.
- [ ] Build artifacts are produced in CI, not on laptops; signing and SBOM generation exist where the organization requires them.
- [ ] Unused dependencies are removed.

## Identification and authentication failures

- [ ] Authentication uses the framework or an identity provider, not custom code.
- [ ] Login, signup, password reset and MFA endpoints are rate-limited, with progressive lockout or delays.
- [ ] Error messages don't reveal whether an account exists.
- [ ] Session IDs rotate on login and privilege change; sessions are invalidated on logout and password change; idle and absolute timeouts exist.
- [ ] JWT validation pins the algorithm and checks signature, `exp`, `nbf`, `iss` and `aud`; no secrets in claims; keys rotate.
- [ ] Reset and magic-link tokens are random, single-use, short-lived and stored hashed.
- [ ] MFA is available, and required for admins.
- [ ] Credential-stuffing defenses exist (rate limits, breached-password checks) where the risk justifies them.

## Software and data integrity failures

- [ ] No native deserialization of untrusted data (`pickle`, `ObjectInputStream`, `BinaryFormatter`, `unserialize`, `Marshal`, unsafe YAML loaders).
- [ ] Webhooks and callbacks verify signatures over the raw body, with timestamp checks for replay.
- [ ] Auto-update and plugin mechanisms verify signatures.
- [ ] CI/CD pipelines: protected branches, required reviews, secrets scoped to the jobs that need them, and no untrusted code running with deploy credentials (watch pull-request workflows from forks).

## File handling

- [ ] Upload size limits are enforced at the proxy and in the app.
- [ ] File type is checked by content; the stored filename is server-generated; files are stored outside the web root.
- [ ] Downloads are served with `Content-Disposition: attachment` and `nosniff`; user-uploaded HTML or SVG is never served inline from the main origin.
- [ ] Path inputs are canonicalized and confined to a base directory; archive extraction checks every entry path.
- [ ] Image and document processing libraries are up to date (they are common RCE vectors).

## Security logging and alerting failures

- [ ] Auth successes and failures, access denials, permission changes, admin actions and high-value transactions are logged with actor, action, target, time and source.
- [ ] Logs contain no passwords, tokens, keys, session IDs or full card numbers.
- [ ] Logs are structured, centrally collected and tamper-resistant (append-only or a separate account).
- [ ] Alerts exist for auth-failure spikes, access-denial spikes, and admin actions outside normal patterns.
- [ ] Incident contacts and a response runbook exist.

## Mishandling of exceptional conditions

- [ ] Errors fail closed: an exception in an authorization or validation path denies the request.
- [ ] Users get generic error messages; details go to logs with a correlation ID.
- [ ] Partial failures in multi-step operations leave consistent state (transactions or compensation).
- [ ] Resource exhaustion is handled: timeouts, size limits on bodies and fields, and limits on regex input (ReDoS), pagination and decompression (zip bombs).

## Secrets

- [ ] A secret scan (gitleaks or similar) runs on the full history and in CI; push protection is on where available.
- [ ] No secrets in code, committed config, images, client bundles, logs or error messages.
- [ ] Secrets come from a secret manager or the environment at runtime, with least-privilege scopes.
- [ ] Any secret ever exposed has been rotated, not just deleted from history, and the user has been told.
