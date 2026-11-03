# PostgreSQL monitoring queries

All queries here are read-only. Function and column names are for PostgreSQL 10+; where a column changed in a later version it is noted. Run them as a role that can see other sessions (for example a member of `pg_monitor`), or you will see only your own sessions.

## Connections

Connections by state:

```sql
SELECT state, count(*)
FROM pg_stat_activity
WHERE backend_type = 'client backend'
GROUP BY state
ORDER BY count(*) DESC;
```

Usage against the limit, and who holds connections:

```sql
SELECT count(*) AS used, current_setting('max_connections')::int AS max_connections
FROM pg_stat_activity;

SELECT usename, application_name, client_addr, count(*)
FROM pg_stat_activity
GROUP BY 1, 2, 3
ORDER BY count(*) DESC
LIMIT 20;
```

Many `idle` connections means oversized pools. Many `idle in transaction` means an application bug (a transaction opened and not closed).

## Long transactions and blocking

Oldest open transactions. These block vacuum and often hold locks:

```sql
SELECT pid, usename, application_name, state,
       now() - xact_start   AS xact_age,
       now() - state_change AS in_state_for,
       left(query, 120)     AS query
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
ORDER BY xact_start
LIMIT 20;
```

Who is blocking whom:

```sql
SELECT blocked.pid                    AS blocked_pid,
       left(blocked.query, 80)        AS blocked_query,
       blocking.pid                   AS blocking_pid,
       blocking.state                 AS blocking_state,
       left(blocking.query, 80)       AS blocking_query,
       now() - blocked.query_start    AS waiting_for
FROM pg_stat_activity AS blocked
JOIN LATERAL unnest(pg_blocking_pids(blocked.pid)) AS b(pid) ON true
JOIN pg_stat_activity AS blocking ON blocking.pid = b.pid
ORDER BY waiting_for DESC;
```

Stopping a session changes production. Show the user the session first and get confirmation:

- `SELECT pg_cancel_backend(<pid>);` cancels the current query; the session stays.
- `SELECT pg_terminate_backend(<pid>);` closes the session and rolls back its transaction.

Forgotten two-phase transactions (they block vacuum like a long transaction):

```sql
SELECT gid, prepared, owner, database FROM pg_prepared_xacts ORDER BY prepared;
```

## Vacuum and bloat

Tables with the most dead rows:

```sql
SELECT relid::regclass AS table_name,
       n_live_tup, n_dead_tup,
       round(100.0 * n_dead_tup / nullif(n_live_tup + n_dead_tup, 0), 1) AS dead_pct,
       last_autovacuum, last_autoanalyze, autovacuum_count
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 20;
```

Vacuums running now:

```sql
SELECT p.pid, p.relid::regclass AS table_name, p.phase,
       now() - a.query_start AS running_for
FROM pg_stat_progress_vacuum AS p
JOIN pg_stat_activity AS a USING (pid);
```

Per-table autovacuum overrides already in place:

```sql
SELECT oid::regclass AS table_name, reloptions
FROM pg_class
WHERE reloptions IS NOT NULL AND relkind = 'r';
```

`n_dead_tup` is an estimate. For an exact bloat measurement on a specific table, the `pgstattuple` extension gives real numbers but reads the whole table, so run it off-peak.

## Transaction ID wraparound

Per database:

```sql
SELECT datname, age(datfrozenxid) AS xid_age
FROM pg_database
ORDER BY xid_age DESC;
```

Per table (run in each large database):

```sql
SELECT c.oid::regclass AS table_name,
       age(c.relfrozenxid) AS xid_age,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size
FROM pg_class AS c
WHERE c.relkind IN ('r', 'm', 't')
ORDER BY age(c.relfrozenxid) DESC
LIMIT 20;
```

Compare `xid_age` against `autovacuum_freeze_max_age` (default 200 million) and the hard limit of about 2 billion. A value that keeps climbing past the freeze age means something is blocking freezing: look at long transactions, slots and prepared transactions above.

## Size and indexes

Largest tables:

```sql
SELECT relid::regclass AS table_name,
       pg_size_pretty(pg_total_relation_size(relid)) AS total_with_indexes,
       pg_size_pretty(pg_relation_size(relid))       AS table_only
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 20;
```

Indexes never scanned since the statistics were last reset (candidates for removal):

```sql
SELECT s.relname AS table_name, s.indexrelname AS index_name, s.idx_scan,
       pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size
FROM pg_stat_user_indexes AS s
JOIN pg_index AS i ON i.indexrelid = s.indexrelid
WHERE s.idx_scan = 0
  AND NOT i.indisunique
  AND NOT i.indisprimary
ORDER BY pg_relation_size(s.indexrelid) DESC;
```

Before dropping one: statistics are per server, so check every replica that serves reads, and check when stats were last reset (`SELECT stats_reset FROM pg_stat_database WHERE datname = current_database();`).

Buffer cache hit ratio per database:

```sql
SELECT datname,
       round(100.0 * blks_hit / nullif(blks_hit + blks_read, 0), 2) AS cache_hit_pct
FROM pg_stat_database
WHERE datname IS NOT NULL;
```

## Replication

On the primary, per replica:

```sql
SELECT application_name, client_addr, state, sync_state,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn)) AS replay_lag_size,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;
```

On a replica (time since the last replayed transaction; this also grows when the primary is idle, so read it together with the size above):

```sql
SELECT pg_is_in_recovery() AS is_replica,
       now() - pg_last_xact_replay_timestamp() AS since_last_replay;
```

Replication slots and the WAL each one is holding:

```sql
SELECT slot_name, slot_type, database, active,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained_wal
FROM pg_replication_slots
ORDER BY pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) DESC NULLS LAST;
```

On PostgreSQL 13+, also select `wal_status` and `safe_wal_size`. Alert on any inactive slot and on retained WAL above a threshold you choose based on free disk.

## Top queries

Requires the `pg_stat_statements` extension (in `shared_preload_libraries`, then `CREATE EXTENSION pg_stat_statements;`).

```sql
SELECT calls,
       round(total_exec_time::numeric)    AS total_ms,
       round(mean_exec_time::numeric, 1)  AS mean_ms,
       rows,
       left(query, 100)                   AS query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

Before PostgreSQL 13 the columns are `total_time` and `mean_time`. Hand the slow queries to the sql-optimization skill.

## Settings

Current values and where they come from:

```sql
SELECT name, setting, unit, source
FROM pg_settings
WHERE name IN (
  'max_connections', 'shared_buffers', 'work_mem', 'maintenance_work_mem',
  'effective_cache_size', 'statement_timeout', 'lock_timeout',
  'idle_in_transaction_session_timeout', 'autovacuum_freeze_max_age',
  'max_slot_wal_keep_size', 'hot_standby_feedback', 'archive_mode'
);
```

Per-role overrides:

```sql
SELECT rolname, rolconfig FROM pg_roles WHERE rolconfig IS NOT NULL;
```
