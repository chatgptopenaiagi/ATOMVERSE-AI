import copy
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import pytest
from atomverse.core import Memory, ValidationError, make_event, metric, validate_event, export_events, Replay
from atomverse.science import record, classification, derived
from atomverse.observer import Collector, ObserverConfig, process_identity, cpu_delta, parent_snapshot
from atomverse.storage import recent, retain, compare
from atomverse.integrations import import_selected
from atomverse.intelligence import summary, request


def sample(value=23, **kwargs):
    return record('fixture', 'cpu', 'system:cpu', {'utilization_pct': metric(value, '%')}, **kwargs)


@pytest.mark.parametrize('cls', ['OBSERVED', 'DERIVED', 'SIMULATED', 'AI_INTERPRETED', 'UNAVAILABLE'])
def test_scientific_categories_roundtrip(cls, tmp_path):
    e = record('fixture', 'cpu', 'entity', cls=cls, message='fixture')
    assert classification(validate_event(e)) == cls
    memory = Memory(tmp_path/'memory.sqlite3'); memory.add([e])
    assert recent(memory)[0] == e
    export_events(tmp_path/'export.json', [e]); assert json.loads((tmp_path/'export.json').read_text())['events'] == [e]
    memory.close()


def test_published_scientific_schema_matches_real_collector():
    import jsonschema
    schema = json.loads((Path(__file__).parents[1]/'ATOMVERSE-EVENT-SCHEMA.json').read_text())
    c = Collector(ObserverConfig(processes=False), 'schema-test')
    try:
        events = c.sample()
        validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
        for e in events:
            validator.validate(e)
    finally: c.close()


@pytest.mark.parametrize('mutation', ['missing_metadata', 'fake_derived', 'ai_measurement', 'sim_observed', 'bad_relation', 'bad_unit', 'incomplete_process', 'incomplete_core'])
def test_invalid_science_rejected(mutation):
    e = sample()
    if mutation == 'missing_metadata': e['scientific']['metric_metadata'] = {}
    if mutation == 'fake_derived': e['scientific']['metric_metadata']['utilization_pct'] = {'classification': 'DERIVED'}
    if mutation == 'ai_measurement': e['scientific']['classification'] = 'AI_INTERPRETED'; e['data_kind'] = 'interpretation'
    if mutation == 'sim_observed': e['scientific']['classification'] = 'SIMULATED'; e['data_kind'] = 'synthetic'
    if mutation == 'bad_relation': e['scientific']['relationships'] = [{'target': 'invented'}]
    if mutation == 'bad_unit': e['metrics']['utilization_pct']['unit'] = 'W'
    if mutation == 'incomplete_process': e['scientific']['entity'] = {'type': 'process'}
    if mutation == 'incomplete_core': e['scientific']['entity'] = {'type': 'cpu_core'}
    with pytest.raises(ValidationError): validate_event(e)


def test_counter_deltas_and_reset():
    value, meta = cpu_delta((1, 1, 8), (2, 2, 16))
    assert value == 20
    assert meta['inputs']['delta_total_s'] == 10
    assert cpu_delta((1, 1, 8), (0, 2, 16)) is None
    assert cpu_delta((1, 1, 8), (1, 1, 8)) is None


@pytest.mark.parametrize('config', [ObserverConfig(interval_s=0.1), ObserverConfig(process_limit=1000), ObserverConfig(max_rows=100000), ObserverConfig(retention_hours=0), ObserverConfig(processes='yes')])
def test_configuration_bounds(config):
    with pytest.raises(ValidationError): config.validate()


def test_migration_preserves_bytes_and_backup(tmp_path):
    path = tmp_path/'legacy.sqlite3'; e = make_event('legacy', 'inventory', 'cpu')
    raw = json.dumps(e, sort_keys=True)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE events(id TEXT PRIMARY KEY,time TEXT,kind TEXT,category TEXT,body TEXT)')
        db.execute('INSERT INTO events VALUES (?,?,?,?,?)', (e['event_id'], e['timestamp_utc'], e['data_kind'], e['category'], raw))
        db.execute('PRAGMA user_version=1')
    memory = Memory(path)
    assert memory.db.execute('PRAGMA user_version').fetchone()[0] == 2
    assert memory.db.execute('SELECT body,ephemeral FROM events').fetchone() == (raw, 0)
    with sqlite3.connect(str(path)+'.v1-backup') as backup:
        assert backup.execute('SELECT body FROM events').fetchone()[0] == raw
        assert backup.execute('PRAGMA user_version').fetchone()[0] == 1
    memory.add([sample()]); memory.close()
    reopened = Memory(path); assert len(recent(reopened)) == 2; reopened.close()


def test_retention_protects_legacy_and_linked_evidence(tmp_path):
    m = Memory(tmp_path/'memory.sqlite3'); old = '2020-01-01T00:00:00.000Z'
    legacy = make_event('legacy', 'test', 'cpu', timestamp=old)
    linked = sample(timestamp=old); rolling = sample(timestamp=old)
    m.add([legacy, linked, rolling])
    explanation = record('model', 'ai', 'ai:1', cls='AI_INTERPRETED', rolling=False, provenance={'event_ids': [linked['event_id']]})
    m.add([explanation]); assert retain(m, hours=1) == 1
    assert {e['event_id'] for e in recent(m)} == {legacy['event_id'], linked['event_id'], explanation['event_id']}
    assert m.db.execute('SELECT sum(removed) FROM retention_audit').fetchone()[0] == 1
    assert m.db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'; m.close()


def test_retention_row_limit_and_replay_immutable(tmp_path):
    m = Memory(tmp_path/'m.sqlite3'); events = [sample(i % 100) for i in range(100)]; m.add(events)
    assert retain(m, incoming=20, max_rows=100) == 20
    saved = recent(m); replay = Replay(saved); assert len(replay.seek(20)) == 20
    assert recent(m) == saved; m.close()


def test_retention_cannot_exceed_configured_cap_with_protected_rows(tmp_path):
    m = Memory(tmp_path/'m.sqlite3'); m.add([make_event('legacy', 'test', 'cpu') for _ in range(70)])
    with pytest.raises(ValidationError): retain(m, incoming=42, max_rows=100)
    assert len(recent(m)) == 70
    m.close()


def test_comparison_requires_comparable_source_and_records_inputs():
    events = [sample(i) for i in (10, 20, 30, 40)]
    e = compare(events, 'system:cpu', 'utilization_pct')
    assert e['metrics']['earlier_mean']['value'] in (15, 20, 25, 30, 35)  # UUID breaks equal timestamp ties only in DB, input order preserved here.
    assert e['metrics']['earlier_mean']['value'] == 15
    assert e['metrics']['later_mean']['value'] == 35
    assert len(e['provenance']['event_ids']) == 4
    events[0]['configuration'] = {'different': True}
    with pytest.raises(ValidationError): compare(events, 'system:cpu', 'utilization_pct')


def test_ai_summary_excludes_process_metadata_and_rejects_remote():
    hardware = sample(); hardware['message'] = 'PRIVATE TEXT'
    proc = record('fixture', 'code', 'process:1', entity={'name': 'PRIVATE PROCESS'})
    text = json.dumps(summary([hardware, proc]))
    assert 'PRIVATE' not in text
    assert hardware['event_id'] in text
    with pytest.raises(ValidationError): request('https://example.com', 'model', 'why', summary([hardware]))
    with pytest.raises(ValidationError): summary([proc])


@pytest.mark.parametrize('suffix', ['', '/v1'])
def test_local_ai_protocol_preserves_classification_and_provenance(suffix):
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    received = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            body = {'message': {'content': 'Fixture interpretation, not a hardware measurement.'}}
            if suffix: body = {'choices': [{'message': body['message']}]}
            encoded = json.dumps(body).encode(); self.send_response(200); self.send_header('Content-Length', str(len(encoded))); self.end_headers(); self.wfile.write(encoded)
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    event = sample()
    try:
        answer = request(f'http://127.0.0.1:{server.server_port}{suffix}', 'fixture-model', 'Explain.', summary([event]))
        assert classification(answer) == 'AI_INTERPRETED' and answer['metrics'] == {}
        assert answer['provenance']['event_ids'] == [event['event_id']]
        assert received[0]['stream'] is False
        if not suffix: assert received[0]['options']['num_gpu'] == 0 and received[0]['keep_alive'] == 0
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_optional_adapters_versioned_and_idempotent(tmp_path):
    cog = tmp_path/'cog.json'
    cog.write_text(json.dumps({'version': '2.0.0', 'events': [{'Timestamp': '2026-11-17T12:00:00+01:00', 'Category': 1, 'Outcome': 4}]}))
    a = import_selected(cog); assert a == import_selected(cog)
    assert a[0]['status'] == 'FAIL' and a[0]['timestamp_utc'] == '2026-11-17T11:00:00.000Z'
    dragon = tmp_path/'dragon.json'
    dragon.write_text(json.dumps({'schema_version': 1, 'registry_version': 'module-registry/1', 'read_only': True, 'as_of': '2026-11-17T12:00:00Z', 'modules': [{'definition': {'module_id': 'local_ai'}, 'observation': {'runtime_state': 'unavailable'}}]}))
    assert import_selected(dragon)[0]['status'] == 'SKIP'
    data = json.loads(dragon.read_text()); data['registry_version'] = 'future/2'; dragon.write_text(json.dumps(data))
    with pytest.raises(ValidationError): import_selected(dragon)


def test_real_windows_sampling_and_permissions():
    c = Collector(ObserverConfig(processes=False, gpu=False), 'test')
    try:
        before = datetime.now(timezone.utc); first = c.sample(); time.sleep(0.05); second = c.sample()
        assert 0 <= second[0]['metrics']['utilization_pct']['value'] <= 100
        assert any(e['metrics'].get('available_bytes', {}).get('value', 0) > 0 for e in second)
        assert any('read_bytes_per_s' in e['metrics'] for e in second)
        assert not any(e['component'] == 'gpu' or e.get('scientific', {}).get('entity', {}).get('type') == 'process' for e in second)
        assert all(datetime.fromisoformat(e['timestamp_utc']) >= before.replace(microsecond=(before.microsecond // 1000)*1000) for e in first)
        assert all(validate_event(e) == e for e in second)
    finally: c.close()


def test_real_process_parent_identity_and_termination():
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(15)'], creationflags=subprocess.CREATE_NO_WINDOW)
    c = Collector(ObserverConfig(process_limit=2, gpu=False), 'test', child.pid)
    try:
        assert parent_snapshot()[child.pid] == os.getpid()
        events = c.sample()
        process = next(e for e in events if e.get('scientific', {}).get('entity', {}).get('pid') == child.pid)
        assert any(r['type'] == 'PARENT' and r['target'].startswith(f'process:{os.getpid()}@') for r in process['scientific']['relationships'])
        identity = process['scientific']['entity_id']
        assert process_identity(child.pid, 1) != process_identity(child.pid, 2)
        child.terminate(); child.wait(timeout=5)
        exited = next(e for e in c.sample() if e['category'] == 'process_exit' and e['scientific']['entity_id'] == identity)
        assert exited['scientific']['entity']['state'] == 'terminated'
    finally:
        if child.poll() is None: child.terminate(); child.wait(timeout=5)
        c.close()


def test_gpu_failure_is_explicit_and_other_sources_continue(monkeypatch):
    import atomverse.observer as module
    class Missing:
        reason = 'fixture driver unavailable'
        def sample(self): return []
        def close(self): pass
    monkeypatch.setattr(module, 'Nvidia', Missing)
    c = Collector(ObserverConfig(processes=False), 'test')
    events = c.sample(); c.close()
    gpu = next(e for e in events if e['component'] == 'gpu')
    assert classification(gpu) == 'UNAVAILABLE' and gpu['metrics'] == {}
    assert any('available_bytes' in e['metrics'] for e in events)


def test_live_gui_updates_labels_queue_bounds_and_shutdown(tmp_path):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from atomverse.living import LivingWindow
    app = QApplication.instance() or QApplication([])
    w = LivingWindow(tmp_path); w.show()
    try:
        assert not w.observer.active
        w.interval.setValue(0.5); w.toggle_live()
        deadline = time.monotonic() + 10
        while w.observer.samples < 3 and time.monotonic() < deadline: QTest.qWait(100)
        w.drain_observations()
        assert w.observer.samples >= 3 and w.scene.frame_count > 5
        assert len(w.observer.queue) <= 4
        assert 'LIVE' in w.mode_badge.text()
        w.nav.setCurrentRow(2); assert w.table.rowCount() > 0
        assert any('DERIVED' in w.table.item(i, 3).text() for i in range(w.table.rowCount()))
        w.nav.setCurrentRow(6); assert w.process_tree.topLevelItemCount() > 0
        w.mode.setCurrentIndex(2); assert not w.observer.active and 'REPLAY' in w.mode_badge.text()
        w.mode.setCurrentIndex(0); assert all(classification(e) == 'SIMULATED' for e in w.displayed)
        w.toggle_live(); QTest.qWait(300)
    finally:
        w.close(); app.processEvents()
    assert not w.observer.active and not w.live_poll.isActive()
