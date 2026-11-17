"""Installed console entry point and frozen worker dispatch."""
import sys

_qt_icu_handle = None


def prepare_qt_runtime():
    """PyPI Qt 6.11 links Windows ICU; a Conda DLL search path may shadow it.

    Pin the OS library in this process for the PyPI layout only. Conda Qt and
    frozen distributions retain their own matched libraries. No PATH changes.
    """
    if sys.platform != 'win32' or getattr(sys, 'frozen', False):
        return
    import ctypes
    import importlib.util
    from pathlib import Path
    spec = importlib.util.find_spec('PySide6')
    if spec and spec.origin:
        directory = Path(spec.origin).parent
        if (directory/'QtCore.pyd').is_file() and (directory/'Qt6Core.dll').is_file():
            system = ctypes.create_unicode_buffer(32768)
            if not ctypes.windll.kernel32.GetSystemDirectoryW(system, len(system)):
                raise OSError('Cannot locate the Windows system library directory')
            global _qt_icu_handle
            _qt_icu_handle = ctypes.WinDLL(str(Path(system.value)/'icuuc.dll'))


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    if '--verification-load' in arguments:
        import time
        until = time.monotonic() + 12
        value = 1
        while time.monotonic() < until:
            for _ in range(10000):
                value = (value * 1664525 + 1013904223) & 0xffffffff
        return 0
    flag = next((f for f in ('--worker', '--observer-worker', '--ai-worker') if f in arguments), None)
    if flag:
        if sys.stdout is None and sys.platform == 'win32':
            import ctypes
            import msvcrt
            import os
            from ctypes import wintypes
            ctypes.windll.kernel32.GetStdHandle.restype = wintypes.HANDLE
            handle = ctypes.windll.kernel32.GetStdHandle(-11)
            sys.stdout = os.fdopen(msvcrt.open_osfhandle(handle, os.O_WRONLY), 'w', buffering=1)
            if sys.stdin is None and flag != '--worker':
                handle = ctypes.windll.kernel32.GetStdHandle(-10)
                sys.stdin = os.fdopen(msvcrt.open_osfhandle(handle, os.O_RDONLY), 'r')
        if flag == '--observer-worker':
            from .observer_worker import main as run
        elif flag == '--ai-worker':
            from .intelligence import main as run
        else:
            from .worker import main as run
        return run(arguments[arguments.index(flag) + 1:])
    import argparse
    import os
    from pathlib import Path
    from . import __version__
    parser = argparse.ArgumentParser(description='ATOMVERSE AI native Windows desktop; shared Python event core')
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--export-licenses', type=Path, help='Copy bundled third-party license texts to a new directory, then exit')
    parser.add_argument('--data-dir', type=Path, default=Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'ATOMVERSE-AI')
    parser.add_argument('--gpu-python', default='')
    parser.add_argument('--import-arx', type=Path)
    parser.add_argument('--verify', type=Path)
    parser.add_argument('--verify-mission002', type=Path)
    parser.add_argument('--verify-ai', type=Path)
    parser.add_argument('--ai-endpoint', default='http://127.0.0.1:11434')
    args = parser.parse_args(arguments)
    if args.export_licenses:
        import shutil
        candidates = [Path(getattr(sys, '_MEIPASS', '')) / 'LICENSES',
                      Path(__file__).resolve().parents[2] / 'LICENSES',
                      Path(sys.prefix) / 'share' / 'atomverse-ai' / 'LICENSES']
        source = next((p for p in candidates if p.is_dir()), None)
        if source is None:
            parser.error('Bundled license directory missing')
        shutil.copytree(source, args.export_licenses)
        return 0
    if sys.platform != 'win32':
        parser.error('This desktop entry point is supported on Windows. The pure event/science/storage modules can be used independently; Android uses the packaged native client.')
    prepare_qt_runtime()
    from PySide6.QtWidgets import QApplication
    from .living import LivingWindow as Window
    app = QApplication(sys.argv[:1]); app.setApplicationName('ATOMVERSE AI')
    if args.verify:
        from .app import Window
    window = Window(args.data_dir, args.gpu_python); window.show()
    if args.verify_ai:
        from .verification002 import verify_ai
        verify_ai(app, window, args.verify_ai, args.ai_endpoint)
    elif args.verify_mission002:
        from .verification002 import verify
        verify(app, window, args.verify_mission002, args.import_arx)
    elif args.verify:
        from .verification import verify_gui
        verify_gui(app, window, args.verify, args.import_arx)
    elif args.import_arx:
        window.import_path(args.import_arx)
    return app.exec()
