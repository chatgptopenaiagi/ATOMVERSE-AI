import json
import sqlite3
import pytest
from atomverse.core import ValidationError, validate_event, demo_events
from atomverse.mobile import Mobile
from atomverse.science import classification


def raw(cpu=100, elapsed=1000):
    return json.dumps({'ram': {'total': 8192, 'available': 2048}, 'storage': {'total': 16384, 'available': 8192},
                       'app_cpu_ms': cpu, 'elapsed_ms': elapsed, 'logical_processors': 2, 'app_pss_bytes': 1024})


def test_mobile_formulas_provenance_and_unavailability(tmp_path):
    m = Mobile(tmp_path)
    first = json.loads(m.sample(raw()))
    second = json.loads(m.sample(raw(300, 2000)))
    assert {o['label']:o['phase'] for o in first['objects']} == {o['label']:o['phase'] for o in second['objects']}
    for e in first['events'] + second['events']:
        assert validate_event(e) == e
        assert e['provenance']['adapter'] == 'android-sdk/1'
    cpu = next(e for e in second['events'] if e['component'] == 'cpu')
    assert cpu['metrics']['utilization_pct']['value'] == 10
    assert classification(cpu, 'utilization_pct') == 'DERIVED'
    ram = next(e for e in second['events'] if e['source'] == 'Android ActivityManager.MemoryInfo')
    assert ram['visual']['visual_energy'] == .75
    gpu = next(e for e in second['events'] if e['component'] == 'gpu')
    assert classification(gpu) == 'UNAVAILABLE' and not gpu['metrics']
    assert m.integrity() == 'ok'
    m.close()


def test_mobile_roundtrip_replay_and_atomic_rejection(tmp_path):
    m = Mobile(tmp_path)
    m.sample(raw())
    original = json.loads(m.export_history())
    imported = {'format': 'atomverse-export/1', 'events': demo_events()}
    m.import_history(json.dumps(imported))
    exported = json.loads(m.export_history())
    assert {e['data_kind'] for e in exported['events']} == {'observed', 'synthetic'}
    assert original['events'][0] in exported['events']
    assert len(json.loads(m.history(3))['events']) == 3
    m.export_file(tmp_path/'streamed.json')
    assert json.loads((tmp_path/'streamed.json').read_text())['events'] == exported['events']
    count = len(exported['events'])
    for malformed in ['[]', '{', json.dumps({'format': 'atomverse-export/1', 'events': [original['events'][0], {}]})]:
        with pytest.raises((ValidationError, ValueError)):
            m.import_history(malformed)
    assert len(json.loads(m.export_history())['events']) == count
    m.close()
    m = Mobile(tmp_path)
    assert len(json.loads(m.export_history())['events']) == count
    m.close()


def test_mobile_bounds_missing_sensors_and_demo_isolation(tmp_path):
    m = Mobile(tmp_path)
    assert json.loads(m.demo())['stored'] == 0
    packet = json.loads(m.sample('{}'))
    assert all(classification(e) == 'UNAVAILABLE' for e in packet['events'])
    m.settings(100, 1)
    for i in range(30):
        m.sample(raw(i * 10, i * 1000))
    assert len(json.loads(m.export_history())['events']) <= 100
    with pytest.raises(ValidationError): m.import_history(' ' * (4 * 1024 * 1024 + 1))
    with pytest.raises(ValidationError): m.settings(99, 0)
    m.close()


def test_android_activity_recreation_serializes_first_database_open(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    barrier = Barrier(4)
    def activity():
        barrier.wait()
        m = Mobile(tmp_path)
        try:
            return m.integrity(), m.memory.db.execute('PRAGMA user_version').fetchone()[0]
        finally:
            m.close()
    with ThreadPoolExecutor(max_workers=4) as workers:
        result = list(workers.map(lambda _: activity(), range(4)))
    assert result == [('ok', 2)] * 4


def test_installed_worker_command_uses_package_module():
    from pathlib import Path
    from atomverse.live_controller import command
    executable, args = command('--observer-worker')
    assert Path(args[0]).name == '__main__.py' and Path(args[0]).exists()


def test_desktop_routes_mobile_history_without_relabeling(tmp_path):
    from PySide6.QtWidgets import QApplication
    from atomverse.living import LivingWindow
    from atomverse.core import make_event, metric
    app = QApplication.instance() or QApplication([])
    window = LivingWindow(tmp_path)
    real = make_event('adapter-contract-fixture', 'telemetry', 'memory', {'used_pct': metric(30, '%')})
    simulated = demo_events()[0]
    try:
        window.ingest_exchange([real, simulated])
        assert window.memory.events() == [real]
        assert not window.memory.events('synthetic')
        window.mode.setCurrentIndex(0)
        assert window.displayed == [simulated]
        assert classification(window.displayed[0]) == 'SIMULATED'
    finally:
        window.close()
