# SQLite memory schema

Version: PRAGMA user_version = 1. Unsupported versions fail rather than overwrite.

```sql
CREATE TABLE events (
  id TEXT PRIMARY KEY,
  time TEXT NOT NULL,
  kind TEXT NOT NULL,
  category TEXT NOT NULL,
  body TEXT NOT NULL
);
CREATE INDEX event_time ON events(time, id);
```

The body is a validated, finite JSON event containing units, source, provenance, status, benchmark configuration, calculated normalization and visual properties. Event IDs are immutable: identical reimports do nothing; conflicting content fails the transaction.

Memory.add validates the batch before writing and uses one transaction. Rows are ordered by canonical UTC timestamp then ID. Replay never inserts rows. The application persists observed records only; the core store can separate other kinds for tests/future use.

Limits: 10,000 events, each at most 8 KiB, and max_page_count 65536 (256 MiB at the default 4096-byte page size). Capacity produces an actionable error; no silent pruning. JSON export can contain the complete bounded history and is admitted by the 96 MiB input limit.

Default location: %LOCALAPPDATA%/ATOMVERSE-AI/memory.sqlite3. --data-dir selects an isolated location. The SQLite file and settings are local and ignored by Git. They are not encrypted. Explicit operator text may contain private material; review exports before sharing.

Journal mode DELETE keeps transactions recoverable without an indefinitely growing WAL. Export writes and fsyncs a sibling temporary file before atomic replacement.
