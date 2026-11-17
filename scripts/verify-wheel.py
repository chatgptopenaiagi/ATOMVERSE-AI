"""Acceptance against an installed wheel, with no source-directory imports."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import hashlib
import sqlite3
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--environment', type=Path, required=True)
parser.add_argument('--wheel', type=Path, required=True)
parser.add_argument('--arx', type=Path, required=True)
parser.add_argument('--gpu-python', required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--exchange', type=Path)
args = parser.parse_args()
output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
python = args.environment.resolve()/'Scripts/python.exe'
entry = python.with_name('atomverse-ai.exe')
env = os.environ.copy(); env.pop('PYTHONPATH', None)
report = {'status': 'FAIL', 'wheel_sha256': hashlib.sha256(args.wheel.read_bytes()).hexdigest(), 'checks': {}}
def run(command, timeout=30):
    result = subprocess.run([str(x) for x in command], cwd=output, env=env, capture_output=True, text=True, timeout=timeout)
    assert result.returncode == 0, (result.stdout + result.stderr)[-4000:]
    return result.stdout
try:
    with zipfile.ZipFile(args.wheel) as wheel:
        assert not any(n.endswith(('.dll','.pyd','.so','.exe')) for n in wheel.namelist())
        metadata = wheel.read(next(n for n in wheel.namelist() if n.endswith('.dist-info/WHEEL'))).decode()
        assert 'Root-Is-Purelib: true' in metadata and 'Tag: py3-none-any' in metadata
        report['checks']['pure_python_payload_and_correct_tags'] = True
        root = Path(__file__).resolve().parents[1]
        report['shared_source_sha256'] = {}
        for name in ('core.py','science.py','storage.py','mobile.py'):
            data = wheel.read('atomverse/'+name)
            assert data == (root/'SOFTWARE/atomverse'/name).read_bytes()
            report['shared_source_sha256'][name] = hashlib.sha256(data).hexdigest()
    probe = r'''
import json, importlib.metadata as md, sys
from pathlib import Path
import atomverse
from atomverse.core import Memory, make_event, metric, validate_event, export_events
assert Path(atomverse.__file__).is_relative_to(Path(sys.prefix))
assert md.version('atomverse-ai') == '0.2.0a2'
e=make_event('wheel-acceptance','telemetry','cpu',{'utilization_pct':metric(25,'%')},kind='synthetic')
assert validate_event(e)['visual']['visual_energy']==.25
m=Memory('probe.sqlite3'); assert m.add([e])==1; assert m.events('synthetic')==[e]
assert m.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'; m.close()
export_events('probe.json',[e]); assert json.loads(Path('probe.json').read_text())['events']==[e]
exchanged=0
if len(sys.argv)>1:
 from atomverse.adapters import import_events
 from atomverse.storage import recent
 records=import_events(sys.argv[1]);memory=Memory('android-exchange.sqlite3');memory.add(records)
 export_events('android-exchange.json',recent(memory,10000));memory.close()
 assert {e['event_id']:e for e in import_events('android-exchange.json')}=={e['event_id']:e for e in records}
 exchanged=len(records)
print(json.dumps({'version':atomverse.__version__,'installed_module_inside_environment':True,'requires_python':md.metadata('atomverse-ai')['Requires-Python'],'dependencies':md.requires('atomverse-ai'),'core_validation_sqlite_export':True,'android_history_records_exchanged':exchanged}))
'''
    report['installed_probe'] = json.loads(run([python, '-c', probe] + ([args.exchange.resolve()] if args.exchange else [])))
    report['checks']['version_entry_point'] = run([entry, '--version']).strip() == '0.2.0-alpha.2'
    report['checks']['module_entry_point'] = run([python, '-m', 'atomverse', '--version']).strip() == '0.2.0-alpha.2'
    report['checks']['help_entry_point'] = '--data-dir' in run([entry, '--help'])
    run([entry, '--export-licenses', output/'licenses'])
    report['checks']['license_export'] = (output/'licenses/QT-LGPL-3.0.txt').is_file()
    run([entry, '--data-dir', output/'data', '--import-arx', args.arx.resolve(), '--gpu-python', args.gpu_python,
         '--verify-mission002', output/'gui'], timeout=115)
    gui = json.loads((output/'gui/gui-verification.json').read_text())
    assert gui['status'] == 'PASS' and not gui['packaged_executable'], gui
    report['gui'] = gui
    with sqlite3.connect(output/'data/memory.sqlite3') as db:
        events = json.loads((output/'gui/observations.json').read_text())['events']
        assert all(json.loads(db.execute('SELECT body FROM events WHERE id=?',(e['event_id'],)).fetchone()[0]) == e for e in events)
    report['checks']['gui_storage_export_readback'] = True
    run([python, '-m', 'pip', 'uninstall', '-y', 'atomverse-ai'])
    run([python, '-c', "import importlib.util; assert importlib.util.find_spec('atomverse') is None"])
    report['checks']['uninstall_removed_entry_point'] = not entry.exists()
    assert all(report['checks'].values())
    report['status'] = 'PASS'
finally:
    (output/'wheel-verification.json').write_text(json.dumps(report, indent=2))
print(json.dumps({'status': report['status'], 'checks': report['checks']}))
