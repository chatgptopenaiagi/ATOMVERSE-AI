# SQLite memory v2

Mission 001 event bodies remain byte-for-byte intact. Opening v1 creates `memory.sqlite3.v1-backup` using SQLite backup; an existing backup is never overwritten. An additive transaction adds columns/tables and sets `PRAGMA user_version=2`. Future versions fail safely. Use the preserved original database or backup with the old 0.1 executable; it cannot open v2.

```sql
CREATE TABLE events (
  id TEXT PRIMARY KEY, time TEXT NOT NULL, kind TEXT NOT NULL,
  category TEXT NOT NULL, body TEXT NOT NULL,
  session TEXT NOT NULL DEFAULT '', entity TEXT NOT NULL DEFAULT '',
  classification TEXT NOT NULL DEFAULT '', ephemeral INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX event_time ON events(time, id);
CREATE INDEX event_entity ON events(entity, time);
CREATE TABLE sessions(id TEXT PRIMARY KEY, started TEXT NOT NULL, ended TEXT, configuration TEXT NOT NULL);
CREATE TABLE retention_audit(time TEXT NOT NULL, removed INTEGER NOT NULL, reason TEXT NOT NULL);
```

Each sample is one validated transaction. Duplicate IDs are ignored only when immutable bodies match. Original records remain protected (`ephemeral=0`). Live samples explicitly use rolling retention; comparisons and interpretations also protect their referenced source events.

Settings control 100–10,000 total rows and 0.01–720 hours of rolling samples (defaults 10,000 rows / 1 hour). The first limit reached wins: at short intervals, 10,000 rows can cover much less than one hour. Retention only deletes rolling rows, retains at most 100 audit entries and removes empty closed sessions. Protected-history capacity produces an error; export and select a new data directory. SQLite has a 256 MiB page cap, 3-second lock timeout and DELETE journaling.

Live UI history contains the newest 1,500 records; tables show up to 1,000 filtered rows. Load all retained records to replay/export older history. Replay is read-only. Equal-count comparison windows require matching entity, metric, unit, source and sampling configuration. They describe changes, not verified performance regressions or causes.

JSON retains full events, formulas, relationships, units and provenance. CSV includes classification and scientific/provenance JSON. Exports use a flushed temporary sibling and atomic replacement. Local data is not encrypted; review before sharing.
