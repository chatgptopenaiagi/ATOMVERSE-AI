import json
import time
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from atomverse.app import Window
from atomverse.core import ValidationError, demo_events, make_event, metric


@pytest.fixture(scope='module')
def app():
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def window(app, tmp_path):
    w = Window(tmp_path); w.show(); QTest.qWait(60)
    yield w
    w.close(); app.processEvents()


def test_gui_sources_and_mode_isolation(window):
    assert window.mode.currentIndex() == 0
    assert not window.live_timer.isActive()
    assert len(window.scene.events) == 64
    window.mode.setCurrentIndex(1)
    assert window.scene.events == []
    with pytest.raises(ValidationError): window.ingest(demo_events())
    e = make_event('test', 'telemetry', 'cpu', {'utilization_pct': metric(42, '%')})
    window.ingest([e]); assert window.table.rowCount() == 1
    window.mode.setCurrentIndex(0); assert all(e['data_kind'] == 'synthetic' for e in window.displayed)
    assert len(window.observed) == 1


def test_gui_camera_selection_pause_and_settings(window):
    window.scene.paused = True; window.scene.repaint()
    point, _, event = window.scene.hits[-1]
    QTest.mouseClick(window.scene, Qt.MouseButton.LeftButton, pos=point.toPoint())
    assert json.loads(window.inspector.toPlainText())['event_id'] == event['event_id']
    yaw = window.scene.yaw; QTest.keyClick(window.scene, Qt.Key.Key_Right); assert window.scene.yaw > yaw
    zoom = window.scene.zoom; QTest.keyClick(window.scene, Qt.Key.Key_Plus); assert window.scene.zoom > zoom
    phase = window.scene.phase; QTest.qWait(70); assert window.scene.phase == phase
    original = json.dumps(window.displayed)
    window.scale.setValue(20); window.particles.setValue(32)
    assert len(window.scene.events) <= 32
    assert json.dumps(window.displayed) == original


def test_gui_benchmark_cancel_persists_accurate_state(window):
    window.duration.setValue(3); window.start_benchmark('cpu')
    assert window.bench.active
    window.fps.setCurrentText('60')
    assert window.scene.timer.interval() >= 66
    with pytest.raises(ValidationError): window.bench.start('cpu')
    QTest.qWait(150); window.bench.cancel(); QTest.qWait(80)
    assert not window.bench.active
    assert window.last_result['status'] == 'CANCELLED'
    assert window.memory.events()[-1]['status'] == 'CANCELLED'


def test_gui_replay_filter_and_shutdown(window):
    events = [make_event('test', 'test', 'cpu', event_id=str(i)) for i in range(4)]
    window.ingest(events); window.mode.setCurrentIndex(2); window.timeline.setValue(2)
    assert len(window.displayed) == 2
    assert len(window.memory.events()) == 4
    window.search.setText('absent'); assert window.table.rowCount() == 0
    window.search.clear(); assert window.table.rowCount() == 2
    window.close(); assert not window.scene.timer.isActive(); assert not window.bench.active


def test_gui_hard_deadline_failure(window):
    window.duration.setValue(3); window.start_benchmark('cpu')
    window.bench.timeout.start(1)
    QTest.qWait(180)
    assert window.last_result['status'] == 'FAIL'
    assert 'wall limit' in window.last_result['message']
    assert not window.bench.active


def test_gui_shutdown_terminates_active_worker(window):
    window.duration.setValue(3); window.start_benchmark('cpu')
    QTest.qWait(100)
    window.close()
    assert not window.bench.active
    assert window.bench.process.processId() == 0


def test_failed_executable_is_recorded_as_failure(window, tmp_path):
    invalid = tmp_path/'python.exe'; invalid.write_bytes(b'not an executable')
    window.python_path.setText(str(invalid)); window.start_benchmark('gpu')
    QTest.qWait(180)
    assert window.last_result['status'] == 'FAIL'
    assert not window.bench.active
    assert window.memory.events()[-1]['visual']['color'] == '#ff637c'
