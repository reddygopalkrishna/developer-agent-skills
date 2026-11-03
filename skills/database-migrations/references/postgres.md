# PostgreSQL migration reference

Check the server version first (`SELECT version();`). Version-specific behaviour is marked below. When in doubt, read the "Notes" section of the `ALTER TABLE` page in the official docs for that exact major version.

## Lock levels that matter

| Lock | Taken by (common cases) | Blocks |
|---|---|---|
| `ACCESS EXCLUSIVE` | Most `ALTER TABLE` forms, `DROP TABLE`, `TRUNCATE`, `VACUUM FULL`, `CLUSTER` | Everything, including plain `SELECT` |
| `SHARE ROW EXCLUSIVE` | `ADD FOREIGN KEY` (on the referencing and the referenced table), `CREATE TRIGGER` | Writes |
| `SHARE` | `CREATE INDEX` (non-concurrent); `REINDEX` (non-concurrent) on the table, plus `ACCESS EXCLUSIVE` on the index being rebuilt | Writes (`INSERT`, `UPDATE`, `DELETE`) for the whole build; `REINDEX` also blocks almost all queries on the table, because planning locks every index |
| `SHARE UPDATE EXCLUSIVE` | `CREATE INDEX CONCURRENTLY`, `VALIDATE CONSTRAINT`, `VACUUM`, `ANALYZE` | Other schema changes only; reads and writes continue |

Even a metadata-only `ACCESS EXCLUSIVE` statement is dangerous: it waits for every running transaction on the table to finish, and while it waits, **every new query on that table queues behind it**. That is why every DDL needs a lock timeout.

## Guard header

```sql
SET lock_timeout = '5s';          -- give up instead of queueing traffic behind us
SET statement_timeout = '30min';  -- upper bound for this session's statements; tune per migration
```

Inside a transaction-wrapped migration use `SET LOCAL ...` so the setting ends with the transaction. If the statement times out on the lock, retry later (ideally with backoff in the migration runner) rather than raising the timeout.

## Recipes

### Add a column with a default

- PostgreSQL 11+: `ALTER TABLE t ADD COLUMN c integer NOT NULL DEFAULT 0;` is metadata-only when the default is **non-volatile** (constants, `now()`).
- Volatile defaults (`random()`, `gen_random_uuid()`, `clock_timestamp()`) rewrite the whole table. Instead: add the column nullable with no default, backfill in batches, then `ALTER COLUMN c SET DEFAULT ...` and add NOT NULL with the recipe below.
- Before PostgreSQL 11, any default rewrites the table.

### Add NOT NULL to an existing column

```sql
ALTER TABLE users ADD CONSTRAINT users_email_not_null
  CHECK (email IS NOT NULL) NOT VALID;               -- instant, brief lock
ALTER TABLE users VALIDATE CONSTRAINT users_email_not_null;  -- scans, but reads/writes continue
ALTER TABLE users ALTER COLUMN email SET NOT NULL;   -- PG 12+: uses the valid CHECK, skips the scan
ALTER TABLE users DROP CONSTRAINT users_email_not_null;
```

Run these as separate migrations (or at least separate transactions). On PostgreSQL 11 and older, `SET NOT NULL` always scans; keep the CHECK constraint instead. PostgreSQL 18+ can also add the not-null constraint itself as `NOT VALID` (`ALTER TABLE users ADD CONSTRAINT users_email_not_null NOT NULL email NOT VALID;`) and then `VALIDATE CONSTRAINT` it with the same weaker lock.

### Create an index

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS orders_customer_id_idx ON orders (customer_id);
```

- Cannot run inside a transaction block. Put it alone in its own migration and disable the tool's transaction (table below).
- Takes longer than a normal build and waits for existing transactions to finish.
- If it fails or is cancelled it leaves an **INVALID** index that still slows writes. Find and remove it, then retry:

```sql
SELECT indexrelid::regclass AS index_name
FROM   pg_index
WHERE  NOT indisvalid;

DROP INDEX CONCURRENTLY IF EXISTS orders_customer_id_idx;
```

- PostgreSQL 12+ can rebuild without blocking: `REINDEX INDEX CONCURRENTLY name;`.
- Partitioned tables: `CREATE INDEX CONCURRENTLY` on the partitioned parent is not supported in current releases. Create the parent index `ON ONLY` the parent, build each partition's index concurrently, then `ALTER INDEX parent_idx ATTACH PARTITION child_idx;`. Check the `CREATE INDEX` docs for your version.

### Add a unique constraint

```sql
-- 1. Check for duplicates first; the build fails if any exist.
SELECT email, count(*) FROM users GROUP BY email HAVING count(*) > 1;

-- 2. Build the index without blocking writes (own migration, no transaction).
CREATE UNIQUE INDEX CONCURRENTLY users_email_key ON users (email);

-- 3. Attach it as a constraint (brief lock).
ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE USING INDEX users_email_key;
```

### Add a foreign key

```sql
ALTER TABLE orders
  ADD CONSTRAINT orders_customer_id_fkey
  FOREIGN KEY (customer_id) REFERENCES customers (id) NOT VALID;   -- brief lock, no scan

ALTER TABLE orders VALIDATE CONSTRAINT orders_customer_id_fkey;     -- scans without blocking writes
```

Also index the referencing column (`orders.customer_id`) concurrently; otherwise every delete or key update on `customers` scans `orders`.

### Add a CHECK constraint

Same pattern as foreign keys: `ADD CONSTRAINT ... CHECK (...) NOT VALID`, then `VALIDATE CONSTRAINT` in a separate step.

### Change a column type

- Metadata-only (no rewrite): `varchar(n)` → `text`, increasing `varchar(n)` to a larger `n`, removing a length limit.
- Almost everything else rewrites the table under `ACCESS EXCLUSIVE` (for example `integer` → `bigint`, `text` → `integer`, timestamp ↔ timestamptz in most cases). Test on a copy: if `ALTER TABLE ... ALTER COLUMN ... TYPE` changes the table's `relfilenode` (`SELECT relfilenode FROM pg_class WHERE relname = 't';` before and after), it rewrote.
- For large tables use expand/contract:
  1. Add the new column (for example `id_new bigint`).
  2. Keep it in sync for new writes (a trigger, or dual writes in the app).
  3. Backfill in batches.
  4. Build any needed indexes concurrently on the new column.
  5. In one short transaction with a lock timeout, swap names (and sequences/defaults/constraints for primary keys).
  6. Drop the old column later.

Primary key type changes (`int` → `bigint`) also touch every referencing foreign key. Plan them as a project, not a single migration.

### Rename a column or table

`ALTER TABLE ... RENAME` is metadata-only, but it breaks every running instance that uses the old name. Use expand/contract. For a table rename, a short-lived compatibility view with the old name (`CREATE VIEW old_name AS SELECT * FROM new_name;`) can bridge simple read/write cases. Verify that the view is auto-updatable for the way your app writes to it.

### Drop a column or table

1. Remove every code reference and deploy (see the ORM notes in SKILL.md).
2. Confirm a backup or snapshot exists.
3. Get explicit approval from the user.
4. Drop with a lock timeout: `ALTER TABLE t DROP COLUMN c;` is metadata-only (the space is reclaimed later), but it still needs `ACCESS EXCLUSIVE` briefly.

## Running statements outside a transaction, per tool

| Tool | How |
|---|---|
| Rails | `disable_ddl_transaction!` in the migration class; `add_index :t, :c, algorithm: :concurrently` |
| Django | `atomic = False` on the `Migration` class; `AddIndexConcurrently` / `RemoveIndexConcurrently` from `django.contrib.postgres.operations` |
| Alembic | `with op.get_context().autocommit_block(): op.create_index(..., postgresql_concurrently=True)` |
| EF Core | `migrationBuilder.Sql("CREATE INDEX CONCURRENTLY ...", suppressTransaction: true);` |
| Liquibase | `runInTransaction="false"` on the changeset |
| Flyway | Supports non-transactional scripts, but the mechanism depends on the Flyway version and edition. Check the Flyway docs for "executeInTransaction" / script configuration for your version before relying on it |
| golang-migrate, Prisma, others | Put the statement alone in its own migration file, then check the tool's docs for whether it wraps files in a transaction. Sending several statements in one call can also create an implicit transaction |

## Find what is blocking

```sql
SELECT pid,
       pg_blocking_pids(pid)  AS blocked_by,
       state,
       wait_event_type,
       now() - xact_start     AS xact_age,
       left(query, 100)       AS query
FROM   pg_stat_activity
WHERE  datname = current_database()
  AND  state <> 'idle'
ORDER  BY xact_start NULLS LAST;
```

- Look for `idle in transaction` sessions with an old `xact_age`; they hold locks and block DDL. `idle_in_transaction_session_timeout` limits them.
- Cancelling (`pg_cancel_backend(pid)`) or terminating (`pg_terminate_backend(pid)`) another session affects real users. **Ask the user before doing either.**

## Replication lag during backfills

```sql
SELECT application_name, replay_lag FROM pg_stat_replication;   -- run on the primary
```

Pause the backfill while lag is growing. Large single-statement updates also generate a burst of WAL that replicas and logical-replication consumers must replay.
