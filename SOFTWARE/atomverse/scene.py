"""A bounded, interactive 3D projection painted by Qt; no GPU compute dependency."""
import hashlib
import math
import random
import time
from collections import deque
from PySide6.QtCore import Qt, QPointF, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget
from .core import ORBITS
from .science import classification, COLORS


class Universe(QWidget):
    selected = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(460, 420)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName('Interactive computational universe')
        self.events, self.hits = [], []
        self.phase, self.yaw, self.tilt, self.zoom = 0.0, -0.2, 0.6, 1.0
        self.pan, self.drag = QPointF(0, 0), None
        self.paused, self.selected_id = False, None
        self.intensity, self.particle_limit = 1.0, 256
        self.effective_limit = 256
        self.paint_ms = deque(maxlen=300)
        self.frame_count = 0
        self.last_quality_frame = -1
        self.last_tick = time.perf_counter()
        rng = random.Random(7)
        self.stars = [(rng.random(), rng.random(), rng.uniform(0.5, 1.6)) for _ in range(160)]
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.tick)
        self.timer.start()

    def set_events(self, events):
        self.events = list(events[-self.particle_limit:])
        if self.selected_id not in {e['event_id'] for e in self.events}:
            self.selected_id = None
        self.update()

    def tick(self):
        now = time.perf_counter()
        if not self.paused:
            self.phase += min(now - self.last_tick, 0.1)
            self.update()
        self.last_tick = now
        if self.frame_count and self.frame_count % 20 == 0 and self.last_quality_frame != self.frame_count and len(self.paint_ms) >= 20:
            self.last_quality_frame = self.frame_count
            mean = sum(list(self.paint_ms)[-20:]) / 20
            if mean > self.timer.interval() * 0.85:
                self.effective_limit = max(32, int(min(self.effective_limit, self.particle_limit) * 0.75))

    def project(self, radius, angle, orbit):
        x, z = radius * math.cos(angle), radius * math.sin(angle)
        y = math.sin(angle + orbit) * (14 + orbit * 2)
        x, z = x * math.cos(self.yaw) - z * math.sin(self.yaw), x * math.sin(self.yaw) + z * math.cos(self.yaw)
        y, z = y * math.cos(self.tilt) - z * math.sin(self.tilt), y * math.sin(self.tilt) + z * math.cos(self.tilt)
        factor = 850 / (850 + z)
        fit = min(self.width() / 780, self.height() / 680) * self.zoom
        return QPointF(self.width() / 2 + x * factor * fit + self.pan.x(), self.height() / 2 + y * factor * fit + self.pan.y()), factor * fit

    def paintEvent(self, event):
        start = time.perf_counter()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = QLinearGradient(0, 0, self.width(), self.height())
        bg.setColorAt(0, QColor('#0b1628'))
        bg.setColorAt(1, QColor('#070d18'))
        p.fillRect(self.rect(), bg)
        for x, y, r in self.stars:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(136, 175, 218, 75))
            p.drawEllipse(QPointF(x * self.width(), y * self.height()), r, r)
        colors = ['#68d5f7', '#aa91ff', '#74e2b1', '#a5b9d3', '#f29bdb', '#ffca78', '#a5def4', '#ff7c94']
        camera = (self.width(), self.height(), self.yaw, self.tilt, self.zoom, self.pan.x(), self.pan.y())
        if getattr(self, '_orbit_camera', None) != camera:
            self._orbit_camera = camera; self._orbit_paths = []
            for i in range(len(ORBITS)):
                path = QPainterPath()
                for step in range(81):
                    point, _ = self.project(90 + i * 32, step * math.tau / 80, i)
                    path.moveTo(point) if step == 0 else path.lineTo(point)
                self._orbit_paths.append(path)
        for i, name in enumerate(ORBITS):
            radius = 90 + i * 32
            path = self._orbit_paths[i]
            col = QColor(colors[i]); col.setAlpha(60)
            p.setPen(QPen(col, 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
            label, _ = self.project(radius, -0.8 + i * 0.61, i)
            p.setPen(QColor(colors[i]))
            p.setFont(QFont('Segoe UI', 8))
            p.drawText(label + QPointF(6, -6), name.upper())
        center, fit = self.project(0, 0, 0)
        energy = sum(e['visual']['visual_energy'] for e in self.events) / max(1, len(self.events)) * self.intensity
        glow = QRadialGradient(center, 85 * fit)
        glow.setColorAt(0, QColor(90, 203, 255, 180))
        glow.setColorAt(0.3, QColor(66, 128, 255, 60))
        glow.setColorAt(1, QColor(20, 55, 100, 0))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(glow)
        p.drawEllipse(center, 85 * fit, 85 * fit)
        p.setBrush(QColor('#183453')); p.setPen(QPen(QColor('#94e4ff'), 1.4))
        p.drawEllipse(center, (22 + energy * 9) * fit, (22 + energy * 9) * fit)
        p.setFont(QFont('Segoe UI', 9, QFont.Weight.DemiBold)); p.setPen(QColor('#d9f6ff'))
        p.drawText(center + QPointF(-23, 4), 'ATOM')
        self.hits = []
        rendered = self.events[-min(self.particle_limit, self.effective_limit):]
        for e in rendered:
            orbit = ORBITS.index(e['component'])
            seed = int(hashlib.sha256((e.get('scientific', {}).get('entity_id') or e['event_id']).encode()).hexdigest()[:8], 16)
            v = e['visual']['visual_energy'] * self.intensity
            angle = seed / 0xffffffff * math.tau + self.phase * v * 0.42
            point, scale = self.project(90 + orbit * 32 + ((seed % 19) - 9), angle, orbit)
            radius = (3.0 + 5.5 * v) * scale
            cls = classification(e)
            color = QColor(COLORS[cls] if 'scientific' in e and e['status'] != 'FAIL' else e['visual']['color'])
            if v > 0:
                for j in (3, 2, 1):
                    tail, _ = self.project(90 + orbit * 32 + ((seed % 19) - 9), angle - j * 0.025 * v, orbit)
                    faded = QColor(color); faded.setAlpha(35 + j * 8)
                    p.setPen(Qt.PenStyle.NoPen); p.setBrush(faded)
                    p.drawEllipse(tail, radius + j * 1.3, radius + j * 1.3)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(color)
            if cls in ('SIMULATED', 'AI_INTERPRETED'):
                p.drawRect(point.x() - radius, point.y() - radius, radius * 2, radius * 2)
            else:
                p.drawEllipse(point, radius, radius)
            entity = e.get('scientific', {}).get('entity', {})
            if entity.get('type') == 'cpu_core':
                p.setPen(QColor('#83cde5')); p.setFont(QFont('Segoe UI', 7))
                p.drawText(point + QPointF(8, -5), f"C{entity['logical_index']}")
            if e['event_id'] == self.selected_id:
                p.setPen(QPen(QColor('#ffffff'), 1.4)); p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(point, radius + 6, radius + 6)
            self.hits.append((point, max(9, radius + 3), e))
        positions = {e.get('scientific', {}).get('entity_id'): point for point, _, e in self.hits if e.get('scientific', {}).get('entity_id')}
        self.relationship_count = 0
        for point, _, e in self.hits:
            for rel in e.get('scientific', {}).get('relationships', []):
                target = positions.get(rel['target'])
                if target is not None:
                    p.setPen(QPen(QColor(115, 190, 200, 65), 0.8, Qt.PenStyle.DotLine))
                    p.drawLine(point, target); self.relationship_count += 1
        p.setPen(QColor('#7f95af')); p.setFont(QFont('Segoe UI', 9))
        p.drawText(18, self.height() - 34, 'DRAG TO ORBIT   ·   RIGHT DRAG TO PAN   ·   SCROLL TO ZOOM')
        p.drawText(18, self.height() - 15, f'{len(rendered)} rendered / {len(self.events)} data particles  ·  motion & radius = derived score')
        p.end()
        self.paint_ms.append((time.perf_counter() - start) * 1000)
        self.frame_count += 1

    def mousePressEvent(self, e):
        self.setFocus()
        self.drag = (e.position(), e.button(), e.position())

    def mouseMoveEvent(self, e):
        if not self.drag:
            return
        previous, button, origin = self.drag
        delta = e.position() - previous
        if button == Qt.MouseButton.RightButton:
            self.pan += delta
        else:
            self.yaw += delta.x() / 180
            self.tilt = max(-1.2, min(1.2, self.tilt + delta.y() / 260))
        self.drag = (e.position(), button, origin)
        self.update()

    def mouseReleaseEvent(self, e):
        if self.drag and (e.position() - self.drag[2]).manhattanLength() < 6:
            for point, radius, event in reversed(self.hits):
                if (e.position() - point).manhattanLength() < radius * 1.6:
                    self.selected_id = event['event_id']
                    self.selected.emit(event)
                    self.update()
                    break
        self.drag = None

    def wheelEvent(self, e):
        self.zoom = max(0.35, min(3.0, self.zoom * (1.12 if e.angleDelta().y() > 0 else 1 / 1.12)))
        self.update()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Space:
            self.paused = not self.paused
        elif e.key() == Qt.Key.Key_Left:
            self.yaw -= 0.1
        elif e.key() == Qt.Key.Key_Right:
            self.yaw += 0.1
        elif e.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.zoom = min(3.0, self.zoom * 1.1)
        elif e.key() == Qt.Key.Key_Minus:
            self.zoom = max(0.35, self.zoom / 1.1)
        elif e.key() == Qt.Key.Key_Home:
            self.yaw, self.tilt, self.zoom, self.pan = -0.2, 0.6, 1.0, QPointF(0, 0)
        self.update()
