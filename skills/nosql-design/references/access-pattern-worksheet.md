# Access-pattern worksheet

Fill this in with the user before designing keys or indexes. Every row must end with a concrete key or index. A row you can't map is a design problem to solve now, not later.

## Template

| # | Pattern (read or write) | Inputs | Result | Frequency (per second or day) | Latency target | Consistency | Maps to |
|---|---|---|---|---|---|---|---|
| R1 | | | | | | strong / eventual | key, range or index |
| W1 | | | | | | | |

Also record:

- **Growth**: how many items per parent over the system's lifetime (orders per customer, events per device). Anything unbounded needs its own collection, partition scheme or TTL.
- **Size**: typical and maximum document or item size.
- **Hot keys**: any single key that gets a large share of traffic (a celebrity account, a global counter, "today").
- **Invariants**: uniqueness, "stock never below zero", "one active session per user". Each needs an atomic operation, condition or unique index.
- **Retention**: how long data lives, and how it is deleted (TTL, batch job).

## Worked example: order service

| # | Pattern | Inputs | Result | Frequency | Consistency |
|---|---|---|---|---|---|
| R1 | Get order with lines | orderId | 1 order, up to ~50 lines | High | Strong |
| R2 | Customer's recent orders | customerId | latest 20, newest first | High | Eventual OK |
| R3 | Open orders older than 1 hour (ops dashboard) | status, time | up to a few hundred | Low | Eventual OK |
| W1 | Place order | order + lines | — | Medium | Must not double-create on retry |
| W2 | Update order status | orderId, from-status, to-status | — | Medium | Must not overwrite a newer status |

### MongoDB mapping

- `orders` collection, one document per order with its lines embedded (bounded, read together, owned by the order).
- R1: `findOne({ _id: orderId })`.
- R2: index `{ customerId: 1, createdAt: -1 }` (equality, then sort); query `find({ customerId }).sort({ createdAt: -1 }).limit(20)`.
- R3: partial index `{ createdAt: 1 }` with `partialFilterExpression: { status: "open" }`; query `find({ status: "open", createdAt: { $lt: cutoff } })`.
- W1: use a client-generated `_id` or a unique index on an idempotency key, so a retried insert fails with a duplicate-key error instead of creating a second order.
- W2: `updateOne({ _id: orderId, status: "paid" }, { $set: { status: "shipped" } })` and check `matchedCount`; 0 means the status had already changed.

### DynamoDB mapping

| Item | PK | SK | GSI1PK | GSI1SK |
|---|---|---|---|---|
| Order header | `ORDER#<orderId>` | `META` | `STATUS#open` (only while open) | `<createdAt>` |
| Order line | `ORDER#<orderId>` | `LINE#<n>` | — | — |
| Customer's order index | `CUSTOMER#<customerId>` | `ORDER#<createdAt>#<orderId>` | — | — |

- R1: `Query PK = ORDER#<orderId>` returns the header and all lines.
- R2: `Query PK = CUSTOMER#<customerId>`, `SK begins_with ORDER#`, `ScanIndexForward = false`, `Limit = 20`.
- R3: `Query` on GSI1 with `GSI1PK = STATUS#open` and `GSI1SK < cutoff`. Remove the GSI1 attributes when the order closes, so the index stays sparse. If open orders become very numerous, this partition gets hot: shard it (`STATUS#open#0` to `#9`) and query all shards.
- W1: `TransactWriteItems` writing the header with `attribute_not_exists(PK)`, the lines, and the customer index item.
- W2: `UpdateItem` with `ConditionExpression: #s = :from`; a `ConditionalCheckFailedException` means the status had already changed.

### Fit check

All five patterns map to direct keys or indexes, growth per order is bounded, and invariants are enforced by the store. NoSQL fits. If the team later needs "revenue by region by week" queries, export the data to an analytics store rather than adding scans.
