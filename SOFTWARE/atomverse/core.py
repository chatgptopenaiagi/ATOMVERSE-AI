"""Pure event contracts, deterministic visual mapping and bounded durable memory."""
from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sqlite3
import tempfile
from datetime import datetime, timezone
from uuid import uuid4

ORBITS = ('cpu', 'gpu', 'memory', 'storage', 'ai', 'code', 'database', 'guardian')
STATUSES = ('PASS', 'FAIL', 'INFO', 'SKIP', 'CANCELLED')
KINDS = ('observed', 'synthetic', 'interpretation')
MAX_FILE = 96 * 1024 * 1024  # fits the entire 10,000 x 8 KiB bounded store
MAX_EVENT = 8192
MAX_EVENTS = 10000
METRIC_RANGES = {
    'utilization_pct': (0, 100), 'used_pct': (0, 100),
    'duration_ms': (0, 5000), 'throughput_gflops': (0, 500),
    'logical_processors': (0, 32), 'total_bytes': (0, 128 * 1024**3),
    'memory_mib': (0, 16384), 'file_count': (0, 2000), 'characters': (0, 10000),
}
UNITS = {'%', 'ms', 's', 'bytes', 'MiB', 'count', 'C', 'GFLOP/s', 'ratio', 'W', 'MHz', 'bytes/s'}


class ValidationError(ValueError):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def utc(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValidationError('timestamp must be an ISO-8601 string with timezone')
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            raise ValueError('timezone missing')
        return dt.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    except ValueError as exc:
        raise ValidationError('invalid timestamp or missing timezone') from exc


def metric(value, unit):
    return {'value': value, 'unit': unit}


def _number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def derive(metrics, status, category, confidence=1.0, scale=1.0):
    if not isinstance(metrics, dict) or len(metrics) > 32:
        raise ValidationError('metrics must be an object with at most 32 entries')
    expected_units = {'utilization_pct': '%', 'used_pct': '%', 'duration_ms': 'ms', 'throughput_gflops': 'GFLOP/s', 'logical_processors': 'count', 'total_bytes': 'bytes', 'memory_mib': 'MiB', 'file_count': 'count', 'characters': 'count'}
    for key, value in metrics.items():
        if not isinstance(value, dict) or set(value) != {'value', 'unit'} or not _number(value['value']):
            raise ValidationError('each metric requires a finite value and unit')
        if key in expected_units and value['unit'] != expected_units[key]:
            raise ValidationError(f'incorrect unit for {key}')
    if not _number(confidence) or not 0 <= confidence <= 1 or not _number(scale) or not 0 <= scale <= 1:
        raise ValidationError('confidence and display scale must be finite values in [0,1]')
    selected = next((key for key in METRIC_RANGES if key in metrics), None)
    intensity = 0.0
    calculation = {'metric': selected, 'confidence': confidence, 'scale': scale, 'intensity': 0.0}
    if selected:
        lo, hi = METRIC_RANGES[selected]
        value = metrics[selected]['value']
        intensity = max(0.0, min(1.0, (value - lo) / (hi - lo)))
        calculation.update(value=value, unit=metrics[selected]['unit'], lower=lo, upper=hi, intensity=intensity)
    color = '#ff637c' if status == 'FAIL' else '#8292ab' if status in ('SKIP', 'CANCELLED') else '#ffd17b' if category == 'benchmark' and status == 'PASS' else '#68e4b0' if status == 'PASS' else '#65baff'
    return calculation, {'visual_energy': round(intensity * confidence * scale, 8), 'color': color}


def make_event(source, category, component, metrics=None, *, status='INFO', kind='observed',
               message='', provenance=None, configuration=None, timestamp=None, event_id=None, confidence=1.0):
    e = {'schema_version': '1.0', 'event_id': event_id or str(uuid4()),
         'timestamp_utc': utc(timestamp or utc_now()), 'source': source,
         'category': category, 'component': component, 'status': status, 'data_kind': kind,
         'metrics': metrics or {}, 'message': message, 'provenance': provenance or {},
         'configuration': configuration or {}}
    e['calculated'], e['visual'] = derive(e['metrics'], status, category, confidence)
    return validate_event(e)


def validate_event(event):
    if not isinstance(event, dict):
        raise ValidationError('event must be an object')
    if event.get('schema_version') == '1.1':
        from .science import validate_scientific
        return validate_scientific(event)
    required = {'schema_version', 'event_id', 'timestamp_utc', 'source', 'category', 'component',
                'status', 'data_kind', 'metrics', 'message', 'provenance', 'configuration', 'calculated', 'visual'}
    if set(event) != required:
        raise ValidationError('event fields do not match schema 1.0')
    if event['schema_version'] != '1.0':
        raise ValidationError('unsupported event schema version')
    for key, limit in [('event_id', 128), ('source', 160), ('category', 64), ('message', 2048)]:
        if not isinstance(event[key], str) or len(event[key]) > limit or (key != 'message' and not event[key]):
            raise ValidationError(f'invalid {key}')
    if event['timestamp_utc'] != utc(event['timestamp_utc']):
        raise ValidationError('timestamp_utc must use canonical UTC milliseconds and Z')
    if event['component'] not in ORBITS or event['status'] not in STATUSES or event['data_kind'] not in KINDS:
        raise ValidationError('invalid component, status or data kind')
    metrics = event['metrics']
    if not isinstance(metrics, dict) or len(metrics) > 32:
        raise ValidationError('metrics must be an object with at most 32 entries')
    for key, m in metrics.items():
        if not isinstance(key, str) or not 1 <= len(key) <= 64 or not isinstance(m, dict) or set(m) != {'value', 'unit'}:
            raise ValidationError('each metric requires value and unit')
        if not _number(m['value']) or abs(m['value']) > 1e18 or not isinstance(m['unit'], str) or m['unit'] not in UNITS:
            raise ValidationError(f'invalid metric value or unit: {key}')
        if m['unit'] == '%' and not 0 <= m['value'] <= 100:
            raise ValidationError('percentage out of range')
        if m['unit'] != 'C' and m['value'] < 0:
            raise ValidationError('negative metric')
        if m['unit'] == 'C' and m['value'] < -273.15:
            raise ValidationError('temperature below absolute zero')
    for name in ('provenance', 'configuration', 'calculated', 'visual'):
        if not isinstance(event[name], dict):
            raise ValidationError(f'{name} must be an object')
    calc, visual = derive(metrics, event['status'], event['category'], event['calculated'].get('confidence'), event['calculated'].get('scale'))
    if event['calculated'] != calc or event['visual'] != visual:
        raise ValidationError('visual calculation does not match observation')
    try:
        encoded = json.dumps(event, allow_nan=False, ensure_ascii=False)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValidationError('event must contain finite JSON data') from exc
    if len(encoded.encode('utf-8')) > MAX_EVENT:
        raise ValidationError('event exceeds 8 KiB')
    return copy.deepcopy(event)


def load_json(path):
    with Path(path).open('rb') as f:
        data = f.read(MAX_FILE + 1)
    return decode_json(data)


def decode_json(data):
    if len(data) > MAX_FILE:
        raise ValidationError('input exceeds 96 MiB')
    try:
        return json.loads(data.decode('utf-8-sig'), parse_constant=lambda _: (_ for _ in ()).throw(ValidationError('non-finite JSON number')))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValidationError('invalid UTF-8 JSON document') from exc


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def export_events(path, events):
    validated = [validate_event(e) for e in events]
    if Path(path).suffix.lower() == '.csv':
        out = io.StringIO(newline='')
        writer = csv.writer(out)
        writer.writerow(['event_id', 'timestamp_utc', 'source', 'component', 'category', 'status', 'data_kind', 'metric', 'value', 'unit', 'classification', 'provenance_json'])
        for e in validated:
            for name, m in (e['metrics'] or {'': {'value': '', 'unit': ''}}).items():
                from .science import classification
                row = [e[k] for k in ('event_id', 'timestamp_utc', 'source', 'component', 'category', 'status', 'data_kind')] + [name, m['value'], m['unit'], classification(e, name), json.dumps({'provenance': e['provenance'], 'scientific': e.get('scientific')}, sort_keys=True)]
                writer.writerow(["'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@', '\t', '\r')) else v for v in row])
        atomic_write(path, out.getvalue())
    else:
        atomic_write(path, json.dumps({'format': 'atomverse-export/1', 'exported_at_utc': utc_now(), 'events': validated}, indent=2, allow_nan=False))


class Memory:
    def __init__(self, path, limit=MAX_EVENTS):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.limit = min(MAX_EVENTS, max(1, limit))
        self.db = sqlite3.connect(self.path, timeout=3)
        self.db.execute('PRAGMA journal_mode=DELETE')
        self.db.execute('PRAGMA max_page_count=65536')
        self.db.execute('PRAGMA busy_timeout=3000')
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 1, 2):
            self.db.close()
            raise ValidationError('unsupported database schema version')
        self.db.execute('CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, time TEXT NOT NULL, kind TEXT NOT NULL, category TEXT NOT NULL, body TEXT NOT NULL)')
        self.db.execute('CREATE INDEX IF NOT EXISTS event_time ON events(time, id)')
        self.db.commit()
        from .storage import migrate
        migrate(self.db, self.path, version)

    def add(self, events):
        if len(events) > MAX_EVENTS:
            raise ValidationError('too many events in one transaction')
        encoded = [validate_event(e) for e in events]
        inserted = 0
        with self.db:
            count = self.db.execute('SELECT count(*) FROM events').fetchone()[0]
            for e in encoded:
                body = json.dumps(e, sort_keys=True, allow_nan=False)
                existing = self.db.execute('SELECT body FROM events WHERE id=?', (e['event_id'],)).fetchone()
                if existing:
                    if existing[0] != body:
                        raise ValidationError('event ID conflicts with immutable history')
                    continue
                if count + inserted >= self.limit:
                    raise ValidationError('memory limit reached; export history and choose a new database')
                s = e.get('scientific', {})
                if s.get('classification') == 'AI_INTERPRETED' or e['category'] == 'comparison':
                    for reference in e['provenance'].get('event_ids', [])[:20]:
                        self.db.execute('UPDATE events SET ephemeral=0 WHERE id=?', (reference,))
                self.db.execute('INSERT INTO events(id,time,kind,category,body,session,entity,classification,ephemeral) VALUES (?,?,?,?,?,?,?,?,?)',
                    (e['event_id'], e['timestamp_utc'], e['data_kind'], e['category'], body, s.get('session_id', ''), s.get('entity_id', ''), s.get('classification', ''), int(s.get('retention') == 'rolling')))
                inserted += 1
        return inserted

    def events(self, kind='observed'):
        return [json.loads(row[0]) for row in self.db.execute('SELECT body FROM events WHERE kind=? ORDER BY time,id LIMIT ?', (kind, self.limit))]

    def close(self):
        self.db.close()


class Replay:
    def __init__(self, events):
        self.events = sorted([validate_event(e) for e in events], key=lambda e: (e['timestamp_utc'], e['event_id']))
        self.index = 0

    def seek(self, count):
        self.index = max(0, min(len(self.events), int(count)))
        return self.events[:self.index]


def demo_events():
    records = []
    for i in range(64):
        component = ORBITS[i % len(ORBITS)]
        category = 'benchmark' if i % 5 == 0 else 'inference' if component == 'ai' else 'execution' if component == 'code' else 'telemetry'
        records.append(make_event('demo-generator', category, component,
            {'utilization_pct': metric((i * 17 + 13) % 100, '%')}, kind='synthetic',
            status='FAIL' if i in (19, 39) else 'PASS' if category in ('benchmark', 'execution') else 'INFO',
            message='SYNTHETIC demonstration. Not a measurement.', event_id=f'demo-{i:03}',
            timestamp=f'2026-01-01T00:00:{i // 2:02}.{(i % 2) * 500:03}Z',
            provenance={'generator': 'deterministic-demo/1'}))
    return records
