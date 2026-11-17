"""Extract the verified ZIP, launch away from the source tree, and close its own window."""
import ctypes as c
from ctypes import wintypes as w
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import time
import zipfile

root=Path(__file__).resolve().parents[1]
archive=root/'dist/ATOMVERSE-AI-0.2.0-alpha.1-win-x64.zip'
target=root/'.local/mission002/portable-smoke'
if target.exists(): raise RuntimeError('Portable smoke destination already exists; preserve prior evidence')
target.mkdir(parents=True)
with zipfile.ZipFile(archive) as z:
    for info in z.infolist():
        destination=(target/info.filename).resolve()
        if not destination.is_relative_to(target.resolve()): raise RuntimeError('Archive path escapes destination')
    z.extractall(target)
exe=target/'ATOMVERSE-AI/ATOMVERSE-AI.exe'
manifest=json.loads((root/'RELEASES/0.2.0-alpha.1/BUILD-MANIFEST.json').read_text())
assert hashlib.sha256(exe.read_bytes()).hexdigest()==manifest['executable_sha256']
process=subprocess.Popen([str(exe),'--data-dir',str(target/'data')],cwd=target,creationflags=subprocess.CREATE_NO_WINDOW)
user=c.WinDLL('user32',use_last_error=True)
callback_type=c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
user.EnumWindows.argtypes=[callback_type,w.LPARAM]
user.GetWindowThreadProcessId.argtypes=[w.HWND,c.POINTER(w.DWORD)]
user.IsWindowVisible.argtypes=[w.HWND]
user.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,c.c_int]
user.PostMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM]
windows=[]
@callback_type
def visit(handle, param):
    pid=w.DWORD();user.GetWindowThreadProcessId(handle,c.byref(pid))
    if pid.value==process.pid and user.IsWindowVisible(handle):
        title=c.create_unicode_buffer(256);user.GetWindowTextW(handle,title,256)
        if title.value.startswith('ATOMVERSE AI'): windows.append(handle)
    return True
started=time.monotonic()
try:
    while time.monotonic()-started<15 and not windows and process.poll() is None:
        user.EnumWindows(visit,0);time.sleep(.1)
    assert windows,'Extracted executable did not show its native application window'
    time.sleep(2)
    assert process.poll() is None
    user.PostMessageW(windows[0],0x0010,0,0)
    assert process.wait(timeout=8)==0
    with sqlite3.connect(target/'data/memory.sqlite3') as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert db.execute('SELECT count(*) FROM events').fetchone()[0]==0,'Demo data must not enter the observation database'
    report={'status':'PASS','extracted_zip_launch':True,'working_directory_outside_source':True,
            'native_window_visible':True,'closed_by_native_WM_CLOSE':True,'exit_code':0,'sqlite_integrity':'ok',
            'synthetic_demo_not_persisted_as_observation':True,'executable_sha256':manifest['executable_sha256'],'elapsed_s':time.monotonic()-started}
    (root/'EVIDENCE/MISSION-002-PORTABLE-VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
finally:
    if process.poll() is None:process.kill();process.wait(timeout=5)
