"""GUI-owned subprocess lifecycle and fixed wall-time policy."""
from pathlib import Path
import sys
from PySide6.QtCore import QObject, QProcess, QTimer, Signal
import json
from .core import ValidationError, make_event


class BenchmarkController(QObject):
    progress = Signal(dict)
    completed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.read)
        self.process.readyReadStandardError.connect(self.read_error)
        self.process.finished.connect(self.finish)
        self.process.errorOccurred.connect(self.process_error)
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.timeout.connect(self.expired)
        self.active = False
        self.buffer = b''
        self.stderr = b''

    def start(self, kind, seconds=1.0, size=32, python_path=''):
        if self.active:
            raise ValidationError('one benchmark at a time')
        if kind not in ('cpu', 'gpu') or not 0.1 <= seconds <= 3 or not (8 <= size <= 64 if kind == 'cpu' else 128 <= size <= 1024):
            raise ValidationError('benchmark configuration exceeds resource limits')
        worker = Path(__file__).with_name('worker.py')
        if kind == 'gpu':
            program = Path(python_path)
            if not program.is_file() or program.name.lower() not in ('python.exe', 'python3.exe', 'python', 'python3'):
                raise ValidationError('select an existing Python interpreter in Settings for GPU benchmarks')
            args = ['-I', str(worker), kind]
        elif getattr(sys, 'frozen', False):
            program, args = Path(sys.executable), ['--worker', kind]
        else:
            program, args = Path(sys.executable), [str(worker), kind]
        args += ['--seconds', str(seconds), '--size', str(size)]
        self.kind, self.config = kind, {'kind': kind, 'seconds': seconds, 'size': size}
        self.result, self.reason, self.buffer, self.stderr = None, None, b'', b''
        self.active = True
        self.process.setProgram(str(program))
        self.process.setArguments(args)
        self.process.start()
        self.timeout.start(30000)

    def read_error(self):
        self.stderr = (self.stderr + bytes(self.process.readAllStandardError()))[-4096:]

    def read(self):
        self.buffer += bytes(self.process.readAllStandardOutput())
        if len(self.buffer) > 65536:
            self.reason = 'FAIL: worker output exceeded 64 KiB'
            self.process.kill()
            return
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            try:
                data = json.loads(line)
                if data.get('type') == 'progress':
                    self.progress.emit(data)
                elif data.get('type') == 'result':
                    self.result = data
            except (ValueError, AttributeError):
                self.reason = 'FAIL: malformed benchmark output'

    def expired(self):
        self.reason = 'FAIL: benchmark exceeded 30-second wall limit'
        self.process.kill()

    def cancel(self):
        if self.active:
            self.reason = 'CANCELLED: benchmark stopped by operator'
            self.process.kill()
            self.process.waitForFinished(2000)

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.reason = 'FAIL: benchmark process could not start'
            self.finish(-1)

    def finish(self, code, *args):
        if not self.active:
            return
        self.read()
        self.read_error()
        self.active = False
        self.timeout.stop()
        data = self.result or {}
        if self.reason or not data or code != 0 and data.get('status') != 'FAIL':
            data = {'status': 'CANCELLED' if (self.reason or '').startswith('CANCELLED') else 'FAIL',
                    'message': self.reason or ('Worker ended without a verified result. ' + self.stderr.decode(errors='replace')[:500]), 'metrics': {}, 'configuration': self.config}
        try:
            event = make_event('benchmark-worker', 'benchmark', self.kind, data.get('metrics', {}),
                               status=data.get('status', 'FAIL'), message=data.get('message', '')[:1800],
                               configuration=data.get('configuration', self.config), provenance={'worker': 'atomverse-matrix/1'})
        except Exception as exc:
            event = make_event('benchmark-worker', 'benchmark', self.kind, status='FAIL', message=f'Invalid worker result: {exc}', configuration=self.config)
        self.completed.emit(event)
