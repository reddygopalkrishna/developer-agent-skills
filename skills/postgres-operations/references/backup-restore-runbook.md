# Backup and restore runbook

Every restore in this runbook goes to a **new, separate instance or database**. Never restore over the database you are trying to recover, and get explicit confirmation from the user before any restore, cutover or deletion on shared infrastructure.

## 1. Decide the targets

Agree on these with the user and write them down:

- **RPO**: how much data loss is acceptable (for example 5 minutes). Nightly dumps give an RPO of up to 24 hours; continuous WAL archiving gives seconds to minutes.
- **RTO**: how long recovery may take. Only a timed restore drill tells you the real number.
- **Retention**: how far back you need to go (accidental deletes are often noticed days later).
- **Location**: backups in a different account or project and region from the database, with deletion protection or immutability where available.

## 2. Pick the method

| Situation | Method |
|---|---|
| Managed service (RDS, Cloud SQL, Azure, ...) | Provider automated backups + PITR. Confirm the retention window, then still run drills. Add logical dumps if you need copies outside the provider |
| Self-managed, any real data | A backup tool (pgBackRest, Barman or WAL-G) with full/incremental base backups and continuous WAL archiving |
| Small database, or portable copy for one database | `pg_dump` on a schedule, in addition to (not instead of) physical backups for anything important |

## 3. Logical backups

```bash
# One database, custom format (compressed, supports parallel and selective restore)
pg_dump -Fc -d "$SOURCE_URL" -f app_$(date +%Y%m%d).dump

# Roles and other cluster-wide objects (pg_dump does not include them)
pg_dumpall --globals-only -d "$SOURCE_URL" -f globals.sql

# Inspect what a dump contains
pg_restore --list app_20261103.dump | head -50

# Restore into a NEW database on a separate (non-production) server
createdb -h "$TARGET_HOST" -U "$TARGET_USER" app_restore
pg_restore -h "$TARGET_HOST" -U "$TARGET_USER" -d app_restore -j 4 --no-owner app_20261103.dump
```

Managed services often do not allow dumping role passwords; `pg_dumpall --globals-only --no-role-passwords` works around that, and passwords are then set again separately.

## 4. Physical backups and PITR

### With a backup tool

Each tool has its own setup (a "stanza" in pgBackRest, a "server" in Barman). Follow the tool's documentation for the installed version. The checks that matter:

- WAL archiving is on and succeeding: `SELECT archived_count, failed_count, last_failed_wal FROM pg_stat_archiver;` shows `failed_count` not increasing.
- The tool's own check passes (for example `pgbackrest --stanza=<name> check`).
- The tool lists recent backups (for example `pgbackrest --stanza=<name> info`, `barman list-backup <server>`, `wal-g backup-list`).

### Native PostgreSQL (no tool)

- Base backup: `pg_basebackup -D /backups/base_$(date +%Y%m%d) -Fp -X stream -P` (run as a replication-capable role).
- WAL archiving: `archive_mode = on` plus `archive_command` (or `archive_library` on newer versions) that copies WAL to durable storage and returns non-zero on failure.

Point-in-time restore on PostgreSQL 12+:

1. Start from a copy of the base backup in a new, empty data directory on a separate host.
2. In `postgresql.conf` (or `postgresql.auto.conf`) set:
   ```
   restore_command = 'cp /wal-archive/%f "%p"'
   recovery_target_time = '2026-11-03 10:14:00+00'
   recovery_target_action = 'promote'
   ```
3. Create an empty `recovery.signal` file in the data directory.
4. Start PostgreSQL and watch the log until recovery reaches the target and the server promotes.

Before PostgreSQL 12, these settings lived in `recovery.conf`; check the docs for your version.

## 5. Restore drill (do this on a schedule)

1. Pick a random recent backup and a recovery point (for example "yesterday 14:00").
2. Restore it to an isolated instance using the steps above. **Start a timer.**
3. Validate:
   - The server starts and accepts connections.
   - Row counts of key tables are in the expected range, and the newest rows match the recovery point.
   - The application's read-only smoke checks pass against it.
   - Optional: check index and table integrity with `pg_amcheck` (PostgreSQL 14+) or the `amcheck` extension.
4. Stop the timer. Compare with the RTO.
5. Record date, backup used, duration, problems found. Fix the problems before the next drill.
6. Delete the drill instance (it contains production data) after confirming with the user.

## 6. Real recovery (incident)

Typical case: data was deleted or corrupted at a known time.

1. **Stop the damage.** Pause the job or deploy that caused it. Do not run more fixes on the primary yet.
2. **Find the recovery point**: the last moment before the bad change, from application logs, audit tables or `pg_stat_statements`.
3. **Restore to a new instance** at that point (section 4). Do not touch the primary.
4. **Decide with the user** between:
   - copying the lost rows from the restored instance back into the primary (smaller blast radius, keeps newer writes), or
   - switching the application to the restored instance (loses everything written after the recovery point).
5. **Validate** the chosen result with the same checks as a drill.
6. Write up the incident (see the incident-response skill), including how long the restore actually took.
