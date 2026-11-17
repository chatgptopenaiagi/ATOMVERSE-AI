"""Native desktop shell. Every data particle resolves to inspectable evidence."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow, QPlainTextEdit,
    QProgressBar, QPushButton, QSlider, QSpinBox, QSplitter, QStackedWidget,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget)

from . import __version__
from .adapters import import_events
from .benchmark import BenchmarkController
from .core import Memory, Replay, ValidationError, atomic_write, demo_events, export_events, make_event, metric
from .scene import Universe
from .sources import sample_hardware, inspect_repository, discover_python, explain_local

STYLE = '''
QMainWindow, QWidget { background:#0b1220; color:#dce6f5; font-family:"Segoe UI"; font-size:13px; }
QLabel#brand { color:#c5efff; font-size:22px; font-weight:700; }
QLabel#title { font-size:26px; font-weight:600; }
QLabel#sub { color:#8a9db5; }
QLabel#mode { color:#76ddbf; background:#16352f; padding:8px 14px; border-radius:6px; font-weight:600; }
QFrame#sidebar { background:#0e192a; border-right:1px solid #203149; }
QListWidget { background:#0e192a; border:0; outline:0; }
QListWidget::item { padding:12px 8px; border-radius:5px; margin:2px 0; color:#9cb0ca; }
QListWidget::item:selected { background:#1c354b; color:#b1efff; border-left:3px solid #6cd5f3; }
QPushButton { background:#1c3047; border:1px solid #2b4560; border-radius:5px; padding:8px 12px; }
QPushButton:hover { background:#28465e; border-color:#65baff; }
QPushButton:disabled { color:#5d7087; background:#141f30; }
QPushButton#primary { background:#69d9eb; color:#071925; border:0; font-weight:600; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background:#101e30; border:1px solid #29415a; border-radius:4px; padding:7px; }
QPlainTextEdit, QTextEdit, QTableWidget { background:#0e1929; border:1px solid #20334a; border-radius:6px; selection-background-color:#284c68; }
QTableWidget { gridline-color:#203149; alternate-background-color:#111f31; }
QHeaderView::section { background:#192a40; color:#a8bdd6; padding:9px; border:0; border-bottom:1px solid #2e4965; }
QProgressBar { background:#14253a; border:0; border-radius:4px; height:13px; text-align:center; }
QProgressBar::chunk { background:#64cde4; border-radius:4px; }
QSlider::groove:horizontal { height:5px; background:#243952; }
QSlider::handle:horizontal { background:#6cd5f3; width:13px; margin:-5px 0; border-radius:6px; }
QScrollBar:vertical { background:#0e1929; width:10px; }
QScrollBar::handle:vertical { background:#30465e; border-radius:4px; min-height:25px; }
QStatusBar { color:#91a6bf; background:#0b1220; }
'''


def label(text, name=None):
    w = QLabel(text)
    if name:
        w.setObjectName(name)
    w.setWordWrap(True)
    return w


def button(text, fn, primary=False):
    w = QPushButton(text)
    if primary:
        w.setObjectName('primary')
    w.clicked.connect(fn)
    return w


class Window(QMainWindow):
    def __init__(self, data_dir, gpu_python=''):
        super().__init__()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.memory = Memory(self.data_dir / 'memory.sqlite3')
        self.settings_path = self.data_dir / 'settings.json'
        try:
            settings = json.loads(self.settings_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            settings = {}
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='atomverse-input')
        self.pending = None
        self.observed = self.memory.events()
        self.synthetic = demo_events()
        self.displayed = []
        self.replay = Replay(self.observed)
        self.last_error = ''
        self.last_result = None
        self.closing = False
        self.setWindowTitle(f'ATOMVERSE AI · {__version__}')
        self.resize(1440, 920)
        self.setMinimumSize(1180, 760)
        self.setStyleSheet(STYLE)
        self.bench = BenchmarkController(self)
        self.bench.completed.connect(self.benchmark_finished)
        self.bench.progress.connect(self.benchmark_progress)
        root = QWidget(); self.setCentralWidget(root)
        outer = QHBoxLayout(root); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)
        side = QFrame(); side.setObjectName('sidebar'); side.setFixedWidth(190)
        sl = QVBoxLayout(side); sl.setContentsMargins(17, 25, 12, 18)
        brand = label('ATOMVERSE', 'brand'); brand.setWordWrap(False); sl.addWidget(brand)
        sl.addWidget(label('COMPUTATIONAL UNIVERSE', 'sub'))
        sl.addSpacing(22)
        self.nav = QListWidget()
        self.names = ['Universe', 'Benchmark Arena', 'Data Tables', 'AI Intelligence', 'Knowledge Memory', 'Hardware Map', 'Software Map', 'Source Code Galaxy', 'Guardian', 'Settings']
        self.nav.addItems(self.names); sl.addWidget(self.nav)
        sl.addWidget(label('GENESIS\n0.1.0-alpha.1\nLocal · experimental', 'sub'))
        outer.addWidget(side)
        main = QVBoxLayout(); main.setContentsMargins(24, 20, 24, 12); main.setSpacing(13); outer.addLayout(main)
        top = QHBoxLayout()
        titles = QVBoxLayout(); self.title = label('Your computational universe', 'title'); titles.addWidget(self.title)
        titles.addWidget(label('Information becomes motion. Measurements remain inspectable.', 'sub'))
        top.addLayout(titles, 1); self.mode_badge = label('', 'mode'); self.mode_badge.setWordWrap(False); top.addWidget(self.mode_badge); main.addLayout(top)
        controls = QHBoxLayout()
        self.mode = QComboBox(); self.mode.addItems(['Demo', 'Live / recorded data', 'Replay'])
        self.mode.currentIndexChanged.connect(self.change_mode)
        controls.addWidget(self.mode)
        self.import_button = button('Import ARX / JSON', self.choose_import, True); controls.addWidget(self.import_button)
        self.sample_button = button('Sample hardware', self.sample); controls.addWidget(self.sample_button)
        self.live_button = button('Start live telemetry', self.toggle_live); controls.addWidget(self.live_button)
        controls.addStretch(); controls.addWidget(button('Export view', self.choose_export)); main.addLayout(controls)
        self.stats = label('', 'sub'); main.addWidget(self.stats)
        self.pages = QStackedWidget(); main.addWidget(self.pages, 1)
        self.make_universe()
        self.make_arena()
        self.make_table()
        self.make_ai(settings)
        self.make_history()
        self.hardware = self.make_text_page('Hardware observations', 'Import an ARX report or sample hardware. Static inventory is not live load.')
        self.software = self.make_text_page('Software observations', 'ARX tool versions are snapshots of the source report. No installations are modified.')
        self.make_code()
        self.guardian = self.make_text_page('Verified diagnostics', 'Failures and skipped operations from observed records appear here.')
        self.make_settings(settings, gpu_python)
        self.nav.currentRowChanged.connect(self.navigate); self.nav.setCurrentRow(0)
        self.status = self.statusBar(); self.status.showMessage('Choose a source to begin. Demo values are synthetic.')
        self.poll = QTimer(self); self.poll.setInterval(100); self.poll.timeout.connect(self.poll_task); self.poll.start()
        self.live_timer = QTimer(self); self.live_timer.setInterval(2000); self.live_timer.timeout.connect(self.sample)
        self.replay_timer = QTimer(self); self.replay_timer.setInterval(400); self.replay_timer.timeout.connect(self.step_replay)
        self.mode.setCurrentIndex(1 if self.observed else 0)
        self.change_mode()

    def make_universe(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        field_label = label('WORKSTATION  /  EVENT FIELD', 'sub'); field_label.setWordWrap(False); bar.addWidget(field_label); bar.addStretch()
        self.pause_button = button('Pause motion', self.pause_scene); bar.addWidget(self.pause_button)
        bar.addWidget(button('Reset camera', self.reset_camera)); layout.addLayout(bar)
        split = QSplitter(); self.scene = Universe(); split.addWidget(self.scene)
        detail = QWidget(); dl = QVBoxLayout(detail); dl.setContentsMargins(14, 0, 0, 0)
        dl.addWidget(label('EVENT INSPECTOR', 'sub'))
        self.inspector = QPlainTextEdit(); self.inspector.setReadOnly(True)
        self.inspector.setPlaceholderText('Select a particle or table row.\n\nRaw metrics, units, provenance, and the dimensionless visual score appear here.')
        self.inspector.setFont(QFont('Cascadia Mono', 9)); dl.addWidget(self.inspector)
        dl.addWidget(label('Blue · information\nGold · verified benchmark\nGreen · successful execution\nRed · recorded failure\nGrey · skipped / cancelled', 'sub'))
        split.addWidget(detail); split.setSizes([810, 290]); layout.addWidget(split, 1)
        self.scene.selected.connect(self.inspect); self.pages.addWidget(page)

    def make_arena(self):
        page = QWidget(); layout = QVBoxLayout(page)
        layout.addWidget(label('Run a measured experiment', 'title'))
        layout.addWidget(label('One worker at a time. Matrix output is checked numerically. Duration is bounded; GPU work reserves 1536 MiB of free VRAM.', 'sub'))
        form = QFormLayout()
        self.duration = QDoubleSpinBox(); self.duration.setRange(0.1, 3); self.duration.setValue(1); self.duration.setSuffix(' seconds')
        self.cpu_size = QSpinBox(); self.cpu_size.setRange(8, 64); self.cpu_size.setValue(32)
        self.gpu_size = QSpinBox(); self.gpu_size.setRange(128, 1024); self.gpu_size.setValue(512)
        form.addRow('Measured kernel duration', self.duration); form.addRow('CPU matrix dimension', self.cpu_size); form.addRow('GPU matrix dimension', self.gpu_size); layout.addLayout(form)
        row = QHBoxLayout(); self.cpu_button = button('Run CPU matrix', lambda: self.start_benchmark('cpu'), True); self.gpu_button = button('Run GPU matrix', lambda: self.start_benchmark('gpu'))
        row.addWidget(self.cpu_button); row.addWidget(self.gpu_button); self.cancel_button = button('Stop benchmark', self.bench.cancel); self.cancel_button.setEnabled(False); row.addWidget(self.cancel_button); row.addStretch(); layout.addLayout(row)
        self.progress = QProgressBar(); self.progress.setRange(0, 100); layout.addWidget(self.progress)
        self.bench_status = label('Ready. CPU uses a portable matrix kernel. GPU uses your selected PyTorch interpreter.', 'sub'); layout.addWidget(self.bench_status)
        self.bench_result = QPlainTextEdit(); self.bench_result.setReadOnly(True); layout.addWidget(self.bench_result, 1)
        self.pages.addWidget(page)

    def make_table(self):
        page = QWidget(); layout = QVBoxLayout(page)
        row = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText('Search event, source, metric, status…'); self.search.textChanged.connect(self.populate_table); row.addWidget(self.search)
        self.filter_status = QComboBox(); self.filter_status.addItems(['All outcomes', 'PASS', 'FAIL', 'INFO', 'SKIP', 'CANCELLED']); self.filter_status.currentIndexChanged.connect(self.populate_table); row.addWidget(self.filter_status)
        self.since = QLineEdit(); self.since.setPlaceholderText('From UTC: YYYY-MM-DD'); self.since.textChanged.connect(self.populate_table); row.addWidget(self.since)
        layout.addLayout(row)
        self.table = QTableWidget(0, 7); self.table.setHorizontalHeaderLabels(['Time (UTC)', 'Source', 'Orbit', 'Operation', 'Status', 'Measurements', 'Event ID'])
        self.table.setAlternatingRowColors(True); self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); self.table.setSortingEnabled(True)
        self.table.itemSelectionChanged.connect(self.select_table)
        self.table.horizontalHeader().setStretchLastSection(True); layout.addWidget(self.table)
        layout.addWidget(label('The universe and export use the current mode. Table search filters visible rows. Numeric units are preserved.', 'sub'))
        self.pages.addWidget(page)

    def make_ai(self, settings):
        page = QWidget(); layout = QVBoxLayout(page)
        layout.addWidget(label('Ask about the evidence', 'title'))
        layout.addWidget(label('Optional local model. Sends the latest 12 observed events only when you click Explain. Responses are interpretations, never measurements or executed actions.', 'sub'))
        self.endpoint = QLineEdit(settings.get('endpoint', 'http://127.0.0.1:8080/v1'))
        self.model_name = QLineEdit(settings.get('model', 'Qwen3-Coder-30B-A3B-Instruct'))
        form = QFormLayout(); form.addRow('Local model endpoint', self.endpoint); form.addRow('Model served by endpoint', self.model_name); layout.addLayout(form)
        self.question = QLineEdit(); self.question.setMaxLength(4000); self.question.setPlaceholderText('Why did the latest benchmark fail?'); layout.addWidget(self.question)
        layout.addWidget(button('Explain latest observed evidence', self.ask_ai))
        self.ai_answer = QPlainTextEdit(); self.ai_answer.setReadOnly(True); self.ai_answer.setPlainText('No model connection has been verified. Start your chosen local server separately. No model is loaded automatically.'); layout.addWidget(self.ai_answer, 1)
        self.pages.addWidget(page)

    def make_history(self):
        page = QWidget(); layout = QVBoxLayout(page)
        layout.addWidget(label('Remember. Revisit. Compare.', 'title'))
        layout.addWidget(label('Replay follows recorded event order. Scrub by event; original UTC timestamps remain visible. Playback advances one event every 400 ms, compressing historical time.', 'sub'))
        self.timeline = QSlider(Qt.Orientation.Horizontal); self.timeline.valueChanged.connect(self.seek); layout.addWidget(self.timeline)
        self.replay_label = label('No history yet', 'sub'); layout.addWidget(self.replay_label)
        row = QHBoxLayout(); row.addWidget(button('Replay in universe', self.begin_replay)); self.play_button = button('Play / pause replay', self.toggle_replay); row.addWidget(self.play_button); row.addStretch(); layout.addLayout(row)
        self.history_text = QPlainTextEdit(); self.history_text.setReadOnly(True); layout.addWidget(self.history_text)
        layout.addWidget(label('History is immutable and capped at 10,000 events / 256 MiB. At capacity, export history and choose a fresh data directory; old evidence is never silently overwritten.', 'sub'))
        self.pages.addWidget(page)

    def make_text_page(self, title, description):
        page = QWidget(); layout = QVBoxLayout(page); layout.addWidget(label(title, 'title')); layout.addWidget(label(description, 'sub'))
        text = QPlainTextEdit(); text.setReadOnly(True); layout.addWidget(text, 1); self.pages.addWidget(page); return text

    def make_code(self):
        page = QWidget(); layout = QVBoxLayout(page)
        layout.addWidget(label('Absorb selected information', 'title'))
        layout.addWidget(label('Select a repository to count files and language extensions. This alpha reads metadata only, with a 2,000-file / 2-second bound. Typed text is explicitly stored when absorbed.', 'sub'))
        layout.addWidget(button('Select source directory', self.choose_code))
        self.words = QPlainTextEdit(); self.words.setPlaceholderText('Type words or an engineering result to turn into an information event…'); layout.addWidget(self.words)
        layout.addWidget(button('Absorb this text', self.absorb_text, True)); self.pages.addWidget(page)

    def make_settings(self, settings, gpu_python):
        page = QWidget(); layout = QVBoxLayout(page)
        layout.addWidget(label('Your sources. Your limits.', 'title'))
        form = QFormLayout()
        self.python_path = QLineEdit(gpu_python or settings.get('gpu_python') or shutil.which('python') or '')
        form.addRow('GPU Python executable', self.python_path)
        row = QHBoxLayout(); row.addWidget(button('Browse Python', self.choose_python)); row.addWidget(button('Check interpreter', self.check_python)); row.addStretch(); form.addRow(row)
        self.fps = QComboBox(); self.fps.addItems(['15', '30', '60']); self.fps.setCurrentText(str(settings.get('fps', 30))); self.fps.currentTextChanged.connect(self.render_settings)
        self.particles = QSpinBox(); self.particles.setRange(32, 512); self.particles.setValue(int(settings.get('particles', 256))); self.particles.valueChanged.connect(self.render_settings)
        self.scale = QSlider(Qt.Orientation.Horizontal); self.scale.setRange(0, 100); self.scale.setValue(int(settings.get('intensity', 100))); self.scale.valueChanged.connect(self.render_settings)
        form.addRow('Frame-rate cap', self.fps); form.addRow('Particle limit', self.particles); form.addRow('Visual intensity', self.scale); layout.addLayout(form)
        layout.addWidget(button('Save settings', self.save_settings, True))
        self.sources_label = label('', 'sub'); layout.addWidget(self.sources_label)
        layout.addWidget(label('No passive session capture. Hardware polling is off at startup. Import and text actions are explicit. Rendering controls never change raw measurements. Local model calls occur only on request.', 'sub'))
        layout.addStretch(); self.pages.addWidget(page); self.render_settings()

    def navigate(self, row):
        self.pages.setCurrentIndex(row); self.title.setText('Your computational universe' if row == 0 else self.names[row])

    def inspect(self, event):
        self.inspector.setPlainText(json.dumps(event, indent=2, ensure_ascii=False))
        self.scene.selected_id = event['event_id']; self.scene.update()

    def pause_scene(self):
        self.scene.paused = not self.scene.paused
        self.pause_button.setText('Resume motion' if self.scene.paused else 'Pause motion')

    def reset_camera(self):
        from PySide6.QtCore import QPointF
        self.scene.yaw, self.scene.tilt, self.scene.zoom, self.scene.pan = -0.2, 0.6, 1.0, QPointF(0, 0)
        self.scene.update()

    def change_mode(self, *_):
        if not hasattr(self, 'scene') or not hasattr(self, 'live_timer'):
            return
        self.inspector.clear(); self.scene.selected_id = None
        mode = self.mode.currentIndex()
        if mode != 1:
            self.live_timer.stop(); self.live_button.setText('Start live telemetry')
        self.replay_timer.stop()
        if mode == 2:
            self.replay = Replay(self.observed); self.timeline.setMaximum(len(self.observed)); self.timeline.setValue(len(self.observed)); self.replay.seek(len(self.observed))
        self.refresh()

    def refresh(self):
        if not hasattr(self, 'history_text'):
            return
        mode = self.mode.currentIndex()
        self.displayed = self.synthetic if mode == 0 else self.observed if mode == 1 else self.replay.seek(self.timeline.value())
        self.mode_badge.setText(['DEMO: SYNTHETIC DATA', 'REAL DATA · OBSERVED', 'REPLAY · RECORDED EVENTS'][mode])
        self.scene.set_events(self.displayed)
        failures = sum(e['status'] == 'FAIL' for e in self.displayed)
        sources = sorted({e['source'] for e in self.displayed})
        self.stats.setText(f'{len(self.displayed):,} EVENTS    /    {len(sources)} SOURCES    /    {failures} FAILURES    /    {len(self.observed):,} OBSERVED RECORDS RETAINED')
        self.populate_table()
        def summary(events):
            return '\n\n'.join(f"{e['timestamp_utc']}  |  {e['source']}  |  {e['status']}\n{e['message']}\n" + json.dumps(e['metrics'], ensure_ascii=False) for e in events[-60:]) or 'No matching observed records.'
        self.hardware.setPlainText(summary([e for e in self.observed if e['component'] in ('cpu', 'gpu', 'memory', 'storage')]))
        self.software.setPlainText(summary([e for e in self.observed if e['source'] == 'ARX' and e['component'] == 'code']))
        self.guardian.setPlainText(summary([e for e in self.observed if e['status'] in ('FAIL', 'SKIP', 'CANCELLED')]))
        self.history_text.setPlainText(summary([e for e in self.observed if e['category'] == 'benchmark']))
        self.sources_label.setText('Active: ' + ('psutil + nvidia-smi polling every 2 seconds' if self.live_timer.isActive() else 'no continuous telemetry') + '\nRetained sources: ' + ', '.join(sorted({e['source'] for e in self.observed})))

    def populate_table(self, *_):
        if not hasattr(self, 'table'):
            return
        needle, status, since = self.search.text().lower(), self.filter_status.currentText(), self.since.text().strip()
        rows = [e for e in self.displayed if (status == 'All outcomes' or e['status'] == status) and e['timestamp_utc'] >= since and needle in json.dumps(e).lower()]
        self.table.setSortingEnabled(False); self.table.setRowCount(len(rows))
        for row, event in enumerate(rows):
            measurements = '; '.join(f"{name}: {m['value']:.4g} {m['unit']}" for name, m in event['metrics'].items()) or 'No numerical measurement'
            values = [event['timestamp_utc'], event['source'], event['component'].upper(), event['category'], event['status'], measurements, event['event_id']]
            for column, text in enumerate(values):
                item = QTableWidgetItem(text); item.setData(Qt.ItemDataRole.UserRole, event['event_id'])
                if column == 4:
                    item.setForeground(QColor(event['visual']['color']))
                self.table.setItem(row, column, item)
        self.table.setSortingEnabled(True)
        for column, width in enumerate([180, 110, 85, 120, 75, 320]):
            self.table.setColumnWidth(column, width)

    def select_table(self):
        items = self.table.selectedItems()
        if items:
            eid = items[0].data(Qt.ItemDataRole.UserRole)
            event = next((e for e in self.displayed if e['event_id'] == eid), None)
            if event:
                self.inspect(event)
                self.status.showMessage('Selected event is available in the Universe inspector: ' + eid)

    def submit(self, task, callback):
        if self.pending:
            self.status.showMessage('A source operation is still running. Please wait.'); return False
        self.pending = (self.pool.submit(task), callback)
        self.status.showMessage('Reading the selected source…'); return True

    def poll_task(self):
        if self.pending and self.pending[0].done():
            future, callback = self.pending; self.pending = None
            try:
                callback(future.result())
            except Exception as exc:
                self.report_error(str(exc))

    def report_error(self, message):
        self.last_error = message
        self.status.showMessage('ERROR: ' + message)
        event = make_event('application', 'diagnostic', 'guardian', status='FAIL', message=message[:1800])
        try:
            self.memory.add([event]); self.observed = self.memory.events(); self.refresh()
        except Exception:
            pass

    def ingest(self, events):
        if any(e['data_kind'] != 'observed' for e in events):
            raise ValidationError('real-data intake only accepts observed records; demo remains isolated')
        count = self.memory.add(events); self.observed = self.memory.events()
        self.mode.setCurrentIndex(1); self.refresh(); self.status.showMessage(f'{count} new events stored. Duplicate evidence was preserved without re-insertion.')

    def choose_import(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select ARX or ATOMVERSE JSON', '', 'JSON (*.json)')
        if path:
            self.import_path(path)

    def import_path(self, path):
        return self.submit(lambda: import_events(path), self.ingest)

    def sample(self):
        if self.pending or self.bench.active:
            return
        self.submit(sample_hardware, self.ingest)

    def toggle_live(self):
        if self.live_timer.isActive():
            self.live_timer.stop(); self.live_button.setText('Start live telemetry'); self.refresh()
        else:
            self.mode.setCurrentIndex(1); self.live_timer.start(); self.live_button.setText('Stop live telemetry'); self.sample(); self.refresh()

    def choose_export(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Export current mode (may contain selected private data)', 'atomverse-report.json', 'JSON (*.json);;CSV (*.csv)')
        if path:
            try:
                export_events(path, self.displayed); self.status.showMessage(f'Exported {len(self.displayed)} events. Review before sharing.')
            except Exception as exc:
                self.report_error(str(exc))

    def start_benchmark(self, kind):
        try:
            self.mode.setCurrentIndex(1)
            self.bench.start(kind, self.duration.value(), self.cpu_size.value() if kind == 'cpu' else self.gpu_size.value(), self.python_path.text())
            self.cpu_button.setEnabled(False); self.gpu_button.setEnabled(False); self.cancel_button.setEnabled(True)
            self.progress.setValue(0); self.bench_status.setText('Starting worker. Waiting for measured progress…')
            self.scene.timer.setInterval(67)
        except Exception as exc:
            self.report_error(str(exc))

    def benchmark_progress(self, data):
        self.progress.setValue(int(data.get('fraction', 0) * 100))
        self.bench_status.setText(f"Measured: {data.get('elapsed_s', 0):.2f} s · {data.get('iterations', 0)} completed iterations")
        transient = make_event('benchmark-worker', 'benchmark_progress', self.bench.kind,
                               {'duration_ms': metric(data['elapsed_s'] * 1000, 'ms')}, message='In progress; outcome not yet verified')
        if self.mode.currentIndex() == 1:
            self.scene.set_events(self.displayed + [transient])

    def benchmark_finished(self, event):
        self.last_result = event
        self.cpu_button.setEnabled(True); self.gpu_button.setEnabled(True); self.cancel_button.setEnabled(False)
        self.progress.setValue(100 if event['status'] == 'PASS' else 0)
        self.bench_status.setText(event['status'] + ': ' + event['message'])
        self.bench_result.setPlainText(json.dumps(event, indent=2))
        try:
            self.ingest([event])
        except Exception as exc:
            self.report_error(str(exc))
        self.render_settings()

    def begin_replay(self):
        self.mode.setCurrentIndex(2); self.timeline.setValue(0); self.nav.setCurrentRow(0); self.replay_timer.start()

    def toggle_replay(self):
        if self.replay_timer.isActive():
            self.replay_timer.stop()
        else:
            if self.mode.currentIndex() != 2:
                self.mode.setCurrentIndex(2)
            if self.timeline.value() == self.timeline.maximum():
                self.timeline.setValue(0)
            self.replay_timer.start()

    def step_replay(self):
        if self.timeline.value() >= self.timeline.maximum():
            self.replay_timer.stop()
        else:
            self.timeline.setValue(self.timeline.value() + 1)

    def seek(self, *_):
        if self.mode.currentIndex() == 2:
            self.refresh()
            last = self.displayed[-1]['timestamp_utc'] if self.displayed else 'beginning'
            self.replay_label.setText(f'{len(self.displayed)} / {len(self.replay.events)} recorded events · {last}')

    def choose_code(self):
        path = QFileDialog.getExistingDirectory(self, 'Select repository metadata source')
        if path:
            self.submit(lambda: inspect_repository(path), self.ingest)

    def absorb_text(self):
        text = self.words.toPlainText()
        if not text.strip() or len(text) > 1800:
            self.report_error('Enter 1–1800 characters of explicitly selected text.'); return
        self.ingest([make_event('operator-text', 'human_language', 'ai', {'characters': metric(len(text), 'count')}, message=text)])
        self.words.clear()

    def choose_python(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select existing Python executable', '', 'Python (python.exe)')
        if path:
            self.python_path.setText(path)

    def check_python(self):
        path = self.python_path.text()
        self.submit(lambda: discover_python(path), lambda data: self.status.showMessage(json.dumps(data)))

    def ask_ai(self):
        endpoint, model, question, evidence = self.endpoint.text(), self.model_name.text(), self.question.text(), list(self.observed[-12:])
        self.submit(lambda: explain_local(endpoint, model, question, evidence), self.ai_answer.setPlainText)

    def render_settings(self, *_):
        if not hasattr(self, 'scale'):
            return
        cap = min(15, int(self.fps.currentText())) if self.bench.active else int(self.fps.currentText())
        self.scene.timer.setInterval(round(1000 / cap))
        self.scene.particle_limit = self.particles.value(); self.scene.effective_limit = self.particles.value(); self.scene.intensity = self.scale.value() / 100
        self.scene.set_events(self.displayed)

    def save_settings(self):
        settings = {'gpu_python': self.python_path.text(), 'endpoint': self.endpoint.text(), 'model': self.model_name.text(), 'fps': int(self.fps.currentText()), 'particles': self.particles.value(), 'intensity': self.scale.value()}
        atomic_write(self.settings_path, json.dumps(settings, indent=2)); self.status.showMessage('Local settings saved.')

    def closeEvent(self, event):
        self.closing = True
        self.live_timer.stop(); self.replay_timer.stop(); self.scene.timer.stop(); self.poll.stop()
        self.bench.cancel()
        # All source tasks have explicit I/O deadlines; no uncontrolled monitoring survives the window.
        self.pool.shutdown(wait=True, cancel_futures=True)
        self.memory.close()
        event.accept()
