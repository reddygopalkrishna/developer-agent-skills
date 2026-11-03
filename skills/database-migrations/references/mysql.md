# MySQL / MariaDB migration reference

Check the exact version first (`SELECT VERSION();`). Online DDL support changes between 8.0 point releases, and MariaDB differs from MySQL. The authoritative source is the "Online DDL Operations" page of the MySQL Reference Manual for your exact version (MariaDB: "InnoDB Online DDL Overview").

## No transactional DDL

Every DDL statement in MySQL commits implicitly. A migration file with three `ALTER TABLE` statements that fails on the third leaves the first two applied, and most tools then record the migration as failed or half-done.

- Put one DDL statement per migration.
- Make migrations safe to re-run where possible (check `information_schema` before altering).

## Always state the algorithm and lock

```sql
ALTER TABLE orders ADD COLUMN note VARCHAR(255) NULL, ALGORITHM=INSTANT;
ALTER TABLE orders ADD INDEX orders_customer_id_idx (customer_id), ALGORITHM=INPLACE, LOCK=NONE;
```

If MySQL cannot do the operation with the requested algorithm or lock level, it **fails with an error** instead of silently falling back to a blocking table copy. That is exactly what you want: a failure in CI or on a copy, not an outage.

| Algorithm | Meaning |
|---|---|
| `INSTANT` | Metadata change only; no table rebuild |
| `INPLACE` | Rebuilt or modified inside InnoDB; with `LOCK=NONE`, reads and writes continue (brief exclusive metadata lock at start and end) |
| `COPY` | Full table copy; blocks writes for the whole duration. Never on a large live table |

### What is INSTANT, and since when

- `ADD COLUMN ... ALGORITHM=INSTANT` became available in MySQL 8.0.12, at first only for columns appended as the last column.
- MySQL 8.0.29 extended INSTANT to adding columns in any position and to dropping columns.
- Many other operations (renaming a column, setting or dropping a column default, some ENUM/SET changes) can also be INSTANT, depending on the version and the exact change.

Do not guess. Try the statement with `ALGORITHM=INSTANT` on a copy of the table on the same version. If it errors, try `ALGORITHM=INPLACE, LOCK=NONE`. If that errors too, use an online schema change tool (below).

Note: MySQL limits how many INSTANT column changes a table can accumulate before it requires a rebuild. Check the docs for your version if you make many INSTANT changes to one table.

### Usually needs a rebuild or copy

- Changing a column's data type (for example `INT` → `BIGINT`) uses `COPY` and blocks writes.
- Changing the character set or collation of a column or table.
- Changing the primary key.

For these on large tables, use expand/contract (new column + backfill + switch) or an online schema change tool.

## Metadata locks (MDL)

Every DDL statement, even INSTANT, needs an exclusive metadata lock on the table for a moment. If any open transaction has touched the table, the DDL waits, and **every new query on that table queues behind the waiting DDL**. The default `lock_wait_timeout` is one year.

```sql
SET SESSION lock_wait_timeout = 5;   -- seconds; fail fast, retry later
```

Find what is holding the lock:

```sql
-- Sessions stuck on "Waiting for table metadata lock"
SHOW FULL PROCESSLIST;

-- Who is blocking whom (sys schema, MySQL 5.7+)
SELECT * FROM sys.schema_table_lock_waits;

-- Long-running InnoDB transactions
SELECT trx_mysql_thread_id, trx_started, trx_state, LEFT(trx_query, 100) AS query
FROM   information_schema.innodb_trx
ORDER  BY trx_started;
```

`sys.schema_table_lock_waits` needs the metadata lock instrument (`wait/lock/metadata/sql/mdl`) enabled in performance_schema; it is on by default in MySQL 8.0.

Killing a session (`KILL <id>`) affects real users. **Ask the user first.**

## Online schema change tools

Use these when a change cannot run as INSTANT or INPLACE with `LOCK=NONE` on a large table. Both copy the table in the background and swap it in at the end. Both need free disk space for a full copy.

### gh-ost

- Uses the binary log instead of triggers, so it needs `binlog_format=ROW` and access to a server that writes binlogs.
- Does nothing destructive without `--execute`: running without it performs a dry run.
- `--postpone-cut-over-flag-file=/path/file` keeps the final swap waiting until you delete the file, so a human chooses the moment.
- Foreign key constraints are not supported. For tables that have or are referenced by foreign keys, use pt-online-schema-change or another approach, and check the gh-ost docs ("Requirements and limitations") for your version.

```bash
gh-ost --host=replica.example --database=app --table=orders \
  --alter="ADD COLUMN note VARCHAR(255) NULL" \
  --postpone-cut-over-flag-file=/tmp/ghost.postpone \
  --execute
```

### pt-online-schema-change (Percona Toolkit)

- Trigger-based: creates triggers on the original table to copy ongoing writes. Check for existing triggers and their interaction with the tool's documentation for your version.
- Run `--dry-run` first, then `--execute`.
- For tables referenced by foreign keys, choose `--alter-foreign-keys-method` deliberately (read the docs; `drop_swap` has a window where the table does not exist).

```bash
pt-online-schema-change --alter "ADD COLUMN note VARCHAR(255) NULL" \
  D=app,t=orders --dry-run
pt-online-schema-change --alter "ADD COLUMN note VARCHAR(255) NULL" \
  D=app,t=orders --execute
```

Both tools change production data. **Get explicit approval from the user before running either with `--execute`.** Managed services (Amazon RDS/Aurora, Azure, Cloud SQL) may restrict binlog access or privileges; check the tool's docs for your platform.

## Batched backfills

```sql
UPDATE orders
SET    status_v2 = status
WHERE  id BETWEEN :start AND :end
  AND  status_v2 IS NULL;
```

- Walk the primary key in ranges and commit after each batch.
- Watch replica lag between batches and pause when it grows:

```sql
SHOW REPLICA STATUS;   -- MySQL 8.0.22+; check Seconds_Behind_Source
SHOW SLAVE STATUS;     -- older versions; Seconds_Behind_Master
```

## Indexes

- Adding a secondary index: `ALGORITHM=INPLACE, LOCK=NONE` on InnoDB.
- Adding a unique index fails if duplicates exist. Check first with `GROUP BY ... HAVING COUNT(*) > 1`.
- MySQL has no partial indexes. Functional indexes exist from MySQL 8.0.13 (`INDEX ((LOWER(email)))`).

## Foreign keys

- With `foreign_key_checks=1`, adding a foreign key uses the `COPY` algorithm. With `SET foreign_key_checks = 0` in the session, InnoDB can add it `INPLACE`, **but existing rows are not validated**. Only do that after proving there are no orphan rows:

```sql
SELECT o.id FROM orders o
LEFT JOIN customers c ON c.id = o.customer_id
WHERE o.customer_id IS NOT NULL AND c.id IS NULL
LIMIT 10;
```

- MySQL requires an index on the referencing column and creates one automatically if none exists.
