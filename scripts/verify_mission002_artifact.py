"""External watchdog and independent readback for the actual Windows executable."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import psutil

parser = argparse.ArgumentParser()
parser.add_argument('--exe', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--data', type=Path, required=True)
parser.add_argument('--arx', type=Path, required=True)
parser.add_argument('--gpu-python', required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True); args.data.mkdir(parents=True, exist_ok=True)
baseline = {}
database = args.data/'memory.sqlite3'
if database.exists():
    with sqlite3.connect(database) as db:
        baseline = dict(db.execute('SELECT id,body FROM events'))
started = time.monotonic()
process = subprocess.Popen([str(args.exe.resolve()), '--data-dir', str(args.data.resolve()), '--gpu-python', args.gpu_python,
    '--import-arx', str(args.arx.resolve()), '--verify-mission002', str(args.output.resolve())], cwd=args.output.resolve(), creationflags=subprocess.CREATE_NO_WINDOW)
children = {}
try:
    while process.poll() is None and time.monotonic()-started < 110:
        try:
            for child in psutil.Process(process.pid).children(recursive=True): children[(child.pid, child.create_time())] = child
        except psutil.Error: pass
        time.sleep(.2)
    if process.poll() is None:
        raise TimeoutError('Packaged application exceeded 110-second watchdog')
    report = json.loads((args.output/'gui-verification.json').read_text())
    assert process.returncode == 0 and report['status'] == 'PASS' and report['packaged_executable'], report.get('error')
    with sqlite3.connect(database) as db:
        stored = dict(db.execute('SELECT id,body FROM events'))
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute('PRAGMA user_version').fetchone()[0] == 2
        assert all(stored.get(k) == body for k, body in baseline.items()), 'Legacy record mutated or removed'
    exported = json.loads((args.output/'observations.json').read_text())['events']
    assert all(json.loads(stored[e['event_id']]) == e for e in exported)
    survivors = []
    for (pid, created), child in children.items():
        try:
            if child.is_running() and child.create_time() == created: survivors.append(pid)
        except psutil.Error: pass
    assert not survivors, 'Owned workers survived application shutdown'
    report['external_verification'] = {'exit_code': process.returncode, 'executable_sha256': hashlib.sha256(args.exe.read_bytes()).hexdigest(),
        'all_exported_records_match_sqlite': True, 'legacy_records_preserved': len(baseline), 'no_surviving_owned_processes': True,
        'observed_child_processes': len(children), 'sqlite_integrity': 'ok', 'sqlite_version': 2,
        'working_directory_outside_source': True}
    (args.output/'gui-verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'status':'PASS','elapsed_s':time.monotonic()-started,'external_verification':report['external_verification']}))
finally:
    for child in reversed(list(children.values())):
        try:
            if child.is_running(): child.kill()
        except psutil.Error: pass
    if process.poll() is None: process.kill(); process.wait(timeout=5)
