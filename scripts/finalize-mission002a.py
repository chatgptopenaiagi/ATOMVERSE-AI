"""Assemble reviewed package evidence; remote publication is recorded separately."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT/'VERSION').read_text().strip()
assert VERSION == '0.2.0-alpha.2'
local = ROOT/'.local/mission002a'
release = ROOT/'dist/releases'/VERSION
def read(path): return json.loads(Path(path).read_text())
def save(path, value): Path(path).write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
windows = read(local/'windows-promoted-gui/gui-verification.json')
wheel = read(local/'wheel-final/wheel-verification.json')
android = read(local/'android-final/android-verification.json')
tests = read(ROOT/'EVIDENCE/MISSION-002A-TEST-RESULTS.json')
assert all(r['status'] == 'PASS' for r in (windows, wheel, android, tests))
assert tests['total_tests'] == 85 and tests['baseline_tests'] == 79
assert android['document_picker']['export_readback_events'] == 159
assert wheel['installed_probe']['android_history_records_exchanged'] == 149
packages = []
for name, expected, platform in [
    (f'ATOMVERSE-AI-{VERSION}-windows-x64.exe', windows['external_verification']['executable_sha256'], 'Windows 11 x64; self-contained runtime'),
    ('atomverse_ai-0.2.0a2-py3-none-any.whl', wheel['wheel_sha256'], 'Pure Python payload; desktop supported on Windows; runtime dependencies required'),
    (f'ATOMVERSE-AI-{VERSION}-android-arm64.apk', android['apk_sha256'], 'Android ARM64; min API 24, target API 36; tested API 37 translated emulator')]:
    path = release/name
    assert sha(path) == expected
    packages.append({'name':name, 'bytes':path.stat().st_size, 'sha256':expected, 'platform':platform})
manifest = release/f'ATOMVERSE-AI-{VERSION}-SHA256SUMS.txt'
manifest.write_text(''.join(f"{p['sha256']}  {p['name']}\n" for p in packages), encoding='utf-8')
old_name = 'ATOMVERSE-AI-0.2.0-alpha.1-win-x64.zip'
old_sha = '4db1f2cec468e4adef3252ff71b9cba0ad5caa9a2ddf49c4d7d33c0a026767d2'
old = list((ROOT/'dist').rglob(old_name)); assert old and all(sha(p)==old_sha for p in old)
assert sha(ROOT/'dist/releases/0.2.0-alpha.1/ATOMVERSE-AI/ATOMVERSE-AI.exe') == '109994f3c3057f6cf620d7b0b823617c6ae52c9101279aa7b9cf884c08aa32d6'
for name in ('core.py','science.py','storage.py'):
    assert not subprocess.check_output(['git','diff','e8c8ce0','--','SOFTWARE/atomverse/'+name],cwd=ROOT)
    assert wheel['shared_source_sha256'][name] == android['shared_source_sha256'][name]
assert not subprocess.check_output(['git','diff','e8c8ce0','--','CONCEPT/ORIGINAL-HUMAN-VISION.md','ATOMVERSE-EVENT-SCHEMA.json'],cwd=ROOT)
save(ROOT/'EVIDENCE/MISSION-002A-WINDOWS-VERIFICATION.json', windows)
shutil.copyfile(local/'windows-promoted-gui/recorded-universe.png',ROOT/'EVIDENCE/MISSION-002A-WINDOWS.png')
save(ROOT/'EVIDENCE/MISSION-002A-PERFORMANCE.json', {'windows_exe':windows['performance'], 'installed_wheel':wheel['gui']['performance'],
    'android':{'frames':android['runtime']['frames'],'last_paint_ms':android['runtime']['last_paint_ms'], 'note':'Single measured final frame, not a latency distribution or physical-phone benchmark; 256-object / 10–30 fps rendering caps.'}})
save(ROOT/'EVIDENCE/MISSION-002A-CROSS-PLATFORM.json', {**android['cross_platform'], 'android_system_document_picker':android['document_picker'],
    'installed_wheel_android_records_exchanged':wheel['installed_probe']['android_history_records_exchanged'], 'shared_source_sha256':wheel['shared_source_sha256']})
save(ROOT/'EVIDENCE/MISSION-002A-RESOLVED-ISSUES.json', {'issues':[
    {'finding':'First EXE candidate exceeded the 700 ms p95 sampling limit during concurrent Android compilation (738.3 ms).','resolution':'Kept the threshold, preserved failed evidence and verified the final executable with the owned emulator stopped.','status':'RESOLVED'},
    {'finding':'Android Activity recreation overlapped first SQLite initialization; ready could precede the first packet.','resolution':'Serialized Mobile construction and set readiness after packet generation; concurrent initialization test and signed-APK execution pass.','status':'RESOLVED'},
    {'finding':'Fresh PyPI Qt under Anaconda loaded an incompatible ICU DLL.','resolution':'PE imports/exports identified the collision; the installed entry point loads Windows ICU by absolute path for the PyPI layout only. Existing environments and global PATH were not modified.','status':'RESOLVED'},
    {'finding':'Cross-platform verification initially omitted OBSERVED fixtures and used an observed-only readback on mixed history.','resolution':'Included a genuine ARX observation and compared all retained classes. Nine desktop events and 149 Android events retain their exact event bodies.','status':'TEST HARNESS CORRECTED'},
    {'finding':'An early system-picker download occurred before asynchronous export completed.','resolution':'Read back the completed 159-event file; Android imported it through the actual system picker.','status':'VERIFIED AFTER COMPLETION'},
    {'finding':'The API 37 emulator showed System UI ANRs during boot before ATOMVERSE launch.','resolution':'Allocated four virtual cores / 4 GiB in the owned AVD, stabilized System UI and then executed the signed ARM64 APK. Physical-device coverage remains unavailable.','status':'ENVIRONMENT LIMITATION RECORDED'}]})
build = {'mission':'002A','version':VERSION,'recorded_at_utc':datetime.now(timezone.utc).isoformat(), 'packages':packages,
    'tools':{'pyinstaller':'6.22.3','desktop_python':'3.14.9','pyside6':'6.11.0','psutil':'7.2.2','android_gradle_plugin':'9.1.0','gradle':'9.3.1','jdk':'21.0.8','chaquopy':'17.2.0','android_python':'3.14.8','android_build_tools':'36.0.0'},
    'android_signing_certificate_sha256':'ed2378c073ae98fafa92731de472b1d9e96d8d1e82af21ca1fc43ab9b0b899c8',
    'shared_build_input_sha256':android['shared_source_sha256'], 'original_zip_sha256':old_sha,
    'version_decision':'New Android functionality and installed desktop entry point require the incremented prerelease. Original 0.2.0-alpha.1 assets are immutable.'}
save(ROOT/'EVIDENCE/MISSION-002A-BUILD.json', build)
final = {'mission':'002A','version':VERSION,'status':'LOCAL_ACCEPTANCE_PASS','publication':{'status':'PENDING'},'packages':packages,
    'acceptance':{'original_human_vision_preserved':True,'original_zip_bytes_preserved':True,'original_event_contract_and_core_preserved':True,
    'windows_exe':'PASS','python_wheel':'PASS','android_arm64_apk':'PASS_ON_TRANSLATED_EMULATOR','cross_platform_history':'PASS_ALL_FIVE_CLASSES',
    'python_tests_passed':85,'original_tests_retained':79,'android_runtime_checks_passed':len(android['runtime']['checks']),
    'physical_android_device':'NOT_EXECUTED_NO_DEVICE_AVAILABLE','other_android_api_versions':'NOT_EXECUTED','linux_macos_desktop':'NOT_SUPPORTED_OR_CLAIMED'},
    'preservation':{'original_release':'v0.2.0-alpha.1','zip_sha256':old_sha,'credentials_changed':False,'unrelated_source_or_runtime_installations_modified':False,
                    'owned_emulator':'emulator-5580 stopped; unrelated emulator processes left untouched'}}
save(ROOT/'EVIDENCE/MISSION-002A-FINAL-VERIFICATION.json',final)
table='\n'.join(f"| `{p['name']}` | {p['bytes']:,} | `{p['sha256']}` |" for p in packages)
(ROOT/'ATOMVERSE-FINAL-REPORT.md').write_text(f'''# Mission 002A — Multiplatform Expansion

**Version: {VERSION}. Local package acceptance: PASS.** Publication readback is recorded in [final verification](EVIDENCE/MISSION-002A-FINAL-VERIFICATION.json). This is an experimental prerelease, not a finished intelligence platform.

Android adds application functionality, so this mission uses the explicitly authorized version increment. The original v0.2.0-alpha.1 ZIP, executable, checksum asset, tag and evidence remain intact. Its portable ZIP SHA-256 is `{old_sha}`. Mission 002 documents are archived in RELEASES/0.2.0-alpha.1; the original human vision is unchanged.

| Package | Bytes | SHA-256 |
|---|---:|---|
{table}

Windows EXE acceptance ran the actual promoted one-file executable from a working directory outside the source tree. It verified native GUI interaction, live CPU/RAM/NVIDIA/process observations, real ARX import, CPU and CUDA benchmarks, SQLite integrity, replay, JSON readback, optional-AI unavailable handling and clean worker shutdown. Python/model/CUDA toolkits are not required or silently bundled beyond the included desktop Python runtime. The EXE is not Authenticode signed.

The wheel installed in a fresh environment without system site packages. Metadata, pure-Python tags, import, console/module entry points, license export, real GUI observation and benchmarks, SQLite/export readback, Android-history import and uninstallation passed. The tested Python was Anaconda 3.14.9 on Windows 11 x64. Python 3.15 is allowed by metadata but did not receive a separate wheel GUI run. The `py3-none-any` tag describes package contents, not universal desktop support.

The release-signed ARM64 APK passed {len(android['runtime']['checks'])} actual runtime checks and package/signature checks on an API 37 x86_64 emulator using Android's `libndk_translation` ARM64 bridge. The same ARM64 APK intended for publication was installed, launched and operated; no x86 application binary substituted for it. Rotation, pinch zoom, live Android RAM/app CPU, unavailable GPU states, SQLite, document export, history import/replay, malformed-input rejection and clean worker shutdown passed. The normal system picker also exported and reimported a validated 159-event history. No physical ARM64 device was attached. Other Android API levels and vendor devices remain untested.

All **85 Python tests** pass, retaining all **79 original tests**. Cross-platform verification preserved nine desktop events byte-semantically on Android and 149 Android events through desktop and installed-wheel SQLite/export. OBSERVED, DERIVED, AI_INTERPRETED, SIMULATED and UNAVAILABLE classifications survived the exchange. The original core, science, storage algorithms and published JSON contract remain unchanged; platform adaptation lives in `mobile.py`.

Measured Windows overhead, sampling delay and GUI latency are in [performance evidence](EVIDENCE/MISSION-002A-PERFORMANCE.json). Android's recorded final-frame paint time is a single sample, not a physical-device performance benchmark. Initial failures and fixes—including concurrent migration, a PyPI Qt/Conda ICU collision and concurrent-build latency—are preserved in [resolved issues](EVIDENCE/MISSION-002A-RESOLVED-ISSUES.json).

Android exposes app CPU, device RAM, app PSS and storage capacity. It does not claim Windows process relationships, NVIDIA CUDA, device-wide CPU utilization, GPU workload sensors or an embedded Qwen model. Its normal operation is offline; AI-interpreted history remains readable. Rendering and history views are bounded to 256 objects/events, and exports stream rows. Physical-device coverage, additional Android versions, mobile CSV export and optional authorized AI endpoints are next priorities.

See [installation and platform matrix](INSTALLATION.md), [architecture](ATOMVERSE-ARCHITECTURE.md), [Android build instructions](SOFTWARE/android/README.md), and [source/build instructions](SOFTWARE/README.md). Verified packages are promoted under `dist/releases/{VERSION}`; future candidate builds use a separate directory. No old release asset is overwritten.
''',encoding='utf-8')
print(json.dumps({'status':'LOCAL_ACCEPTANCE_PASS','packages':packages}))
