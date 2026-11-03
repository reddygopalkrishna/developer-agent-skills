# Multi-tenancy patterns

Pick the model from the isolation the business needs (contracts, regulation, noisy neighbours, per-tenant restore) and from the number of tenants. Confirm the choice with the user; switching models later is expensive.

## Decision questions

1. How many tenants now, and in three years? Tens, thousands, millions?
2. Do any contracts or regulations require physical isolation, data residency in a region, or customer-managed encryption keys?
3. Must one tenant's data be restorable or exportable without touching the others?
4. Will a few tenants be much larger than the rest (noisy neighbours)?
5. Do you need cross-tenant queries (internal analytics, admin tools)?

| Answer pattern | Model |
|---|---|
| Many small tenants, no physical isolation requirement | Shared tables + `tenant_id` |
| Moderate tenant count, need per-tenant restore, or moderate isolation | Schema per tenant |
| Few large or regulated tenants, residency or dedicated-key requirements | Database per tenant |
| Mix of the above | Hybrid: shared by default, dedicated databases for large or regulated tenants, behind one routing layer |

## Shared tables + `tenant_id`

Every tenant-owned table has `tenant_id NOT NULL`, and every query filters by it.

### Make cross-tenant references impossible

Include `tenant_id` in keys and foreign keys, so a row can only reference rows of the same tenant:

```sql
CREATE TABLE customers (
  tenant_id  uuid   NOT NULL REFERENCES tenants (id),
  id         bigint GENERATED ALWAYS AS IDENTITY,
  email      text   NOT NULL,
  PRIMARY KEY (tenant_id, id),
  UNIQUE (tenant_id, email)
);

CREATE TABLE invoices (
  tenant_id    uuid   NOT NULL,
  id           bigint GENERATED ALWAYS AS IDENTITY,
  customer_id  bigint NOT NULL,
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, customer_id) REFERENCES customers (tenant_id, id)
);
```

- Lead composite indexes with `tenant_id` for tenant-scoped queries.
- Scope uniqueness per tenant: `UNIQUE (tenant_id, email)`.

### Enforce isolation in the database: PostgreSQL row-level security

Application-level filtering fails the first time someone forgets a `WHERE`. Row-level security (RLS) makes the database refuse cross-tenant rows.

```sql
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices FORCE ROW LEVEL SECURITY;   -- apply to the table owner too

CREATE POLICY tenant_isolation ON invoices
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
```

- When a policy has only `USING`, PostgreSQL also applies it as the `WITH CHECK` for inserts and updates, so a session cannot write rows for another tenant.
- `current_setting('app.tenant_id', true)` returns NULL when the setting is missing, so the policy matches no rows. Unset context fails closed.
- Set the tenant per transaction: `SET LOCAL app.tenant_id = '...';` at the start of every transaction. `SET LOCAL` matters with connection poolers (such as PgBouncer in transaction mode): a plain `SET` would leak to the next client that gets the connection.
- Superusers and roles with `BYPASSRLS` ignore policies. Run the application as a dedicated non-superuser role without `BYPASSRLS`. Without `FORCE ROW LEVEL SECURITY`, the table owner also bypasses policies.
- Add an index on `tenant_id` (or composite indexes that lead with it); the policy predicate is added to every query.
- Write an automated test: with tenant A's context, selecting, updating or inserting tenant B's rows must fail or return nothing.

MySQL has no row-level security. Enforce tenant filtering in one data-access layer (a repository base class or an ORM global scope), and test it the same way.

### Tradeoffs

- Pros: one schema to migrate, cheapest to run, easy cross-tenant analytics.
- Cons: noisy neighbours share resources; per-tenant restore means filtered exports, not a database restore; one missed filter (without RLS) leaks data.
- Scale-out: shard by `tenant_id` when one database is no longer enough (for example with Citus on PostgreSQL, or application-level routing).

## Schema per tenant

Each tenant gets a schema (PostgreSQL) or database (MySQL treats schema and database as the same thing) with identical tables.

- Route by setting the schema per connection or transaction (PostgreSQL `SET LOCAL search_path = tenant_123, public;`), or by fully qualifying table names.
- Migrations must run once per tenant. Make the runner resumable and track the version per tenant, because some tenants will fail midway.
- Thousands of schemas inflate the system catalogs and slow migrations, backups and some tools. Measure at your expected scale before committing.
- Per-tenant backup and restore is easier (`pg_dump --schema=tenant_123`).
- Cross-tenant queries need `UNION ALL` across schemas or a separate analytics pipeline.

## Database per tenant

- Strongest isolation: separate credentials, backups, encryption keys, regions and resource limits per tenant.
- Costs: provisioning automation, migrations across N databases, connection pooling per database, monitoring and upgrades per database.
- Keep a central catalog (`tenant_id → connection info, region, version`) and route every request through it.
- Cross-tenant analytics require a pipeline into a warehouse.

## Practices for every model

- Put the tenant identifier in the authentication token or session, never in a client-controlled parameter that is trusted on its own.
- Include the tenant in every log line, metric label (where cardinality allows) and trace, so incidents can be scoped.
- Cache keys must include the tenant (`tenant:123:invoice:456`), or one tenant will see another's cached data.
- Background jobs and message consumers must carry and set the tenant context explicitly. They are the most common source of cross-tenant leaks.
- Support per-tenant export and deletion from the start. Contracts and privacy laws will require them.
- Test isolation in CI: create two tenants, act as one, and assert that nothing from the other is visible or writable.
