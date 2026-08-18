# ADR-005: SQLite with Write-Ahead Logging (WAL) and Automated Hot Rolling Backups

## Status
Accepted

## Date
2026-05-24

## Context
Industrial packing facilities frequently encounter unexpected environmental disruptions, such as sudden power outages, emergency line stops, and electrical noise.

Key data persistence requirements:
- **Zero Database Server Administration**: Cannot require running or maintaining external database services (like PostgreSQL, MySQL) on edge sorting PCs.
- **High Concurrency & Low Latency**: Video inference loop logs every fruit sorting event without blocking UI read queries or report generation.
- **Data Integrity & Crash Resilience**: Zero database corruption during power cuts.
- **Automated Backup Strategy**: Regular snapshots to preserve batch history and sorting logs.

## Decision
Utilize embedded **SQLite** with **Write-Ahead Logging (WAL)** and an automated background **Hot Backup Service** (`core/database.py` and `core/db_backup.py`):

1. **WAL Mode Configuration**:
   - Initialized at connection time: `PRAGMA journal_mode=WAL;`
   - Synchronization tuned for SSD reliability: `PRAGMA synchronous=NORMAL;`
   - Busy timeout set to `5000 ms` to handle transient contention.
2. **Automated Rolling Hot Backup (`DBBackupService`)**:
   - Executes in a lightweight background thread.
   - Leverages SQLite's native `sqlite3_backup` API to create non-blocking point-in-time snapshots (`data/backups/durian_backup_YYYYMMDD_HHMMSS.db`) every 15 minutes.
   - Retains a rolling window of the last 10 snapshots, automatically pruning older files to prevent disk exhaustion.
3. **Graceful Shutdown Checkpointing**:
   - Performs a full `PRAGMA wal_checkpoint(TRUNCATE);` on application shutdown to ensure all write-ahead logs are committed back into the primary database file.

## Alternatives Considered

### 1. External PostgreSQL Server
- **Pros**: Robust multi-client networking, advanced analytics.
- **Cons**: Substantial memory consumption (>200 MB), requires service daemon management, complex setup on standalone Windows/Linux edge PCs.
- **Rejected**: Overkill and high maintenance burden for single-machine edge installations.

### 2. In-Memory State with CSV / Flat JSON Files
- **Pros**: Extremely simple.
- **Cons**: Prone to corruption or file truncation during sudden power loss; inefficient querying for large batch histories; lack of ACID transactions.
- **Rejected**: Risk of data loss on factory floor.

## Consequences
- **Positive**:
  - Embedded zero-config database stored in a single file (`data/durian.db`).
  - WAL mode allows concurrent readers (UI dashboard, report exports) without blocking the camera detection logging writer.
  - Resilience against sudden power interruptions with automated 15-minute rolling backups.
- **Negative / Trade-offs**:
  - WAL mode creates auxiliary files (`durian.db-wal`, `durian.db-shm`) alongside the main database file during runtime.
