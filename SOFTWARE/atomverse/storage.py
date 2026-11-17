"""Additive migration, explicit rolling retention and historical queries."""
from datetime import datetime, timedelta, timezone
import json
import sqlite3
from .core import ValidationError, utc_now, metric


def migrate(db, path, version):
    if version == 2:
        return
    if version == 1:
        backup = path.with_name(path.name + '.v1-backup')
        if backup.exists():
            raise ValidationError('migration backup already exists; inspect before migrating')
        with sqlite3.connect(backup) as target:
            db.backup(target)
    with db:
        for name, definition in [('session', "TEXT NOT NULL DEFAULT ''"), ('entity', "TEXT NOT NULL DEFAULT ''"), ('classification', "TEXT NOT NULL DEFAULT ''"), ('ephemeral', 'INTEGER NOT NULL DEFAULT 0')]:
            db.execute(f'ALTER TABLE events ADD COLUMN {name} {definition}')
        db.execute('CREATE INDEX event_entity ON events(entity,time)')
        db.execute('CREATE TABLE retention_audit(time TEXT NOT NULL, removed INTEGER NOT NULL, reason TEXT NOT NULL)')
        db.execute('CREATE TABLE sessions(id TEXT PRIMARY KEY, started TEXT NOT NULL, ended TEXT, configuration TEXT NOT NULL)')
        db.execute('PRAGMA user_version=2')


def recent(memory, limit=1500, entity=None, session=None):
    where, args = [], []
    if entity is not None:
        where.append('entity=?'); args.append(entity)
    if session is not None:
        where.append('session=?'); args.append(session)
    sql = 'SELECT body FROM events' + (' WHERE ' + ' AND '.join(where) if where else '')
    rows = memory.db.execute(sql + ' ORDER BY time DESC,id DESC LIMIT ?', (*args, min(10000, max(1, limit)))).fetchall()
    return [json.loads(row[0]) for row in reversed(rows)]


def retain(memory, incoming=0, max_rows=10000, hours=1):
    if not 100 <= max_rows <= 10000 or not 0.01 <= hours <= 720:
        raise ValidationError('retention bounds: 100–10000 rows, 0.01–720 hours')
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    with memory.db:
        protected = memory.db.execute('SELECT count(*) FROM events WHERE ephemeral=0').fetchone()[0]
        if protected + incoming > min(memory.limit, max_rows):
            raise ValidationError('Configured retention cap cannot fit protected history and one sample; raise the cap or select a new data directory')
        removed = memory.db.execute('DELETE FROM events WHERE ephemeral=1 AND time<?', (cutoff,)).rowcount
        count = memory.db.execute('SELECT count(*) FROM events').fetchone()[0]
        excess = max(0, count + incoming - min(memory.limit, max_rows))
        removed += memory.db.execute('DELETE FROM events WHERE id IN (SELECT id FROM events WHERE ephemeral=1 ORDER BY time,id LIMIT ?)', (excess,)).rowcount
        if removed:
            memory.db.execute('INSERT INTO retention_audit VALUES (?,?,?)', (utc_now(), removed, 'explicit rolling age/row policy; protected history retained'))
            memory.db.execute('DELETE FROM retention_audit WHERE rowid NOT IN (SELECT rowid FROM retention_audit ORDER BY rowid DESC LIMIT 100)')
        memory.db.execute('DELETE FROM sessions WHERE ended IS NOT NULL AND id NOT IN (SELECT DISTINCT session FROM events)')
    return removed


def compare(events, entity, name):
    """Compare two adjacent equal-count windows, never infer causes."""
    from .science import record, derived
    rows = [e for e in events if e.get('scientific', {}).get('entity_id') == entity and name in e['metrics'] and e['data_kind'] == 'observed']
    if len(rows) < 4:
        raise ValidationError('comparison needs at least four matching observations')
    rows = sorted(rows, key=lambda e: e['timestamp_utc'])[-20:]
    unit = rows[0]['metrics'][name]['unit']
    if any(e['metrics'][name]['unit'] != unit or e['source'] != rows[0]['source'] or e['configuration'] != rows[0]['configuration'] for e in rows):
        raise ValidationError('comparison conditions or units differ')
    half = len(rows) // 2; rows = rows[-2 * half:]
    before = sum(e['metrics'][name]['value'] for e in rows[:half]) / half
    after = sum(e['metrics'][name]['value'] for e in rows[half:]) / half
    return record('historical-comparison/1', rows[0]['component'], entity,
        {'earlier_mean': metric(before, unit), 'later_mean': metric(after, unit)}, cls='DERIVED', category='comparison', rolling=False,
        metadata={k: derived('sum(values) / count(values)', values=[e['metrics'][name]['value'] for e in subset]) for k, subset in [('earlier_mean', rows[:half]), ('later_mean', rows[half:])]},
        provenance={'event_ids': [e['event_id'] for e in rows], 'metric': name},
        message='Equal-count chronological windows of the same source, entity and unit. Descriptive change; workload conditions and cause are not established.')
