import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import pytest

from atomverse.core import (Memory, Replay, ValidationError, decode_json, demo_events,
    derive, export_events, load_json, make_event, metric, validate_event, MAX_FILE)
from atomverse.adapters import import_events, arx_events
from atomverse.sources import discover_python, explain_local, inspect_repository


def event(**kwargs):
    return make_event('test', 'telemetry', 'cpu', {'utilization_pct': metric(50, '%')}, **kwargs)


def arx():
    return {'schema_version': '0.1', 'scanner': {'name': 'ARX', 'version': 'test'}, 'generated_at': '2026-11-17T12:00:00Z',
            'machine': {'cpu': {'Name': 'fixture', 'NumberOfCores': 6, 'NumberOfLogicalProcessors': 12},
                        'memory': {'total_bytes': 1000, 'available_bytes': 250},
                        'gpu': [{'Name': 'fixture GPU', 'AdapterRAM': 4294967295}]}}


def test_energy_is_reproducible_and_dimensionless():
    e = event()
    assert e['visual']['visual_energy'] == 0.5
    assert derive(e['metrics'], 'INFO', 'telemetry', 0.8, 0.25)[1]['visual_energy'] == 0.1
    assert e['metrics']['utilization_pct'] == {'value': 50, 'unit': '%'}


def test_clamping_and_missing_metrics():
    assert derive({'duration_ms': metric(10000, 'ms')}, 'INFO', 'test')[1]['visual_energy'] == 1
    assert derive({}, 'INFO', 'test')[1]['visual_energy'] == 0
    assert derive({}, 'FAIL', 'benchmark')[1]['color'] == '#ff637c'


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1, 101, True, '50', 10**1000])
def test_reject_invalid_percentage(value):
    with pytest.raises(ValidationError):
        make_event('test', 'telemetry', 'cpu', {'utilization_pct': metric(value, '%')})


@pytest.mark.parametrize('field,value', [('schema_version', '2.0'), ('status', 'SUCCESS'), ('data_kind', 'real-ish'), ('component', 'network'), ('timestamp_utc', '2026-01-01T00:00:00'), ('message', 'x' * 2049)])
def test_schema_rejections(field, value):
    e = event(); e[field] = value
    with pytest.raises(ValidationError):
        validate_event(e)


def test_wrong_units_and_forged_visual():
    with pytest.raises(ValidationError):
        make_event('test', 'benchmark', 'cpu', {'duration_ms': metric(100, 's')})
    e = event(); e['visual']['visual_energy'] = 0.9
    with pytest.raises(ValidationError):
        validate_event(e)


def test_database_immutable_and_reopen(tmp_path):
    p = tmp_path / 'memory.db'; db = Memory(p); e = event(event_id='fixed')
    assert db.add([e]) == 1
    assert db.add([e]) == 0
    changed = event(event_id='fixed', message='changed')
    with pytest.raises(ValidationError): db.add([changed])
    db.close(); db = Memory(p)
    assert db.events() == [e]
    assert db.db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    db.close()


def test_transaction_rolls_back_on_limit(tmp_path):
    db = Memory(tmp_path/'db', limit=1)
    with pytest.raises(ValidationError): db.add([event(), event()])
    assert db.events() == []
    db.close()


def test_replay_order_does_not_mutate():
    a = event(event_id='a', timestamp='2026-01-02T00:00:00Z')
    b = event(event_id='b', timestamp='2026-01-01T00:00:00Z')
    r = Replay([a, b]); assert r.seek(1) == [b]; assert r.seek(9) == [b, a]; assert r.seek(-1) == []


def test_json_roundtrip_and_csv_formula_protection(tmp_path):
    e = make_event('=unsafe()', 'test', 'cpu')
    p = tmp_path/'export.json'; export_events(p, [e]); assert import_events(p) == [e]
    p = tmp_path/'export.csv'; export_events(p, [e]); assert "'=unsafe()" in p.read_text()


@pytest.mark.parametrize('data', [b'{', b'{"v":NaN}', b'\xff', b'x' * (MAX_FILE + 1)], ids=['malformed', 'nonfinite', 'encoding', 'oversized'])
def test_invalid_json_and_input_bounds(data):
    with pytest.raises(ValidationError): decode_json(data)


def test_arx_measurements_provenance_and_idempotency():
    rows = arx_events(arx(), 'abc')
    assert len(rows) == 3
    assert rows[0]['metrics']['logical_processors']['value'] == 12
    assert rows[1]['metrics']['available_bytes']['value'] == 250
    assert 'used_pct' not in rows[1]['metrics']
    assert rows[2]['metrics'] == {}  # no false 32-bit VRAM value
    assert rows[0]['provenance']['pointer'] == '/machine/cpu'
    assert rows == arx_events(arx(), 'abc')


@pytest.mark.parametrize('version', ['0.2', '1.0', None])
def test_arx_rejects_new_contract(version):
    data = arx(); data['schema_version'] = version
    with pytest.raises(ValidationError): arx_events(data, 'abc')


def test_arx_report_preserved(tmp_path):
    p = tmp_path/'report.json'; p.write_text(json.dumps(arx()))
    before = p.read_bytes(); import_events(p); assert p.read_bytes() == before


def test_demo_never_claims_observation():
    rows = demo_events(); assert len(rows) == 64
    assert {e['data_kind'] for e in rows} == {'synthetic'}
    assert rows == demo_events()


def test_explicit_source_metadata_ignores_private_tree(tmp_path):
    (tmp_path/'a.py').write_text('not executed')
    (tmp_path/'.env').write_text('do not read')
    (tmp_path/'.git').mkdir(); (tmp_path/'.git'/'config').write_text('private')
    row = inspect_repository(tmp_path)[0]
    assert row['metrics']['file_count']['value'] == 1
    assert row['configuration']['extensions'] == {'.py': 1}


def test_python_discovery_and_invalid_target(tmp_path):
    assert discover_python(sys.executable)['python']
    with pytest.raises(ValidationError): discover_python(str(tmp_path/'absent.exe'))


@pytest.mark.parametrize('endpoint', ['https://example.com/v1', 'http://127.0.0.1.evil/v1', 'http://user:pass@localhost/v1', 'http://localhost/v1?secret=yes'])
def test_model_boundary_refuses_nonlocal_or_credentials(endpoint):
    with pytest.raises(ValidationError): explain_local(endpoint, 'model', 'question', [event()])


def test_cpu_worker_actual_output_and_invalid_workload():
    worker = Path(__file__).parents[1]/'SOFTWARE/atomverse/worker.py'
    result = subprocess.run([sys.executable, str(worker), 'cpu', '--seconds', '0.1', '--size', '8'], capture_output=True, text=True, timeout=10)
    data = json.loads(result.stdout.splitlines()[-1])
    assert data['status'] == 'PASS'
    assert data['metrics']['duration_ms']['value'] >= 100
    assert data['metrics']['checksum']['value'] == sum(sum((i+k)%7 for k in range(8)) * 8 for i in range(8))
    result = subprocess.run([sys.executable, str(worker), 'cpu', '--size', '999'], capture_output=True, text=True, timeout=10)
    data = json.loads(result.stdout.splitlines()[-1]); assert data['status'] == 'FAIL'; assert data['metrics'] == {}


def test_published_json_schema_matches_generated_events():
    import jsonschema
    schema = json.loads((Path(__file__).parents[1]/'ATOMVERSE-EVENT-SCHEMA.json').read_text())
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    for e in [event(), *demo_events(), *arx_events(arx(), 'abc')]:
        validator.validate(e)


def test_loopback_model_contract_and_interpretation_label():
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from threading import Thread
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            body = json.dumps({'choices':[{'message':{'content':'Synthetic protocol-test response; no real model.'}}]}).encode()
            self.send_response(200); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
        def log_message(self,*args): pass
    server = HTTPServer(('127.0.0.1',0),Handler)
    thread = Thread(target=server.serve_forever,daemon=True); thread.start()
    try:
        answer = explain_local(f'http://127.0.0.1:{server.server_port}/v1','fixture','Explain', [event()])
        assert answer.startswith('AI INTERPRETATION')
        assert requests[0]['stream'] is False
        assert requests[0]['max_tokens'] == 400
        assert 'evidence' in requests[0]['messages'][1]['content']
    finally:
        server.shutdown(); server.server_close(); thread.join(2)
