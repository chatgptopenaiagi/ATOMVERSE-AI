"""Verify the final signed ARM64 APK on an explicitly selected Android target."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'SOFTWARE'))
from atomverse.adapters import import_events
from atomverse.core import Memory, export_events, validate_event
from atomverse.science import classification
from atomverse.storage import recent

p = argparse.ArgumentParser()
p.add_argument('--apk', type=Path, required=True)
p.add_argument('--test-apk', type=Path, required=True)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--device', required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
adb = a.sdk/'platform-tools/adb.exe'
report = {'status': 'FAIL', 'apk_sha256': hashlib.sha256(a.apk.read_bytes()).hexdigest(), 'checks': {}}
def run(args, timeout=30):
    r = subprocess.run([str(v) for v in args], capture_output=True, text=True, timeout=timeout)
    assert r.returncode == 0, (r.stdout+r.stderr)[-4000:]
    return r.stdout
def device(*args, timeout=30): return run([adb, '-s', a.device, *args], timeout)
def screenshot(name):
    with (a.output/name).open('wb') as stream:
        r = subprocess.run([str(adb), '-s', a.device, 'exec-out', 'screencap', '-p'], stdout=stream, timeout=15)
        assert r.returncode == 0 and (a.output/name).stat().st_size > 10000
def tap(label):
    device('shell', 'uiautomator', 'dump', '/sdcard/atomverse-acceptance-ui.xml')
    device('pull', '/sdcard/atomverse-acceptance-ui.xml', a.output/'ui.xml')
    node = next(n for n in ET.parse(a.output/'ui.xml').iter('node') if n.get('text') == label)
    x1,y1,x2,y2 = map(int,re.findall(r'\d+',node.get('bounds')))
    device('shell', 'input', 'tap', (x1+x2)//2, (y1+y2)//2)
try:
    with zipfile.ZipFile(a.apk) as z:
        abis = sorted({n.split('/')[1] for n in z.namelist() if n.startswith('lib/') and n.endswith('.so')})
        assert abis == ['arm64-v8a'], abis
        assert 'assets/CHAQUOPY.txt' in z.namelist() and 'assets/PYTHON.txt' in z.namelist()
        report['checks']['arm64_only_and_runtime_notices'] = True
    badging = run([a.sdk/'build-tools/36.0.0/aapt.exe','dump','badging',a.apk])
    assert "name='com.atomverse.ai'" in badging and "versionName='0.2.0-alpha.2'" in badging
    assert 'application-debuggable' not in badging and 'android.permission.INTERNET' not in badging
    (a.output/'apk-badging.txt').write_text(badging)
    signature = run([a.sdk/'build-tools/36.0.0/apksigner.bat','verify','--verbose','--print-certs',a.apk])
    assert 'Verified using v2 scheme' in signature
    (a.output/'signature.txt').write_text(signature)
    report['checks']['release_metadata_signature_no_network_permission'] = True
    device('install','--abi','arm64-v8a','-r',a.apk,timeout=90)
    device('install','-r',a.test_apk,timeout=90)
    report['device'] = {'sdk': device('shell','getprop','ro.build.version.sdk').strip(),
                        'abis': device('shell','getprop','ro.product.cpu.abilist').strip(),
                        'native_bridge': device('shell','getprop','ro.dalvik.vm.native.bridge').strip(),
                        'physical_device': False, 'description': 'Owned API 37 Google Play x86_64 emulator running the ARM64 APK through libndk_translation'}
    package = device('shell','dumpsys','package','com.atomverse.ai')
    assert 'primaryCpuAbi=arm64-v8a' in package
    report['checks']['installed_arm64_abi'] = True
    device('shell','am','start','-W','-n','com.atomverse.ai/.MainActivity')
    # Wait for a real data packet, not merely Activity creation or process exit 0.
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        device('shell', 'uiautomator', 'dump', '/sdcard/atomverse-ready.xml')
        xml = device('shell', 'cat', '/sdcard/atomverse-ready.xml')
        if 'DEMO: SYNTHETIC DATA' in xml:
            break
        if 'ERROR ·' in xml:
            raise AssertionError('Android startup reported an application error: ' + xml[:2000])
        time.sleep(1)
    else:
        raise AssertionError('Android demo did not become ready within 90 seconds')
    screenshot('android-demo.png'); tap('Start live'); time.sleep(5); screenshot('android-live.png'); tap('Pause live')
    report['checks']['normal_launcher_and_actual_buttons'] = True
    device('shell','am','force-stop','com.atomverse.ai')
    result = device('shell','am','instrument','-w','com.atomverse.ai.test/com.atomverse.ai.AcceptanceRunner',timeout=150)
    (a.output/'instrumentation.txt').write_text(result)
    device('pull','/sdcard/Android/data/com.atomverse.ai/files/verification',a.output/'runtime')
    acceptance = json.loads((a.output/'runtime/acceptance.json').read_text())
    report['runtime'] = acceptance
    assert acceptance['status'] == 'PASS' and all(acceptance['checks'].values()), acceptance
    exported = import_events(a.output/'runtime/android-export.json')
    assert all(validate_event(e) == e for e in exported)
    memory = Memory(a.output/'desktop-roundtrip.sqlite3')
    memory.add(exported); export_events(a.output/'desktop-readback.json', recent(memory, 10000)); memory.close()
    assert {e['event_id']:e for e in import_events(a.output/'desktop-readback.json')} == {e['event_id']:e for e in exported}
    fixture = import_events(ROOT/'SOFTWARE/android/app/src/androidTest/assets/desktop-history.json')
    readback = {e['event_id']:e for e in import_events(a.output/'runtime/roundtrip-export.json')}
    assert all(readback[e['event_id']] == e for e in fixture)
    assert {classification(e) for e in fixture} == {'OBSERVED','DERIVED','AI_INTERPRETED','SIMULATED','UNAVAILABLE'}
    report['cross_platform'] = {'desktop_to_android_immutable_events':len(fixture),'android_to_desktop_validated_events':len(exported),'all_five_classes_preserved':True,'desktop_sqlite_and_export_equal':True}
    report['shared_source_sha256'] = {}
    for name in ['__init__.py','core.py','science.py','storage.py','mobile.py']:
        original = (ROOT/'SOFTWARE/atomverse'/name).read_bytes()
        generated = (ROOT/'SOFTWARE/android/app/build/shared-python/atomverse'/name).read_bytes()
        assert original == generated
        report['shared_source_sha256'][name] = hashlib.sha256(original).hexdigest()
    report['status'] = 'PASS'
finally:
    (a.output/'android-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'status':report['status'],'checks':report['checks'],'cross_platform':report.get('cross_platform')}))
