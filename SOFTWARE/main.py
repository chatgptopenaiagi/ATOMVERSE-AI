"""Application and packaged worker entry point."""
import sys

if '--verification-load' in sys.argv:
    # A bounded, explicitly invoked acceptance workload; never started during normal use.
    import time
    until = time.monotonic() + 12
    value = 1
    while time.monotonic() < until:
        for _ in range(10000):
            value = (value * 1664525 + 1013904223) & 0xffffffff
    raise SystemExit(0)

worker_flag = next((flag for flag in ('--worker', '--observer-worker', '--ai-worker') if flag in sys.argv), None)
if worker_flag:
    # The windowed Windows bootloader sets stdout=None. QProcess provides a real pipe.
    if sys.stdout is None and sys.platform == 'win32':
        import ctypes
        import msvcrt
        import os
        from ctypes import wintypes
        ctypes.windll.kernel32.GetStdHandle.restype = wintypes.HANDLE
        handle = ctypes.windll.kernel32.GetStdHandle(-11)
        sys.stdout = os.fdopen(msvcrt.open_osfhandle(handle, os.O_WRONLY), 'w', buffering=1)
        if sys.stdin is None and worker_flag != '--worker':
            handle = ctypes.windll.kernel32.GetStdHandle(-10)
            sys.stdin = os.fdopen(msvcrt.open_osfhandle(handle, os.O_RDONLY), 'r')
    if worker_flag == '--observer-worker':
        from atomverse.observer_worker import main
    elif worker_flag == '--ai-worker':
        from atomverse.intelligence import main
    else:
        from atomverse.worker import main
    raise SystemExit(main(sys.argv[sys.argv.index(worker_flag) + 1:]))

import argparse
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from atomverse.living import LivingWindow as Window

parser = argparse.ArgumentParser(description='ATOMVERSE AI experimental native desktop')
parser.add_argument('--data-dir', type=Path, default=Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'ATOMVERSE-AI')
parser.add_argument('--gpu-python', default='')
parser.add_argument('--import-arx', type=Path)
parser.add_argument('--verify', type=Path, help='run bounded interaction verification against this actual application')
parser.add_argument('--verify-mission002', type=Path, help='run live observer and packaged acceptance checks')
parser.add_argument('--verify-ai', type=Path, help='verify optional local AI with a selected measured CPU event')
parser.add_argument('--ai-endpoint', default='http://127.0.0.1:11434')
args = parser.parse_args()
app = QApplication(sys.argv[:1])
app.setApplicationName('ATOMVERSE AI')
if args.verify:
    from atomverse.app import Window  # Explicit Mission 001 compatibility harness.
window = Window(args.data_dir, args.gpu_python)
window.show()
if args.verify_ai:
    from atomverse.verification002 import verify_ai
    verify_ai(app, window, args.verify_ai, args.ai_endpoint)
elif args.verify_mission002:
    from atomverse.verification002 import verify
    verify(app, window, args.verify_mission002, args.import_arx)
elif args.verify:
    from atomverse.verification import verify_gui
    verify_gui(app, window, args.verify, args.import_arx)
elif args.import_arx:
    window.import_path(args.import_arx)
raise SystemExit(app.exec())
