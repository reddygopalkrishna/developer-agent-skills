# STRIDE question bank

Ask these per element. Skip questions that don't apply; spend the time on boundary-crossing flows. Write each "yes, it could" as a specific threat in the table.

## Spoofing (authentication)

External entities and processes:

- How does this element prove who it is? Password, session cookie, token, API key, certificate, network location?
- Can a request reach this process without authentication (forgotten route, health/debug endpoint, internal port exposed)?
- Are credentials sent or stored where they can be stolen (URLs, logs, browser localStorage, client-side code)?
- For webhooks and callbacks: is the sender verified with a signature, and is the timestamp checked to stop replays?
- For service-to-service calls: does the callee verify the caller (mTLS, workload identity, signed token), or trust the network?
- Can a user change identity mid-session (session fixation, token swap, account linking abuse)?
- Can password reset, email change or MFA reset be used to take over an account?

## Tampering (integrity)

Processes, data stores and data flows:

- Can the client change values the server trusts (prices, roles, user IDs, tenant IDs, feature flags) in the body, query, headers or cookies?
- Does the server re-validate everything it receives, even from "internal" callers?
- Is data in transit protected (TLS everywhere, including internal hops and to the database)?
- Can a message on a queue or in a cache be written by something other than the intended producer?
- Can someone modify files the process loads (config, templates, plugins, uploaded files later served or executed)?
- Are build artifacts, container images and dependencies verified (pinned versions, digests, signatures)?
- Do database constraints back up application rules (foreign keys, unique, check constraints)?
- Is mass assignment possible (binding the whole request body onto a model with privileged fields)?

## Repudiation (accountability)

External entities, processes, and data stores that hold logs:

- If a user or admin performs a sensitive action, is there a record of who, what, when, from where, and on what object?
- Can the actor delete or edit that record?
- Are actions performed by services on behalf of users attributed to the user, not just the service?
- Are clocks synchronized so timelines can be reconstructed?
- Are audit logs kept long enough for disputes and investigations, and separate from debug logs?

## Information disclosure (confidentiality)

Processes, data stores and data flows:

- Does every read check that the caller may see **this specific object** (not just that they are logged in)?
- Can IDs be guessed or enumerated, and does that matter given the authz checks?
- Do error messages, stack traces or debug pages leak internals, queries or secrets?
- Are secrets, tokens or personal data written to logs, metrics labels, traces, analytics or crash reports?
- Are storage buckets, snapshots, backups and search indexes private by default?
- Are responses filtered to the fields the caller may see (no full user object in a public API)?
- Do caches or CDNs risk serving one user's response to another (missing `Vary`, cache key without user/tenant)?
- Is sensitive data encrypted at rest where required, and who holds the keys?
- Can timing or response differences reveal whether an account exists?
- Does a third party receive more data than it needs?

## Denial of service (availability)

Processes, data stores and data flows:

- Is there a size limit on every input (request body, upload, header, JSON depth, batch size)?
- Can one request trigger expensive work (unbounded queries, regex backtracking, image processing, report generation, fan-out)?
- Are there rate limits and quotas per user, tenant, API key and IP?
- Do all outbound calls have timeouts, and can retries amplify an outage?
- Can a single tenant or noisy job starve shared resources (DB connections, queue consumers, thread pools)?
- Can an attacker fill storage (logs, uploads, queues) or run up cloud cost?
- Is there a dependency whose outage takes this element down, and is there a fallback?

## Elevation of privilege (authorization)

Processes:

- Is authorization enforced on the server for every request, deny by default?
- Are admin and internal endpoints separated and protected by more than obscurity?
- Can a user grant themselves roles or permissions through any update path?
- Does the process run with more privileges than it needs (cloud IAM role, DB user, container running as root, broad API scopes)?
- Can user input reach a code-execution sink (shell, eval, deserialization, template rendering, SQL)?
- Can a lower-trust component instruct a higher-trust one (SSRF to internal services or cloud metadata endpoints, confused deputy)?
- In multi-tenant systems, is the tenant derived from the authenticated session rather than from user input?
- For AI features: can untrusted content (documents, web pages, tool results) instruct the model to take privileged actions?

## Boundary-specific prompts

| Boundary | Extra questions |
| --- | --- |
| Internet to edge | Bot and credential-stuffing protection? WAF or rate limits? TLS config? CORS allowlist? |
| Edge to internal services | Do internal services re-check identity, or trust anything from the edge? |
| Service to data store | Least-privilege DB user? Network restricted? Credentials rotated? |
| Tenant to tenant | Tenant ID from session? Row-level security? Per-tenant encryption or quotas needed? |
| Your system to third party | What data leaves? Contract and data processing terms? What if the provider is compromised or down? |
| Third party to your system | Inbound webhooks signed and replay-protected? Payload validated like any user input? |
| CI/CD to production | Who can change pipelines? Are deploy credentials short-lived? Are artifacts verified? |
