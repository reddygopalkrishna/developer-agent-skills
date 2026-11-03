# GraphQL and gRPC Notes

Use this when the interface is GraphQL or gRPC, or when choosing between them and REST. The idempotency, timeout and authorization rules in SKILL.md still apply. Only the transport changes.

## Choosing

| Question | REST | GraphQL | gRPC |
|---|---|---|---|
| Who calls it? | Anyone, including third parties | Your own web and mobile clients | Your own services |
| Browser support | Native | Native (over HTTP POST/GET) | Needs gRPC-Web or Connect plus a proxy or compatible server |
| HTTP caching / CDN | Native | Hard; needs persisted queries over GET | No |
| Streaming | SSE, WebSockets | Subscriptions (WebSocket-based in practice) | First-class (server, client, bidirectional) |
| Schema and codegen | OpenAPI (optional discipline) | Schema is mandatory | `.proto` is mandatory; strong codegen |
| Main operational risk | Over-/under-fetching, chatty clients | Expensive queries, N+1 resolvers | Breaking proto changes, missing deadlines |

Default to REST for public APIs. Choose GraphQL when several client types need different shapes of the same graph and a team will own the schema. Choose gRPC for internal service-to-service traffic where latency, streaming or strict contracts matter.

## GraphQL

### Schema design

- Design the schema around client use cases, not database tables.
- Use Relay-style cursor connections for lists: `edges { node cursor }` and `pageInfo { hasNextPage endCursor }`, with `first`/`after` arguments. Cap `first`.
- Mutations take a single `input` argument of an input type and return a payload type. This lets you add fields later without breaking callers.
- Put expected domain errors in the payload, for example `userErrors: [{ field, message, code }]` or a result union (`CreateOrderResult = Order | InsufficientStock`). Use the top-level `errors` array for unexpected failures.
- Fields are nullable by default. Make a field non-null only when it truly can never fail. A non-null field that errors nulls out its parent, which can erase large parts of a response.
- Use global, opaque IDs if clients cache by ID (the `Node` interface pattern).

### Evolution

- GraphQL APIs are usually versionless: add fields, then deprecate old ones with `@deprecated(reason: "Use fullName")` and remove them only after usage drops to zero. Field-level usage metrics make this safe.
- Breaking changes include: removing or renaming a field or type; changing a field's type; making an output field nullable when it was non-null; making an argument or input field required; removing an enum value.
- Run a schema diff in CI (for example `graphql-inspector diff old.graphql new.graphql`, or your schema registry's check command) to catch these.

### Performance and abuse

- **N+1 resolvers:** batch per request with a DataLoader-style loader (one instance per request, never shared across users).
- **Query cost:** enforce a maximum depth and a complexity or cost limit, plus a server-side timeout. Without these, one query can fetch the whole database.
- **Persisted queries / trusted documents:** for first-party clients, accept only registered query hashes in production. This blocks arbitrary queries and enables GET-based CDN caching.
- **Introspection:** consider disabling it in production for private APIs. That is defense in depth, not access control.
- Limit batching of multiple operations per request. Brute-force attacks hide inside batched requests.

### Authorization

- Enforce authorization in the business layer or resolvers for every object and field, not just at the gateway. Any field can be reached through many paths in the graph.
- Treat field arguments like any untrusted input: validate them and bound their sizes.

### HTTP behavior

- Many servers return HTTP 200 even when the `errors` array is non-empty. Monitoring must inspect `errors`, not just status codes.
- Return 4xx at the HTTP level for requests that cannot be parsed or are unauthenticated, if your server and clients support it. Be consistent.

## gRPC

### Proto design

- Follow a style guide. Google's API Improvement Proposals (aip.dev) are the most complete; `buf lint` enforces a common subset.
- One `package` per API with a major version: `package acme.orders.v1;`.
- Resource-oriented methods where possible: `GetOrder`, `ListOrders`, `CreateOrder`, `UpdateOrder`, `DeleteOrder`, with `GetOrderRequest`/`GetOrderResponse`-style messages unique to each RPC. Never reuse a request message across RPCs.
- List methods take `page_size` and `page_token`, and return `next_page_token`.
- Partial updates take a `google.protobuf.FieldMask update_mask`.
- The first enum value must be zero. Name it `<ENUM>_UNSPECIFIED` and never give it business meaning.
- Use proto3 `optional` (protobuf 3.15+) or wrapper types when you need to tell "unset" apart from the zero value.
- Use well-known types for time and durations: `google.protobuf.Timestamp` and `google.protobuf.Duration`.

### Compatibility rules

- **Never change a field number or a field's type.** The wire format identifies fields by number.
- **Never reuse a removed field number or name.** Mark both as `reserved`:

  ```proto
  message Order {
    reserved 4, 7;
    reserved "legacy_status";
    string id = 1;
    string customer_id = 2;
  }
  ```

- Adding fields, messages, enum values and RPCs is safe. Old clients ignore unknown fields.
- Renaming a field keeps the binary wire format but breaks JSON transcoding and generated code. Treat it as breaking.
- Run `buf breaking --against '.git#branch=main'` (adjust the branch) in CI.
- For a breaking change, create a new package version (`v2`) and serve both until clients migrate.

### Deadlines, retries and status codes

- Every client call sets a deadline. Servers pass the remaining deadline on to downstream calls, which gRPC does through the context. A call with no deadline can hang forever.
- Configure retries in the service config or the client library, not in hand-written loops. Retry only codes that are safe for that method.

| Code | Use for | Retry? | Rough HTTP equivalent |
|---|---|---|---|
| `INVALID_ARGUMENT` | Bad input regardless of state | No | 400 |
| `FAILED_PRECONDITION` | System not in the required state | No (fix state first) | 400 |
| `OUT_OF_RANGE` | Valid type, but past a valid range | No | 400 |
| `UNAUTHENTICATED` | Missing or invalid credentials | No | 401 |
| `PERMISSION_DENIED` | Authenticated but not allowed | No | 403 |
| `NOT_FOUND` | Resource missing | No | 404 |
| `ALREADY_EXISTS` | Create conflicts with an existing resource | No | 409 |
| `ABORTED` | Concurrency conflict (for example an optimistic-lock failure) | Retry the whole read-modify-write | 409 |
| `RESOURCE_EXHAUSTED` | Quota or rate limit | With backoff | 429 |
| `UNIMPLEMENTED` | Method not supported | No | 501 |
| `UNAVAILABLE` | Transient outage | Yes, with backoff | 503 |
| `DEADLINE_EXCEEDED` | Deadline passed | Only if the method is idempotent | 504 |
| `INTERNAL` | Bug or invariant broken | No | 500 |

- Attach structured error details through `google.rpc.Status` details (for example `BadRequest`, `ErrorInfo`, `RetryInfo`) instead of encoding them in the message string.

### Operations

- Plain gRPC needs HTTP/2 end to end. Check that load balancers and proxies support it.
- Long-lived HTTP/2 connections defeat connection-level load balancing. Use client-side or L7 (request-level) load balancing.
- Use the standard gRPC health checking protocol (`grpc.health.v1.Health`) for readiness.
- Enable server reflection only where tooling needs it.
- For browser clients, use gRPC-Web or the Connect protocol, behind a compatible proxy or server.
