"""Application and packaged worker entry point."""
import sys

if '--worker' in sys.argv:
    # The windowed Windows bootloader sets stdout=None. QProcess provides a real pipe.
    if sys.stdout is None and sys.platform == 'win32':
        import ctypes
        import msvcrt
        import os
        from ctypes import wintypes
        ctypes.windll.kernel32.GetStdHandle.restype = wintypes.HANDLE
        handle = ctypes.windll.kernel32.GetStdHandle(-11)
        sys.stdout = os.fdopen(msvcrt.open_osfhandle(handle, os.O_WRONLY), 'w', buffering=1)
    from atomverse.worker import main
    raise SystemExit(main(sys.argv[sys.argv.index('--worker') + 1:]))

import argparse
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from atomverse.app import Window

parser = argparse.ArgumentParser(description='ATOMVERSE AI experimental native desktop')
parser.add_argument('--data-dir', type=Path, default=Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'ATOMVERSE-AI')
parser.add_argument('--gpu-python', default='')
parser.add_argument('--import-arx', type=Path)
parser.add_argument('--verify', type=Path, help='run bounded interaction verification against this actual application')
args = parser.parse_args()
app = QApplication(sys.argv[:1])
app.setApplicationName('ATOMVERSE AI')
window = Window(args.data_dir, args.gpu_python)
window.show()
if args.verify:
    from atomverse.verification import verify_gui
    verify_gui(app, window, args.verify, args.import_arx)
elif args.import_arx:
    window.import_path(args.import_arx)
raise SystemExit(app.exec())
