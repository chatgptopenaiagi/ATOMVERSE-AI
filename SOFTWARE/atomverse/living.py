"""Mission 002 extension of the verified Mission 001 native application."""
from collections import deque
import json
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QFormLayout, QSpinBox, QTreeWidget, QTreeWidgetItem, QLabel, QComboBox, QScrollArea
from .app import Window, label, button
from .core import Replay, ValidationError, atomic_write
from .science import classification, COLORS
from .observer import ObserverConfig
from .live_controller import LiveController
from .storage import recent, compare


class LivingWindow(Window):
    def __init__(self, data_dir, gpu_python=''):
        super().__init__(data_dir, gpu_python)
        self.live_timer.stop()
        self.observer = LiveController(self)
        self.observer.failed.connect(self.observer_error)
        self.observer.stopped.connect(self.observer_stopped)
        self.live_packets = deque(maxlen=120)
        self.live_poll = QTimer(self); self.live_poll.setInterval(200); self.live_poll.timeout.connect(self.drain_observations); self.live_poll.start()
        self.observed = recent(self.memory)
        self.names = ['Live Universe', 'Benchmark Arena', 'Scientific Data', 'AI Interpretation', 'Computational Memory', 'System Observer', 'Process Galaxy', 'Source Code Galaxy', 'Engine Integration', 'Settings']
        for i, name in enumerate(self.names):
            self.nav.item(i).setText(name)
        for w in self.findChildren(QLabel):
            text = w.text()
            if text.startswith('GENESIS\n'):
                w.setText('LIVING UNIVERSE\n0.2.0-alpha.1\nLocal · experimental')
            elif text == 'Hardware observations':
                w.setText('System observer')
            elif text.startswith('Import an ARX report or sample hardware.'):
                w.setText('Live numeric readings with source, UTC time and per-metric scientific classification. Missing sensors remain unavailable.')
            elif text == 'Software observations':
                w.setText('Process galaxy')
            elif text.startswith('ARX tool versions are snapshots'):
                w.setText('Process identity = PID + creation time. Select a row to inspect evidence. Child connections are the inverse of verified PARENT relationships. An omitted process is not presumed terminated.')
            elif text.startswith('History is immutable and capped'):
                w.setText('Mission 001, benchmarks and interpretations are protected. Continuous samples use the visible row/age retention policy. Replay and export cover the current 1,500-event window; older retained records can be loaded below.')
            elif text == 'Verified diagnostics':
                w.setText('Engine integration & diagnostics')
            elif text.startswith('Failures and skipped operations'):
                w.setText('Import explicitly selected ARX reports, COG 2.0.0 exports or DRAGONHYDRA module-registry/1 snapshots. Optional engines remain independent. No private sessions or credentials are captured.')
            elif text.startswith('Blue · information'):
                w.setText('Classifications appear above.\nRed marks failed outcomes.\nSelect an entity to inspect its\nmeasurements and history.')
        self.import_button.setText('Import engine / JSON')
        self.sample_button.setText('Observe once')
        self.live_button.setText('Start live observer')
        self.pages.widget(0).layout().insertWidget(1, label('● OBSERVED blue   ● DERIVED green   ■ AI purple   ■ SIMULATED amber   ● UNAVAILABLE gray\nMotion and size are dimensionless visual mappings. Lines connect recorded relationships.', 'sub'))
        self.process_tree = QTreeWidget(); self.process_tree.setHeaderLabels(['Process / relationship', 'State at timestamp', 'Working set', 'CPU / system', 'UTC'])
        self.process_tree.itemClicked.connect(self.select_process)
        self.pages.widget(6).layout().replaceWidget(self.software, self.process_tree); self.software.hide()
        self.class_filter = QComboBox(); self.class_filter.addItems(['All scientific classes', 'OBSERVED', 'DERIVED', 'AI_INTERPRETED', 'SIMULATED', 'UNAVAILABLE'])
        self.class_filter.currentTextChanged.connect(self.populate_table)
        self.pages.widget(2).layout().insertWidget(1, self.class_filter)
        self.pages.widget(4).layout().addWidget(button('Compare CPU utilization: two chronological windows', self.compare_cpu))
        self.pages.widget(4).layout().addWidget(button('Load all retained records (maximum 10,000)', self.load_history))
        self.pages.widget(4).layout().addWidget(button('Verify database integrity', self.verify_database))
        settings = {}
        try:
            settings = json.loads(self.settings_path.read_text())
        except (OSError, ValueError):
            pass
        self.interval = QDoubleSpinBox(); self.interval.setRange(0.5, 30); self.interval.setValue(settings.get('interval_s', 2)); self.interval.setSuffix(' s')
        self.process_limit = QSpinBox(); self.process_limit.setRange(1, 64); self.process_limit.setValue(settings.get('process_limit', 24))
        self.process_permission = QCheckBox('Process names, identity, executable identity and resource use'); self.process_permission.setChecked(settings.get('processes', True))
        self.gpu_permission = QCheckBox('Read-only NVIDIA device telemetry and process context membership'); self.gpu_permission.setChecked(settings.get('gpu', True))
        self.retention_rows = QSpinBox(); self.retention_rows.setRange(100, 10000); self.retention_rows.setValue(settings.get('max_rows', 10000))
        self.retention_hours = QDoubleSpinBox(); self.retention_hours.setRange(0.01, 720); self.retention_hours.setValue(settings.get('retention_hours', 1))
        form = QFormLayout(); form.addRow('Sampling interval', self.interval); form.addRow('Maximum observed processes', self.process_limit)
        form.addRow('Optional process source', self.process_permission); form.addRow('Optional NVIDIA source', self.gpu_permission)
        form.addRow('Retention row cap (includes protected history)', self.retention_rows); form.addRow('Rolling sample retention (hours)', self.retention_hours)
        self.pages.widget(9).layout().insertLayout(2, form)
        self.sources_label.setText('Observer is off. Starting it authorizes the displayed sources for this application session only. No command lines, file contents, network contents, or environment variables are collected. Changes apply at next start.')
        self.nav.currentRowChanged.connect(lambda _: self.refresh_details())
        self.setup_intelligence()
        settings_page = self.pages.widget(9)
        self.pages.removeWidget(settings_page)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(settings_page)
        self.pages.insertWidget(9, scroll)
        self.refresh()

    def config(self):
        return ObserverConfig(self.interval.value(), self.process_limit.value(), self.process_permission.isChecked(), self.gpu_permission.isChecked(), self.retention_rows.value(), self.retention_hours.value())

    def toggle_live(self):
        if self.observer.active:
            self.observer.stop()
        else:
            self.mode.setCurrentIndex(1)
            self.observer.start(self.memory.path, self.config())
            self.live_button.setText('Stop live observer')
            self.sources_label.setText('ACTIVE: CPU times/frequency, RAM/commit, disk counters' + ('; selected process metadata' if self.process_permission.isChecked() else '') + ('; NVIDIA NVML' if self.gpu_permission.isChecked() else '') + f'. Interval {self.interval.value()} s. Rolling cap {self.retention_rows.value()} rows / {self.retention_hours.value()} hours. Protected history is never pruned.')
            self.refresh()

    def sample(self):
        if self.observer.active:
            self.status.showMessage('Observer already running.'); return
        self.mode.setCurrentIndex(1)
        self.observer.start(self.memory.path, self.config(), samples=1)

    def observer_error(self, message):
        self.last_error = message
        self.status.showMessage('Observer unavailable: ' + message)

    def observer_stopped(self):
        self.live_button.setText('Start live observer')
        self.sources_label.setText('Observer stopped. Displayed values are historical snapshots. No background monitoring continues.')
        self.refresh()

    def drain_observations(self):
        if not self.observer.queue:
            return
        while self.observer.queue:
            packet = self.observer.queue.popleft(); self.live_packets.append({k: v for k, v in packet.items() if k != 'events'})
            self.observed.extend(packet['events'])
        self.observed = self.observed[-1500:]
        if packet['retention_removed']:
            self.observed = recent(self.memory)
        self.refresh()

    def change_mode(self, *args):
        if hasattr(self, 'observer') and self.mode.currentIndex() != 1:
            self.observer.stop()
        super().change_mode(*args)

    def refresh(self):
        if not hasattr(self, 'observer'):
            return super().refresh()
        mode = self.mode.currentIndex()
        self.displayed = self.synthetic if mode == 0 else self.observed if mode == 1 else self.replay.seek(self.timeline.value())
        self.mode_badge.setText('DEMO · SIMULATED' if mode == 0 else 'REPLAY · RECORDED' if mode == 2 else 'LIVE · SCIENTIFIC CLASSES' if self.observer.active else 'RECORDED · OBSERVER OFF')
        latest = {}
        for e in self.displayed:
            latest[e.get('scientific', {}).get('entity_id') or e['event_id']] = e
        self.scene.set_events(list(latest.values()))
        self.stats.setText(f'{len(self.displayed):,} RECORDS IN WINDOW  /  {len(latest)} ENTITIES & EVENTS  /  {self.observer.samples} SAMPLES THIS SESSION  /  {self.observer.dropped} SKIPPED DISPLAY BATCHES (STILL STORED)')
        self.refresh_details()

    def refresh_details(self):
        if not hasattr(self, 'process_tree'):
            return
        page = self.nav.currentRow()
        if page == 2:
            self.populate_table()
        elif page == 5:
            latest = {}
            for e in self.displayed:
                if e['component'] in ('cpu', 'gpu', 'memory', 'storage', 'guardian') and e['category'] == 'observation':
                    latest[e.get('scientific', {}).get('entity_id', e['event_id'])] = e
            lines = []
            for entity, e in latest.items():
                lines.append(f"{entity}   |   {e['timestamp_utc']}   |   {e['source']}")
                lines.extend(f"  {name}: {m['value']:.6g} {m['unit']} [{classification(e, name)}]" for name, m in e['metrics'].items())
                lines.extend(f'  {name}: UNAVAILABLE — {reason}' for name, reason in e.get('scientific', {}).get('unavailable', {}).items())
                lines.append('')
            self.hardware.setPlainText('\n'.join(lines) or 'Start observation to collect real measurements.')
        elif page == 6:
            self.process_tree.clear(); latest = {}
            for e in self.displayed:
                if e.get('scientific', {}).get('entity', {}).get('type') == 'process':
                    latest[e['scientific']['entity_id']] = e
            latest_stamp = max((e['timestamp_utc'] for e in latest.values()), default='')
            for e in list(latest.values())[-256:]:
                entity, metrics = e['scientific']['entity'], e['metrics']
                state = entity['state']
                if state != 'terminated' and (not self.observer.active or e['timestamp_utc'] != latest_stamp):
                    state = 'historical / not currently sampled'
                item = QTreeWidgetItem([f"{entity.get('name', '')} · PID {entity['pid']}", state, f"{metrics.get('working_set_bytes', {}).get('value', 0) / 1024**2:.1f} MiB" if 'working_set_bytes' in metrics else '—', f"{metrics['utilization_pct']['value']:.2f}% DERIVED" if 'utilization_pct' in metrics else 'unavailable', e['timestamp_utc']])
                item.setData(0, Qt.ItemDataRole.UserRole, e)
                for rel in e['scientific']['relationships']:
                    child = QTreeWidgetItem([rel['type'], rel['target'], rel['source']]); child.setData(0, Qt.ItemDataRole.UserRole, e); item.addChild(child)
                self.process_tree.addTopLevelItem(item)
            self.process_tree.setColumnWidth(0, 260); self.process_tree.setColumnWidth(1, 250)
        elif page == 8:
            self.guardian.setPlainText('ARX: report adapter 0.1 / gpu-compute 1.0\nCOG: explicit diagnostic export 2.0.0\nDRAGONHYDRA: explicit module-registry/1 snapshot\nNo engine is automatically started or authenticated.\n\n' + '\n'.join(f"{e['timestamp_utc']} [{classification(e)}] {e['source']}: {e['message']}" for e in self.observed[-150:] if e['status'] in ('FAIL', 'SKIP') or e['category'] == 'integration'))

    def populate_table(self, *args):
        if not hasattr(self, 'class_filter'):
            return super().populate_table(*args)
        original = self.displayed
        wanted = self.class_filter.currentText()
        self.displayed = [e for e in original if wanted == 'All scientific classes' or classification(e) == wanted or any(classification(e, k) == wanted for k in e['metrics'])][-1000:]
        super().populate_table(*args)
        by_id = {e['event_id']: e for e in self.displayed}
        self.table.setSortingEnabled(False)
        for row in range(self.table.rowCount()):
            e = by_id[self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)]
            self.table.item(row, 3).setText(f"{e['category']} · {classification(e)}")
            self.table.item(row, 3).setForeground(QColor(COLORS[classification(e)]))
            self.table.item(row, 5).setText('; '.join(f"{k}: {m['value']:.5g} {m['unit']} [{classification(e, k)}]" for k, m in e['metrics'].items()) or 'No numerical measurement')
        self.table.setSortingEnabled(True); self.displayed = original

    def inspect(self, event):
        super().inspect(event)
        entity = event.get('scientific', {}).get('entity_id')
        if entity:
            history = recent(self.memory, limit=12, entity=entity)
            self.inspector.appendPlainText('\nRECORDED ENTITY HISTORY (up to 12 retained observations)\n' + '\n'.join(f"{e['timestamp_utc']} [{classification(e)}] {json.dumps(e['metrics'])}" for e in history))

    def select_process(self, item, column):
        e = item.data(0, Qt.ItemDataRole.UserRole)
        if e:
            self.inspect(e); self.nav.setCurrentRow(0)

    def ingest(self, events):
        if not hasattr(self, 'observer'):
            return super().ingest(events)
        if any(e['data_kind'] == 'synthetic' for e in events):
            raise ValidationError('Simulated imports cannot enter the observed workspace')
        count = self.memory.add(events); self.observed = recent(self.memory)
        self.mode.setCurrentIndex(1); self.refresh(); self.status.showMessage(f'{count} records persisted with scientific provenance.')

    def import_path(self, path):
        from .integrations import import_selected
        return self.submit(lambda: import_selected(path), self.ingest)

    def load_history(self):
        if self.observer.active:
            self.observer.stop()
        self.observed = recent(self.memory, limit=10000)
        self.mode.setCurrentIndex(2); self.replay = Replay(self.observed); self.timeline.setMaximum(len(self.observed)); self.timeline.setValue(len(self.observed)); self.refresh()

    def compare_cpu(self):
        try:
            event = compare(self.observed, 'system:cpu', 'utilization_pct'); self.ingest([event])
            self.history_text.setPlainText(json.dumps(event, indent=2))
        except Exception as exc:
            self.status.showMessage(str(exc))

    def verify_database(self):
        result = self.memory.db.execute('PRAGMA integrity_check').fetchone()[0]
        self.history_text.setPlainText('SQLite integrity_check: ' + result)

    def save_settings(self):
        super().save_settings()
        if hasattr(self, 'interval'):
            values = json.loads(self.settings_path.read_text()); values.update(self.config().validate())
            atomic_write(self.settings_path, json.dumps(values, indent=2))

    def setup_intelligence(self):
        from .intelligence import IntelligenceController
        self.intelligence = IntelligenceController(self)
        self.intelligence.completed.connect(self.ai_completed)
        self.intelligence.failed.connect(lambda message: self.ai_answer.setPlainText('UNAVAILABLE: ' + message))
        self.pages.widget(3).layout().insertWidget(5, button('Cancel interpretation', self.intelligence.cancel))
        for w in self.pages.widget(3).findChildren(QLabel):
            if w.text().startswith('Optional local model.'):
                w.setText('Optional local model. Explain sends a bounded summary of at most 12 aggregate hardware events and your question. Process names and paths are excluded. AI text is stored as AI_INTERPRETED with source-event references; it is never a measurement or an executed action.')
        if self.endpoint.text() == 'http://127.0.0.1:8080/v1':
            self.endpoint.setText('http://127.0.0.1:11434')
        if self.model_name.text() == 'Qwen3-Coder-30B-A3B-Instruct':
            self.model_name.setText('qwen3.8:27b')

    def ask_ai(self):
        if not hasattr(self, 'intelligence'):
            return
        self.ai_answer.setPlainText('Requesting local interpretation… Observation continues independently.')
        try:
            selected = [e for e in self.observed if e['event_id'] == self.scene.selected_id and e.get('scientific', {}).get('entity_id', '').startswith(('system:', 'gpu:'))]
            self.intelligence.start(self.endpoint.text(), self.model_name.text(), self.question.text(), selected or self.observed)
        except Exception as exc:
            self.ai_answer.setPlainText('UNAVAILABLE: ' + str(exc))

    def ai_completed(self, event):
        self.ingest([event]); self.ai_answer.setPlainText('AI_INTERPRETED · hypotheses, not verified causes\n\n' + event['message'] + '\n\nProvenance: ' + json.dumps(event['provenance'], indent=2))

    def closeEvent(self, event):
        self.live_poll.stop(); self.observer.stop(); self.intelligence.cancel()
        super().closeEvent(event)
