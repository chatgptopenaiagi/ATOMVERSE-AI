"""Run the actual Windows binary, then independently inspect its artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'SOFTWARE'))
from atomverse.core import atomic_write, validate_event


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--exe',type=Path,required=True)
    parser.add_argument('--arx',type=Path,required=True)
    parser.add_argument('--gpu-python',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--junit',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise SystemExit('Choose a fresh verification directory; previous evidence is preserved.')
    args.output.mkdir(parents=True)
    command=[str(args.exe.resolve()),'--data-dir',str((args.output/'data').resolve()),'--gpu-python',args.gpu_python,
             '--import-arx',str(args.arx.resolve()),'--verify',str((args.output/'gui').resolve())]
    start=time.monotonic()
    p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    children={}
    while p.poll() is None:
        try:
            for child in psutil.Process(p.pid).children(recursive=True):
                children[child.pid]=child.create_time()
        except psutil.Error:
            pass
        if time.monotonic()-start>110:
            for pid,created in children.items():
                try:
                    child=psutil.Process(pid)
                    if child.create_time()==created:
                        child.kill()
                except psutil.Error:
                    pass
            p.kill(); p.wait(); raise SystemExit('Executable verification timed out')
        time.sleep(0.05)
    stdout,stderr=p.communicate(timeout=2)
    if p.returncode:
        raise SystemExit(f'Executable verification failed: exit {p.returncode}; inspect private output directory')
    gui=json.loads((args.output/'gui/gui-verification.json').read_text())
    assert gui['status']=='PASS' and gui['packaged_executable'] is True
    db=sqlite3.connect(args.output/'data/memory.sqlite3')
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    events=[json.loads(row[0]) for row in db.execute('SELECT body FROM events ORDER BY time,id')]
    db.close()
    exported=json.loads((args.output/'gui/observed-export.json').read_text())['events']
    assert exported==events and len(events)==gui['retained_events']
    for event in events:
        validate_event(event)
    remaining=[]
    for pid,created in children.items():
        try:
            child=psutil.Process(pid)
            if child.create_time()==created and child.is_running(): remaining.append(pid)
        except psutil.Error: pass
    assert not remaining, 'worker survived executable shutdown'
    for name in ('real-universe.png','demo-universe.png','benchmark-arena.png'):
        assert (args.output/'gui'/name).stat().st_size>10000
    gui['external_verification']={'exit_code':p.returncode,'wall_seconds':time.monotonic()-start,
        'database_integrity':'ok','export_matches_database':True,'validated_events':len(events),
        'observed_child_processes':len(children),'surviving_child_processes':0,'stderr_bytes':len(stderr)}
    public=ROOT/'EVIDENCE'
    atomic_write(public/'ATOMVERSE-GUI-VERIFICATION.json',json.dumps(gui,indent=2))
    atomic_write(public/'ATOMVERSE-BENCHMARK-RESULTS.json',json.dumps({'recorded_at_utc':gui['started_at_utc'],'kind':'observed','results':gui['benchmark_results'],
        'timing_scope':'synchronized per-iteration wall time including host overhead; one short acceptance sample, not a performance study',
        'comparison_policy':'CPU/GPU workloads and backends differ; do not compare these values as speedup evidence'},indent=2))
    suite=ET.parse(args.junit).getroot()
    suites=list(suite.iter('testsuite')); tests=list(suite.iter('testcase'))
    summary={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'tests':len(tests),
             'failures':sum(int(s.get('failures',0)) for s in suites),'errors':sum(int(s.get('errors',0)) for s in suites),
             'skipped':sum(int(s.get('skipped',0)) for s in suites),'duration_seconds':sum(float(s.get('time',0)) for s in suites),
             'cases':[{'name':t.get('name'),'class':t.get('classname'),'seconds':float(t.get('time',0)),'passed':not any(c.tag in ('failure','error','skipped') for c in t)} for t in tests]}
    assert summary['failures']==summary['errors']==summary['skipped']==0
    summary['status']='PASS'
    atomic_write(public/'ATOMVERSE-FUNCTIONAL-TESTS.json',json.dumps(summary,indent=2))
    for name in ('real-universe.png','demo-universe.png','benchmark-arena.png'):
        (public/name).write_bytes((args.output/'gui'/name).read_bytes())
    source_files=sorted((ROOT/'SOFTWARE').rglob('*.py'))
    manifest={'version':'0.1.0-alpha.1','recorded_at_utc':datetime.now(timezone.utc).isoformat(),
              'executable':'dist/ATOMVERSE-AI/ATOMVERSE-AI.exe','sha256':digest(args.exe),'bytes':args.exe.stat().st_size,
              'packaging':'PyInstaller 6.22.3, windowed portable directory, Windows x64',
              'artifact_type':'unsigned local development build','public_binary_release':False,
              'source_files':[{'path':p.relative_to(ROOT).as_posix(),'sha256':digest(p)} for p in source_files]}
    atomic_write(public/'BUILD-MANIFEST.json',json.dumps(manifest,indent=2))
    print(json.dumps({'status':'PASS','tests':summary['tests'],'observed_events':len(events),'exe_sha256':manifest['sha256'],'surviving_workers':len(remaining)}))


if __name__=='__main__':
    main()
