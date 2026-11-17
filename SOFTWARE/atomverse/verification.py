"""Bounded acceptance driver executed inside source or the packaged GUI."""
import hashlib
import json
import sys
import time
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtTest import QTest
from .core import atomic_write, export_events, utc_now
from .adapters import import_events


def verify_gui(app, w, output, arx_path):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    checks = {}; start = time.monotonic(); state = {'step': 0, 'wait': 0}
    report = {'started_at_utc': utc_now(), 'packaged_executable': bool(getattr(sys, 'frozen', False)), 'checks': checks}
    timer = QTimer(w); timer.setInterval(100)
    w.verification_timer = timer

    def finish(error=None):
        timer.stop()
        report.update(status='FAIL' if error else 'PASS', elapsed_seconds=time.monotonic()-start, error=error,
                      retained_events=len(w.observed), benchmark_results=[e for e in w.observed if e['category'] == 'benchmark'],
                      rendering={'frames': w.scene.frame_count, 'paint_ms_mean': sum(w.scene.paint_ms)/max(1,len(w.scene.paint_ms)), 'paint_ms_max': max(w.scene.paint_ms, default=0), 'particle_limit': w.scene.particle_limit})
        atomic_write(output/'gui-verification.json', json.dumps(report, indent=2))
        w.close()
        app.exit(1 if error else 0)

    def tick():
        try:
            if time.monotonic()-start > 100:
                raise AssertionError('GUI verification exceeded 100 seconds')
            step = state['step']
            if step == 0:
                assert w.isVisible()
                checks['native_window_visible'] = True
                w.mode.setCurrentIndex(0); assert all(e['data_kind']=='synthetic' for e in w.displayed)
                w.grab().save(str(output/'demo-universe.png'))
                assert not w.live_timer.isActive()
                checks['demo_isolated_and_polling_off_by_default'] = True
                if not arx_path:
                    raise AssertionError('actual ARX report required for acceptance')
                w.import_path(arx_path)
                state['step'] = 1
            elif step == 1 and w.pending is None:
                expected = import_events(arx_path)
                stored = {e['event_id']:e for e in w.observed}
                assert all(stored[e['event_id']] == e for e in expected)
                checks['actual_arx_ingestion_values_and_sqlite'] = len(expected)
                assert all(e['data_kind']=='observed' for e in w.displayed)
                w.scene.paused=True; w.scene.repaint()
                point, _, e = w.scene.hits[-1]
                QTest.mouseClick(w.scene, Qt.MouseButton.LeftButton, pos=point.toPoint())
                selected = json.loads(w.inspector.toPlainText())
                assert selected['event_id'] in stored
                assert selected == stored[selected['event_id']]
                checks['mouse_particle_selection_resolves_exact_event'] = True
                yaw=w.scene.yaw; QTest.keyClick(w.scene, Qt.Key.Key_Right); assert w.scene.yaw != yaw
                zoom=w.scene.zoom; QTest.keyClick(w.scene, Qt.Key.Key_Plus); assert w.scene.zoom > zoom
                before=w.scene.pan.x()
                QTest.mousePress(w.scene, Qt.MouseButton.RightButton, pos=QPoint(50,50)); QTest.mouseMove(w.scene, QPoint(85,70), 30); QTest.mouseRelease(w.scene, Qt.MouseButton.RightButton, pos=QPoint(85,70))
                assert w.scene.pan.x() != before
                checks['rotate_zoom_pan'] = True
                phase=w.scene.phase; QTest.qWait(80); assert w.scene.phase == phase
                QTest.mouseClick(w.pause_button, Qt.MouseButton.LeftButton)
                QTest.qWait(80); assert w.scene.phase > phase
                checks['pause_resume'] = True
                w.search.setText('no-such-event'); assert w.table.rowCount()==0; w.search.clear()
                assert w.table.rowCount()==len(w.observed)
                checks['measurement_table_filter'] = True
                count=len(w.observed); w.mode.setCurrentIndex(2); w.timeline.setValue(3)
                assert len(w.displayed)==3 and len(w.memory.events())==count
                checks['replay_without_duplicate_writes'] = True
                w.mode.setCurrentIndex(1); w.nav.setCurrentRow(1); w.duration.setValue(0.3); w.cpu_size.setValue(16)
                QTest.mouseClick(w.cpu_button, Qt.MouseButton.LeftButton); assert w.bench.active
                w.nav.setCurrentRow(0)
                state['step']=2
            elif step == 2 and not w.bench.active:
                assert w.last_result and w.last_result['status']=='PASS'
                assert w.last_result['metrics']['iterations']['value']>0
                checks['cpu_benchmark_numeric_verification'] = True
                w.gpu_size.setValue(256)
                w.nav.setCurrentRow(1)
                QTest.mouseClick(w.gpu_button, Qt.MouseButton.LeftButton); assert w.bench.active
                w.nav.setCurrentRow(0); state['gpu_start_frames']=w.scene.frame_count
                state['step']=3
            elif step == 3 and not w.bench.active:
                assert w.last_result and w.last_result['component']=='gpu'
                assert w.last_result['status']=='PASS'
                assert w.last_result['configuration']['synchronized'] is True
                checks['gpu_cuda_benchmark_numeric_verification'] = True
                assert w.scene.frame_count > state['gpu_start_frames'] + 3
                checks['universe_rendered_during_gpu_worker'] = w.scene.frame_count - state['gpu_start_frames']
                w.nav.setCurrentRow(1)
                w.grab().save(str(output/'benchmark-arena.png'))
                before=len(w.observed)
                bad=output/'malformed-input.json'; bad.write_text('{bad', encoding='utf-8')
                w.import_path(bad); state['step']=4; state['before_error']=before
            elif step == 4 and w.pending is None:
                assert w.last_error and len(w.observed)==state['before_error']+1
                assert w.observed[-1]['status']=='FAIL'
                checks['malformed_input_visible_failure'] = True
                export_events(output/'observed-export.json', w.observed)
                assert import_events(output/'observed-export.json') == w.observed
                checks['export_readback'] = True
                w.nav.setCurrentRow(0); w.mode.setCurrentIndex(1); w.reset_camera(); w.inspect(w.last_result)
                w.scene.repaint(); w.grab().save(str(output/'real-universe.png'))
                w.particles.setValue(512); w.mode.setCurrentIndex(0)
                stress = [{**e, 'event_id':f"stress-{i}-{e['event_id']}"} for i in range(8) for e in w.synthetic]
                w.scene.set_events(stress); state['wait']=time.monotonic(); state['step']=5
            elif step == 5 and time.monotonic()-state['wait'] > 3:
                assert w.scene.frame_count>10
                checks['bounded_rendering'] = {'particles':len(w.scene.events), 'configured_limit':512, 'effective_limit':w.scene.effective_limit}
                assert len(w.scene.events)<=512
                assert w.memory.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                checks['database_integrity'] = True
                w.mode.setCurrentIndex(1); state['before_sample']=len(w.observed); w.sample(); state['step']=6
            elif step == 6 and w.pending is None:
                assert len(w.observed) >= state['before_sample'] + 2
                checks['real_hardware_sample'] = len(w.observed) - state['before_sample']
                export_events(output/'observed-export.json', w.observed)
                finish()
        except Exception as exc:
            finish(f'{type(exc).__name__}: {exc}')
    timer.timeout.connect(tick)
    timer.start()
