"""Android adapter and UI bridge. Uses the unmodified desktop scientific core.

Only the native Activity supplies measurements; no Windows APIs or Qt imports.
All methods are called by one Android executor, which owns the SQLite connection.
"""
import hashlib
import json
import os
import tempfile
from pathlib import Path
from uuid import uuid4
from threading import Lock
from .core import Memory, Replay, ValidationError, decode_json, demo_events, metric, validate_event, utc_now
from .science import record, classification, derived, COLORS
from .storage import recent, retain

MAX_IMPORT = 4 * 1024 * 1024
_initialization_lock = Lock()


class Mobile:
    def __init__(self, directory):
        # Android can recreate an Activity before its previous worker drains.
        # Serialize first-open migration across those short-lived owners.
        with _initialization_lock:
            self.memory = Memory(Path(directory) / 'atomverse.sqlite3')
        self.session = 'android:' + str(uuid4())
        self.previous = None
        self.rows = 3000
        self.hours = 24

    def packet(self, events, mode):
        events = events[-256:]
        return json.dumps({'mode': mode, 'events': events, 'objects': [
            {'id': e['event_id'], 'orbit': e['component'], 'energy': e['visual']['visual_energy'],
             'color': COLORS[classification(e)], 'classification': classification(e),
             'phase': int(hashlib.sha256((e.get('scientific', {}).get('entity_id') or e['event_id']).encode()).hexdigest()[:8], 16) / 2**32 * 6.283185307,
             'label': e.get('scientific', {}).get('entity_id', e['source'])}
            for e in events[-256:]], 'stored': self.memory.db.execute('SELECT count(*) FROM events').fetchone()[0]}, allow_nan=False)

    def sample(self, raw_json):
        raw = json.loads(raw_json)
        timestamp = utc_now()
        provenance = {'adapter': 'android-sdk/1', 'scope': 'foreground app and documented public device APIs'}
        def event(source, orbit, entity, metrics=None, **kwargs):
            return record(source, orbit, entity, metrics, session=self.session, timestamp=timestamp,
                          provenance=provenance, **kwargs)
        events = []
        for field, orbit, source in [('ram', 'memory', 'Android ActivityManager.MemoryInfo'),
                                      ('storage', 'storage', 'Android StatFs app-data volume')]:
            values = raw.get(field)
            if values and values['total'] > 0 and 0 <= values['available'] <= values['total']:
                total, available = values['total'], values['available']
                events.append(event(source, orbit, 'android:' + field,
                    {'total_bytes': metric(total, 'bytes'), 'available_bytes': metric(available, 'bytes'),
                     'used_pct': metric(100 * (total - available) / total, '%')},
                    metadata={'total_bytes': {'classification': 'OBSERVED'}, 'available_bytes': {'classification': 'OBSERVED'},
                              'used_pct': derived('100 * (total - available) / total', total=total, available=available)}))
            else:
                events.append(event(source, orbit, 'android:' + field, cls='UNAVAILABLE', unavailable={field: 'Public API unavailable or inconsistent counters'}))
        cpu, elapsed, cores = raw.get('app_cpu_ms'), raw.get('elapsed_ms'), raw.get('logical_processors')
        if isinstance(cpu, (int, float)) and isinstance(elapsed, (int, float)) and isinstance(cores, int) and cores > 0:
            metrics = {'cpu_time_ms': metric(cpu, 'ms'), 'logical_processors': metric(cores, 'count')}
            metadata = {k: {'classification': 'OBSERVED'} for k in metrics}
            unavailable = {'system_utilization': 'Android does not expose reliable device-wide CPU utilization to this application'}
            if self.previous and elapsed > self.previous[1] and cpu >= self.previous[0]:
                dc, dt = cpu - self.previous[0], elapsed - self.previous[1]
                metrics['utilization_pct'] = metric(min(100, 100 * dc / dt / cores), '%')
                metadata['utilization_pct'] = derived('min(100, 100 * delta_app_cpu_ms / delta_elapsed_ms / logical_processors)',
                    delta_app_cpu_ms=dc, delta_elapsed_ms=dt, logical_processors=cores)
            else:
                unavailable['utilization_pct'] = 'Needs two monotonic app CPU observations'
            self.previous = (cpu, elapsed)
            events.append(event('Android Process.getElapsedCpuTime', 'cpu', 'android:atomverse-app', metrics,
                metadata=metadata, unavailable=unavailable, message='CPU utilization is this app only, normalized across reported logical processors.'))
        else:
            events.append(event('Android Process', 'cpu', 'android:atomverse-app', cls='UNAVAILABLE', unavailable={'cpu': 'Missing app CPU counters'}))
        if raw.get('app_pss_bytes', -1) >= 0:
            events.append(event('Android Debug.MemoryInfo', 'memory', 'android:app-pss',
                {'pss_bytes': metric(raw['app_pss_bytes'], 'bytes')}, message='App proportional set size (PSS), not whole-device RAM or RSS.'))
        events.append(event('Android public SDK capability check', 'gpu', 'android:gpu', cls='UNAVAILABLE',
            unavailable={'utilization_pct': 'No verified public GPU utilization sensor', 'vram_bytes': 'No verified public VRAM allocation sensor',
                         'temperature': 'No verified public GPU temperature sensor'},
            message='No NVIDIA CUDA claims. Rendering API support does not measure GPU workload.'))
        retain(self.memory, incoming=len(events), max_rows=self.rows, hours=self.hours)
        self.memory.add(events)
        return self.packet(events, 'LIVE OBSERVATIONS · app CPU / device RAM / data volume')

    def demo(self):
        return self.packet(demo_events(), 'DEMO: SYNTHETIC DATA')

    def history(self, count=256):
        total = self.memory.db.execute('SELECT count(*) FROM events').fetchone()[0]
        position = min(total, max(0, int(count)))
        shown = min(position, 256)
        events = [json.loads(row[0]) for row in self.memory.db.execute(
            'SELECT body FROM events ORDER BY time,id LIMIT ? OFFSET ?', (shown, position-shown))]
        return self.packet(Replay(events).seek(shown), f'RECORDED HISTORY · position {position}/{total} · up to 256 events')

    def import_history(self, text):
        if len(text.encode('utf-8')) > MAX_IMPORT:
            raise ValidationError('Android import limit is 4 MiB')
        data = decode_json(text.encode('utf-8'))
        if not isinstance(data, dict) or data.get('format') != 'atomverse-export/1' or not isinstance(data.get('events'), list):
            raise ValidationError('Expected atomverse-export/1 document')
        if len(data['events']) > 1000:
            raise ValidationError('Android import limit is 1000 events per document')
        events = [validate_event(e) for e in data['events']]
        # Imported evidence is immutable, protected from rolling live retention.
        # Bodies stay byte-semantically compatible: pin rows separately, without rewriting the events.
        with self.memory.db:
            self.memory.add(events)
            self.memory.db.executemany('UPDATE events SET ephemeral=0 WHERE id=?', [(e['event_id'],) for e in events])
        return self.packet(events[-256:], 'IMPORTED HISTORY · classifications shown per object')

    def export_history(self):
        return json.dumps({'format': 'atomverse-export/1', 'exported_at_utc': utc_now(), 'events': recent(self.memory, 10000)}, allow_nan=False)

    def export_file(self, destination):
        """Stream retained history for SAF without a large Java JSON string."""
        destination = Path(destination)
        fd, temporary = tempfile.mkstemp(dir=destination.parent, prefix='atomverse-export-', suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                stream.write('{"format":"atomverse-export/1","exported_at_utc":' + json.dumps(utc_now()) + ',"events":[')
                first = True
                for row in self.memory.db.execute('SELECT body FROM events ORDER BY time,id LIMIT 10000'):
                    e = validate_event(json.loads(row[0]))
                    if not first:
                        stream.write(',')
                    stream.write(json.dumps(e, allow_nan=False)); first = False
                stream.write(']}'); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return str(destination)

    def settings(self, rows, hours):
        if not 100 <= int(rows) <= 10000 or not 1 <= int(hours) <= 720:
            raise ValidationError('Retention requires 100–10000 rows and 1–720 hours')
        self.rows, self.hours = int(rows), int(hours)

    def integrity(self):
        return self.memory.db.execute('PRAGMA integrity_check').fetchone()[0]

    def close(self):
        self.memory.close()
