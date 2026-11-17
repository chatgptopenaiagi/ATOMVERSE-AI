"""Assemble reviewed evidence and a complete portable ZIP after acceptance."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile

root = Path(__file__).resolve().parents[1]
local = root/'.local/mission002'
evidence = root/'EVIDENCE'
version = '0.2.0-alpha.1'
folder = root/f'dist/releases/{version}/ATOMVERSE-AI'
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path, value): path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''): h.update(block)
    return h.hexdigest()

gui = read(local/'release-gui/gui-verification.json')
assert gui['status']=='PASS' and gui['packaged_executable'] and gui['external_verification']['legacy_records_preserved']==44
assert sha(folder/'ATOMVERSE-AI.exe')==gui['external_verification']['executable_sha256']
ai = read(local/'packaged-ai/ai-verification.json')
assert ai['status']=='PASS' and ai['packaged_executable'] and ai['clean_shutdown']
driver=read(local/'qwen-packaged-driver.json')
assert driver['status']=='PASS' and driver['owned_server_stopped']
suite = ET.parse(local/'tests-final.xml').getroot().find('testsuite')
assert int(suite.attrib['failures'])==0 and int(suite.attrib['errors'])==0
tests={'status':'PASS','tests':int(suite.attrib['tests']),'failures':0,'errors':0,'skipped':int(suite.attrib['skipped']),
       'elapsed_s':float(suite.attrib['time']),'mission001_tests_preserved':46,
       'cases':[{'name':c.attrib['name'],'module':c.attrib.get('classname'), 'seconds':float(c.attrib.get('time',0))} for c in suite.findall('testcase')],
       'execution_scope':'Real Windows APIs, process lifecycle and Qt GUI; explicit protocol/adapter fixtures are distinguished by test names.',
       'exploratory_failure':'An overlapping development test run recorded observer startup timeout. The isolated final full suite passed; no test was removed.'}
write(evidence/'MISSION-002-TEST-RESULTS.json',tests)
write(evidence/'MISSION-002-GUI-VERIFICATION.json',gui)
performance=gui['performance']
performance['scope_notes']=['Idle phase means no injected load; unrelated workstation activity continued.',
    'Configured rendering cap is 30 fps, temporarily reduced to 15 during benchmarks.',
    'CPU and RSS cover GUI plus observer, excluding optional benchmark/model workers.',
    '30-second baseline/load experiment is not a long-duration soak test.',
    'Maximum GUI tick delay includes synchronous acceptance-driver assertions and export readback; p95 covers the full run.']
write(evidence/'MISSION-002-PERFORMANCE.json',performance)
write(evidence/'MISSION-002-AI-VERIFICATION.json',{'cold_start':read(local/'qwen-verification.json'),'warmed_endpoint_driver':driver,'packaged_application':ai})
shutil.copy2(local/'release-gui/recorded-universe.png',evidence/'MISSION-002-UNIVERSE.png')
shutil.copy2(local/'packaged-ai/ai-interpretation.png',evidence/'MISSION-002-AI.png')

preservation=[]
for item in read(root/'.local/preservation-before.json'):
    path=Path(item['Path']); value=sha(path)
    preservation.append({'component':path.parent.name+'/'+path.name,'sha256':value,'matches_mission001_baseline':value==item['Hash'].lower()})
assert all(p['matches_mission001_baseline'] for p in preservation)
old={'executable':sha(root/'dist/ATOMVERSE-AI/ATOMVERSE-AI.exe'),'zip':sha(root/'dist/ATOMVERSE-AI-0.1.0-alpha.1-win-x64.zip')}
assert old=={'executable':'9c44987308677d9c0478f7cead382bee848eb97fa64505cf669dce4c18a3a7d4','zip':'b31a924defde98a843e70297dadeab6d2d30f497046bd06f0e679dd396178620'}
for name in ('README.md','THIRD-PARTY-NOTICES.md','LICENSE-DECISION.md'):
    shutil.copy2(root/name,folder/name)
shutil.copy2(root/f'RELEASES/{version}/PORTABLE-README.txt',folder/'PORTABLE-README.txt')
files={p.relative_to(folder).as_posix():sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}
archive=root/f'dist/ATOMVERSE-AI-{version}-win-x64.zip'
if archive.exists(): raise RuntimeError('Versioned ZIP exists; do not overwrite a release artifact')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for name in files:z.write(folder/name,'ATOMVERSE-AI/'+name)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert len(z.infolist())==len(files)
    for name,digest in files.items():assert hashlib.sha256(z.read('ATOMVERSE-AI/'+name)).hexdigest()==digest
checksums=root/f'dist/ATOMVERSE-AI-{version}-SHA256SUMS.txt'
checksums.write_text(f'{sha(archive)}  {archive.name}\n{sha(folder/"ATOMVERSE-AI.exe")}  ATOMVERSE-AI.exe\n',encoding='ascii')
manifest={'version':version,'executable_sha256':sha(folder/'ATOMVERSE-AI.exe'),'zip_sha256':sha(archive),'zip_bytes':archive.stat().st_size,
          'file_count':len(files),'all_zip_file_hashes_match_verified_portable_folder':True,'files':files,
          'application_source_sha256':{p.relative_to(root).as_posix():sha(p) for p in sorted((root/'SOFTWARE').rglob('*.py'))}}
write(root/f'RELEASES/{version}/BUILD-MANIFEST.json',manifest)
final={'mission':'002','version':version,'status':'LOCAL_ACCEPTANCE_PASS','publication':{'status':'PENDING_REMOTE_READBACK'},
       'acceptance':{'mission001_preserved':True,'automatic_live_cpu_memory':True,'gpu_provenance':True,'real_windows_process_relationships':True,
       'live_measurements_drive_graphics':True,'persisted_history_and_replay':True,'scientific_categories_distinct':True,
       'optional_integrations_fail_gracefully':True,'bounded_observer_overhead_measured':True,'automated_and_packaged_tests_pass':True,
       'windows_executable_launches':True,'portable_zip_integrity':True,'documentation_and_evidence':True,'public_source_verified':False},
       'automated_tests':tests['tests'],'packaged_gui':gui['external_verification'],'packaged_ai':{'status':ai['status'],'elapsed_s':ai['elapsed_s'],'observer_samples':ai['observer_samples']},
       'artifact':{k:manifest[k] for k in ('executable_sha256','zip_sha256','zip_bytes','file_count')},
       'previous_artifact_hashes_unchanged':old,'selected_existing_installation_checks':preservation,
       'preservation_scope':'Selected existing executable/source hashes and original artifact hashes; no claim of whole-disk forensic equivalence.',
       'limitations':['No reliable CPU temperature sensor, per-process GPU utilization/VRAM or verified disk response time.',
        'Process observation and visible history are deliberately bounded.', 'COG/DRAGONHYDRA real private exports were not tested; source contracts and fixtures were tested.',
        'Cold Qwen startup exceeded the inference deadline; warmed selected-event inference passed.',
        'Short baseline/load performance run, not a long-duration soak or cross-hardware certification.',
        'Unsigned experimental Windows prerelease; project license decision remains with owner.']}
write(evidence/'MISSION-002-FINAL-VERIFICATION.json',final)
print(json.dumps({'status':'READY_FOR_PUBLICATION','zip':str(archive),'zip_sha256':manifest['zip_sha256'],'tests':tests['tests']}))
