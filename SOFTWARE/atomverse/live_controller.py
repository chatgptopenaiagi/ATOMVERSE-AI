"""Qt bridge with bounded IPC and an owned observer lifecycle."""
from collections import deque
import json
import os
from pathlib import Path
import sys
import time
from PySide6.QtCore import QObject, QProcess, QTimer, Signal
from .core import validate_event


def command(flag):
    if getattr(sys, 'frozen', False):
        return sys.executable, [flag]
    return sys.executable, [str(Path(__file__).parents[1] / 'main.py'), flag]


class LiveController(QObject):
    failed = Signal(str)
    stopped = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.read)
        self.process.readyReadStandardError.connect(self.drain_error)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(lambda error: self.failed.emit('Observer process: ' + self.process.errorString()) if error == QProcess.ProcessError.FailedToStart else None)
        self.queue = deque(maxlen=4)
        self.buffer = bytearray(); self.dropped = 0; self.last_packet = 0
        self.latest = None; self.samples = 0; self.pid = None; self.error = ''
        self.watch = QTimer(self); self.watch.setInterval(1000); self.watch.timeout.connect(self.check_watchdog)

    @property
    def active(self):
        return self.process.state() != QProcess.ProcessState.NotRunning

    def start(self, database, config, samples=0):
        if self.active:
            return
        self.config = config; config.validate()
        self.queue.clear(); self.buffer.clear(); self.samples = 0; self.error = ''
        self.last_packet = time.monotonic()
        program, args = command('--observer-worker')
        self.process.start(program, args + ['--database', str(database), '--config', json.dumps(config.validate()), '--gui-pid', str(os.getpid()), '--samples', str(samples)])
        self.watch.start()

    def drain_error(self):
        # Do not allow the stderr pipe to accumulate indefinitely.
        data = bytes(self.process.readAllStandardError())[-2000:]
        if data:
            self.error = data.decode(errors='replace')

    def read(self):
        self.pid = int(self.process.processId()) or self.pid
        self.buffer.extend(bytes(self.process.readAllStandardOutput()))
        if len(self.buffer) > 4 * 1024 * 1024:
            self.failed.emit('Observer IPC buffer limit exceeded'); self.stop(); return
        while b'\n' in self.buffer:
            line, _, remainder = self.buffer.partition(b'\n'); self.buffer = bytearray(remainder)
            try:
                packet = json.loads(line)
                self.last_packet = time.monotonic()
                if packet['type'] == 'sample':
                    if not packet.get('committed') or not isinstance(packet['events'], list) or len(packet['events']) > 400:
                        raise ValueError('invalid observer batch')
                    packet['events'] = [validate_event(e) for e in packet['events']]
                    self.samples += 1; self.latest = packet
                    if len(self.queue) == self.queue.maxlen:
                        self.dropped += 1
                    self.queue.append(packet)
                elif packet['type'] == 'error':
                    self.error = packet['message']; self.failed.emit(self.error)
            except (KeyError, ValueError, TypeError) as exc:
                self.error = 'Malformed observer output: ' + str(exc)
                self.failed.emit(self.error); self.stop(); return

    def check_watchdog(self):
        if self.active and time.monotonic() - self.last_packet > max(15, self.config.interval_s * 3):
            self.failed.emit('Observer exceeded its response deadline'); self.stop()

    def stop(self):
        self.watch.stop()
        if self.active:
            self.process.write(b'stop\n'); self.process.closeWriteChannel()
            if not self.process.waitForFinished(1200):
                self.process.kill(); self.process.waitForFinished(1200)

    def finished(self, code, status):
        self.watch.stop()
        if code and not self.error:
            self.failed.emit(f'Observer exited with code {code}')
        self.stopped.emit()
