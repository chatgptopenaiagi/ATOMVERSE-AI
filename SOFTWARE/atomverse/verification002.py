"""Real native application acceptance. Reports facts, fails on unmet assertions."""
import json
import statistics
import sys
import time
from pathlib import Path
from PySide6.QtCore import QProcess, QTimer, Qt, QPoint
from PySide6.QtTest import QTest
from .adapters import import_events
from .core import atomic_write, export_events, utc_now, validate_event
from .live_controller import command
from .science import classification
from .storage import recent, compare


def percentile(values, percent):
    return sorted(values)[min(len(values) - 1, int((len(values) - 1) * percent))] if values else 0


def verify(app, w, output, arx_path):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    checks, loads, heartbeat, packets, benchmarks = {}, [], [], [], []
    state = {'step': 0, 'time': time.monotonic(), 'last_tick': time.monotonic(), 'phase': 'setup'}
    started = time.monotonic()
    timer = QTimer(w); timer.setInterval(50); w.verification_timer = timer
    report = {'version': '0.2.0-alpha.1', 'started_at_utc': utc_now(), 'packaged_executable': bool(getattr(sys, 'frozen', False)), 'checks': checks}
    performance = {'method': '15-second idle-observer phase and 15-second controlled-load phase; three owned 12-second CPU workloads plus bounded CPU/GPU benchmark; sampling 1 s, 24 processes, 30 fps; CPU normalized across logical processors', 'phases': {}}
    def phase_stats(name):
        rows = [p for p in packets if p['phase'] == name]
        cpu = [p['overhead']['utilization_pct']['value'] for p in rows if 'utilization_pct' in p['overhead']]
        ram = [p['overhead']['working_set_bytes']['value'] for p in rows]
        duration = [p['sample_duration_ms'] for p in rows]
        lag = [p['scheduling_delay_ms'] for p in rows]
        frames = [p['paint_ms'] for p in rows if p['paint_ms']]
        return {'samples': len(rows), 'cpu_pct_system_mean': statistics.mean(cpu) if cpu else None, 'working_set_bytes_max': max(ram, default=0),
                'sample_duration_ms_p95': percentile(duration, .95), 'scheduling_delay_ms_p95': percentile(lag, .95),
                'paint_ms_mean': statistics.mean(frames) if frames else 0,
                'system_cpu_pct_min': min((p['system_cpu_pct'] for p in rows if p['system_cpu_pct'] is not None), default=None), 'system_cpu_pct_max': max((p['system_cpu_pct'] for p in rows if p['system_cpu_pct'] is not None), default=None)}
    def finish(error=None):
        timer.stop()
        w.observer.stop()
        for process in loads:
            if process.state() != QProcess.ProcessState.NotRunning:
                process.kill(); process.waitForFinished(1500)
        performance['phases'] = {name: phase_stats(name) for name in ('idle', 'active')}
        performance.update(gui_tick_delay_ms_p95=percentile(heartbeat, .95), gui_tick_delay_ms_max=max(heartbeat, default=0),
                           paint_ms_p95=percentile(list(w.scene.paint_ms), .95), frames=w.scene.frame_count,
                           particle_limit=w.scene.particle_limit, effective_particle_limit=w.scene.effective_limit, queue_capacity=4, display_batches_dropped=w.observer.dropped)
        report.update(status='FAIL' if error else 'PASS', error=error, elapsed_s=time.monotonic()-started,
                      retained_events=w.memory.db.execute('SELECT count(*) FROM events').fetchone()[0],
                      benchmarks=[{'component': e['component'], 'status': e['status'], 'metrics': e['metrics'], 'configuration': e['configuration']} for e in benchmarks], performance=performance)
        w.close()
        checks['clean_shutdown'] = not w.observer.active and not w.bench.active and not w.live_poll.isActive() and all(p.state() == QProcess.ProcessState.NotRunning for p in loads)
        if not checks['clean_shutdown']:
            report['status'] = 'FAIL'
        atomic_write(output/'gui-verification.json', json.dumps(report, indent=2))
        atomic_write(output/'performance.json', json.dumps(performance, indent=2))
        app.exit(0 if report['status'] == 'PASS' else 1)
    def tick():
        now = time.monotonic(); heartbeat.append(max(0, (now - state['last_tick']) * 1000 - 50)); state['last_tick'] = now
        try:
            if now - started > 95:
                raise AssertionError('Mission 002 acceptance deadline exceeded')
            latest = w.observer.latest
            if latest and state.get('sequence') != latest['sequence']:
                state['sequence'] = latest['sequence']
                overhead = next(e for e in latest['events'] if e['scientific']['entity_id'] == 'atomverse:overhead')
                cpu = next(e for e in latest['events'] if e['scientific']['entity_id'] == 'system:cpu')
                packets.append({'phase': state['phase'], 'overhead': overhead['metrics'], 'system_cpu_pct': cpu['metrics'].get('utilization_pct', {}).get('value'),
                                'sample_duration_ms': latest['sample_duration_ms'], 'scheduling_delay_ms': latest['scheduling_delay_ms'],
                                'paint_ms': statistics.mean(w.scene.paint_ms) if w.scene.paint_ms else 0})
            step = state['step']
            if step == 0:
                assert w.isVisible() and not w.observer.active
                checks['native_window_and_opt_in_startup'] = True
                w.mode.setCurrentIndex(0); assert all(classification(e) == 'SIMULATED' for e in w.displayed)
                checks['simulation_label_and_isolation'] = 'SIMULATED' in w.mode_badge.text()
                w.grab().save(str(output/'demo-universe.png'))
                assert arx_path, 'real ARX report required'
                w.ingest(import_events(arx_path)); checks['real_arx_import'] = len(import_events(arx_path))
                w.interval.setValue(1); w.toggle_live(); state.update(step=1, time=now, phase='idle')
            elif step == 1 and now - state['time'] >= 15:
                assert w.observer.samples >= 10 and not w.last_error
                checks['continuous_cpu_and_memory_sampling'] = True
                w.drain_observations()
                cpu_events = [e for e in w.observed if e.get('scientific', {}).get('entity_id') == 'system:cpu' and 'utilization_pct' in e['metrics']]
                assert len({e['visual']['visual_energy'] for e in cpu_events}) > 1
                assert all(abs(e['visual']['visual_energy'] - e['metrics']['utilization_pct']['value']/100) < 1e-7 for e in cpu_events)
                checks['live_values_drive_deterministic_visual_changes'] = True
                events = latest['events']; gpu = next(e for e in events if e['component'] == 'gpu')
                assert gpu['source'] == 'NVIDIA NVML'
                checks['gpu_telemetry'] = {'classification': classification(gpu), 'metric_names': list(gpu['metrics']), 'unavailable': gpu['scientific']['unavailable']}
                assert 'utilization_pct' in gpu['metrics'], 'This discovered NVIDIA workstation must supply GPU measurements'
                processes = [e for e in events if e['scientific']['entity'].get('type') == 'process']
                assert any(any(r['type'] == 'PARENT' for r in e['scientific']['relationships']) for e in processes)
                checks['real_windows_process_relationships'] = len(processes)
                for _ in range(3):
                    p = QProcess(w); program, args = command('--verification-load'); p.start(program, args); loads.append(p)
                w.duration.setValue(2); w.cpu_size.setValue(32); w.start_benchmark('cpu')
                state.update(step=2, time=now, phase='active')
            elif step == 2 and not w.bench.active:
                assert w.last_result and w.last_result['status'] == 'PASS'
                benchmarks.append(w.last_result); checks['cpu_benchmark_passed'] = w.last_result['metrics']
                w.duration.setValue(.3); w.gpu_size.setValue(256); w.start_benchmark('gpu'); state['step'] = 3
            elif step == 3 and not w.bench.active:
                assert w.last_result and w.last_result['component'] == 'gpu' and w.last_result['status'] == 'PASS'
                benchmarks.append(w.last_result); checks['gpu_benchmark_passed'] = w.last_result['metrics']
                state['step'] = 4
            elif step == 4 and now - state['time'] >= 15:
                assert all(p.state() == QProcess.ProcessState.NotRunning and p.exitCode() == 0 for p in loads)
                w.observer.stop(); w.drain_observations(); state['phase'] = 'interaction'
                idle, active = phase_stats('idle'), phase_stats('active')
                assert idle['samples'] >= 10 and active['samples'] >= 10
                assert max(idle['cpu_pct_system_mean'], active['cpu_pct_system_mean']) < 5
                assert max(idle['working_set_bytes_max'], active['working_set_bytes_max']) < 450 * 1024**2
                assert max(idle['sample_duration_ms_p95'], active['sample_duration_ms_p95']) < 700
                assert percentile(heartbeat, .95) < 150
                checks['bounded_observer_overhead_and_responsiveness'] = True
                w.nav.setCurrentRow(2); assert w.table.rowCount() > 100
                w.search.setText('no-such-event'); assert w.table.rowCount() == 0; w.search.clear()
                checks['scientific_table_and_filter'] = True
                w.nav.setCurrentRow(6); assert w.process_tree.topLevelItemCount() > 0
                checks['process_galaxy_inspection'] = True
                w.nav.setCurrentRow(0); w.scene.repaint()
                target = next(e for e in reversed(w.observed) if e.get('scientific', {}).get('entity_id') == 'system:cpu')
                w.inspect(target); assert target['event_id'] in w.inspector.toPlainText() and 'RECORDED ENTITY HISTORY' in w.inspector.toPlainText()
                yaw = w.scene.yaw; QTest.keyClick(w.scene, Qt.Key.Key_Right); assert w.scene.yaw != yaw
                zoom = w.scene.zoom; QTest.keyClick(w.scene, Qt.Key.Key_Plus); assert w.scene.zoom > zoom
                before = w.scene.pan.x(); QTest.mousePress(w.scene, Qt.MouseButton.RightButton, pos=QPoint(40,40)); QTest.mouseMove(w.scene, QPoint(75,60), 20); QTest.mouseRelease(w.scene, Qt.MouseButton.RightButton, pos=QPoint(75,60)); assert w.scene.pan.x() != before
                w.pause_scene(); phase = w.scene.phase; QTest.qWait(80); assert w.scene.phase == phase; w.pause_scene()
                checks['navigation_pause_and_evidence_inspection'] = True
                w.grab().save(str(output/'recorded-universe.png'))
                w.ingest([compare(w.observed, 'system:cpu', 'utilization_pct')]); checks['historical_comparison_with_input_references'] = True
                count = w.memory.db.execute('SELECT count(*) FROM events').fetchone()[0]
                w.mode.setCurrentIndex(2); w.timeline.setValue(20)
                assert len(w.displayed) == 20 and 'REPLAY' in w.mode_badge.text()
                assert w.memory.db.execute('SELECT count(*) FROM events').fetchone()[0] == count
                checks['recorded_replay_without_database_mutation'] = True
                events = recent(w.memory, 10000); export_events(output/'observations.json', events)
                readback = json.loads((output/'observations.json').read_text())['events']
                assert readback == events and all(validate_event(e) == e for e in readback)
                checks['json_export_and_provenance_readback'] = len(readback)
                assert w.memory.db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
                checks['sqlite_integrity'] = True
                w.mode.setCurrentIndex(1); w.endpoint.setText('http://127.0.0.1:1'); w.question.setText('Summarize observed CPU activity.'); w.ask_ai()
                state.update(step=5, time=now)
            elif step == 5 and w.ai_answer.toPlainText().startswith('UNAVAILABLE:'):
                checks['optional_ai_unavailable_does_not_disable_application'] = True
                w.toggle_live(); state.update(step=6, time=now)
            elif step == 6 and now - state['time'] > 2:
                assert w.observer.active and w.scene.frame_count > 100
                checks['observer_restart_and_shutdown_while_active'] = True
                finish()
        except Exception as exc:
            finish(f'{type(exc).__name__}: {exc} (step {state["step"]})')
    timer.timeout.connect(tick); timer.start()


def verify_ai(app, w, output, endpoint):
    """Actual GUI/worker/persistence path; requires an already available local server."""
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic(); state = {'step': 0}
    timer = QTimer(w); timer.setInterval(100); w.verification_timer = timer
    def finish(error=None):
        timer.stop()
        events = recent(w.memory, 10000)
        interpretations = [e for e in events if classification(e) == 'AI_INTERPRETED']
        refs = {i for e in interpretations for i in e['provenance']['event_ids']}
        report = {'status': 'FAIL' if error else 'PASS', 'error': error, 'packaged_executable': bool(getattr(sys, 'frozen', False)),
                  'elapsed_s': time.monotonic()-started, 'model': w.model_name.text(), 'interpretations': interpretations,
                  'source_observations': [e for e in events if e['event_id'] in refs], 'observer_samples': w.observer.samples,
                  'rendered_frames': w.scene.frame_count}
        w.close(); report['clean_shutdown'] = not w.observer.active and w.intelligence.process.state() == QProcess.ProcessState.NotRunning
        atomic_write(output/'ai-verification.json', json.dumps(report, indent=2))
        app.exit(1 if error else 0)
    def tick():
        try:
            if time.monotonic()-started > 105:
                raise AssertionError('AI verification exceeded deadline')
            if state['step'] == 0:
                w.interval.setValue(1); w.toggle_live(); state['step'] = 1
            elif state['step'] == 1 and w.observer.samples >= 3:
                w.drain_observations()
                event = next(e for e in reversed(w.observed) if e.get('scientific', {}).get('entity_id') == 'system:cpu')
                state['event'] = event; w.inspect(event)
                w.endpoint.setText(endpoint); w.question.setText('Give one short sentence about this CPU measurement. Cite its event ID. Do not infer causes.')
                w.nav.setCurrentRow(3); w.ask_ai(); state['step'] = 2; state['samples'] = w.observer.samples
            elif state['step'] == 2:
                if w.ai_answer.toPlainText().startswith('UNAVAILABLE:'):
                    raise AssertionError(w.ai_answer.toPlainText())
                if w.ai_answer.toPlainText().startswith('AI_INTERPRETED'):
                    events = recent(w.memory, 10000)
                    answer = next(e for e in reversed(events) if classification(e) == 'AI_INTERPRETED')
                    assert answer['metrics'] == {} and state['event']['event_id'] in answer['provenance']['event_ids']
                    assert any(e == state['event'] for e in events)
                    assert w.observer.samples > state['samples'] + 2
                    w.grab().save(str(output/'ai-interpretation.png')); finish()
        except Exception as exc:
            finish(str(exc))
    timer.timeout.connect(tick); timer.start()
