import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QFrame, QTabWidget
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import QPointF, QMargins

from .scope_device import ScopeDevice, WaveformData
from .mock_device import MockScopeDevice
from .logic_view import LogicAnalyzerPanel


# ── Waveform Display Widget ───────────────────────────────────

class WaveformView(QChartView):
    """Custom chart widget for displaying oscilloscope waveforms."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.chart = QChart()
        self.chart.setBackgroundBrush(QColor("#0a0a0f"))
        self.chart.setTitleBrush(QColor("#00ff88"))
        self.chart.legend().setLabelColor(QColor("#00ff88"))
        self.chart.setMargins(QMargins(5, 5, 5, 5))

        # Channel A series
        self.series_a = QLineSeries()
        self.series_a.setName("CH A")
        pen_a = self.series_a.pen()
        pen_a.setColor(QColor("#00ff88"))
        pen_a.setWidth(1)
        self.series_a.setPen(pen_a)

        # Channel B series
        self.series_b = QLineSeries()
        self.series_b.setName("CH B")
        pen_b = self.series_b.pen()
        pen_b.setColor(QColor("#4488ff"))
        pen_b.setWidth(1)
        self.series_b.setPen(pen_b)

        # Axes
        self.axis_x = QValueAxis()
        self.axis_x.setTitleText("Time (ms)")
        self.axis_x.setLabelFormat("%.2f")
        self.axis_x.setLabelsColor(QColor("#005533"))
        self.axis_x.setTitleBrush(QColor("#005533"))
        self.axis_x.setGridLineColor(QColor("#111122"))

        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("Voltage (V)")
        self.axis_y.setLabelFormat("%.1f")
        self.axis_y.setLabelsColor(QColor("#005533"))
        self.axis_y.setTitleBrush(QColor("#005533"))
        self.axis_y.setGridLineColor(QColor("#111122"))
        self.axis_y.setRange(-5, 5)

        self.chart.addSeries(self.series_a)
        self.chart.addSeries(self.series_b)
        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        self.series_a.attachAxis(self.axis_x)
        self.series_a.attachAxis(self.axis_y)
        self.series_b.attachAxis(self.axis_x)
        self.series_b.attachAxis(self.axis_y)

        self.setChart(self.chart)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)

    def update_waveform(self, data: WaveformData, show_b: bool = False):
        time_ms = data.time_axis * 1000

        points_a = [QPointF(t, v) for t, v in zip(time_ms, data.channel_a)]
        self.series_a.replace(points_a)

        if show_b and data.channel_b is not None:
            points_b = [QPointF(t, v) for t, v in zip(time_ms, data.channel_b)]
            self.series_b.replace(points_b)
            self.series_b.setVisible(True)
        else:
            self.series_b.setVisible(False)

        if len(time_ms) > 0:
            self.axis_x.setRange(time_ms[0], time_ms[-1])

        all_data = list(data.channel_a)
        if show_b and data.channel_b is not None:
            all_data += list(data.channel_b)
        if all_data:
            y_min = min(all_data) * 1.2
            y_max = max(all_data) * 1.2
            self.axis_y.setRange(y_min, y_max)


# ── Scope Module ──────────────────────────────────────────────

class ScopeModule(QWidget):
    """
    Scope / Logic Analyzer module UI panel.
    Contains tabbed interface for Oscilloscope and Logic Analyzer.
    """

    def __init__(self, shell, device: ScopeDevice = None):
        super().__init__()
        self.shell          = shell
        self.device         = device or MockScopeDevice()
        self.running        = False
        self.show_channel_b = False
        self.logic_panel    = None

        self._build_ui()
        self._connect_device()

        self.timer = QTimer()
        self.timer.timeout.connect(self._capture_and_update)

    # ── UI Construction ───────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        layout.addLayout(self._build_top_bar())

        self.info_label = QLabel("Connecting...")
        self.info_label.setStyleSheet("color: #005533; font-size: 11px;")
        layout.addWidget(self.info_label)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #003322;
                background: #0a0a0f;
            }
            QTabBar::tab {
                background: #0f1f0f;
                color: #005533;
                border: 1px solid #003322;
                padding: 6px 16px;
                font-family: 'Courier New';
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background: #1a3a1a;
                color: #00ff88;
                border-bottom: 2px solid #00ff88;
            }
            QTabBar::tab:hover {
                color: #00ff88;
            }
        """)

        # Oscilloscope tab
        scope_tab = QWidget()
        scope_layout = QVBoxLayout(scope_tab)
        scope_layout.setContentsMargins(0, 8, 0, 0)
        scope_layout.setSpacing(8)

        self.waveform_view = WaveformView()
        self.waveform_view.setMinimumHeight(200)
        scope_layout.addWidget(self.waveform_view, stretch=1)
        scope_layout.addLayout(self._build_controls())
        scope_layout.addWidget(self._build_measurements())

        # Logic analyzer tab
        self.logic_panel = LogicAnalyzerPanel()

        self.tabs.addTab(scope_tab,        "📈  Oscilloscope")
        self.tabs.addTab(self.logic_panel, "📟  Logic Analyzer")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self.tabs, stretch=1)

    def _build_top_bar(self):
        bar = QHBoxLayout()

        back_btn = QPushButton("◀  Home")
        back_btn.setObjectName("back_btn")
        back_btn.setFixedWidth(100)
        back_btn.clicked.connect(self._on_back)

        title = QLabel("SCOPE / LOGIC")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.run_btn = QPushButton("▶  RUN")
        self.run_btn.setObjectName("module_btn")
        self.run_btn.setFixedWidth(100)
        self.run_btn.clicked.connect(self._toggle_run)

        bar.addWidget(back_btn)
        bar.addWidget(title, stretch=1)
        bar.addWidget(self.run_btn)
        return bar

    def _build_controls(self):
        controls = QHBoxLayout()
        controls.setSpacing(12)

        controls.addWidget(QLabel("Timebase:"))
        self.timebase_combo = QComboBox()
        self.timebase_combo.addItems([
            "1 µs", "5 µs", "10 µs", "50 µs",
            "100 µs", "500 µs", "1 ms", "5 ms"
        ])
        self.timebase_combo.setCurrentIndex(6)
        self.timebase_combo.setStyleSheet(
            "QComboBox { background: #0f1f0f; color: #00ff88; "
            "border: 1px solid #00aa55; border-radius: 4px; padding: 4px; }"
        )
        controls.addWidget(self.timebase_combo)

        controls.addWidget(QLabel("Range:"))
        self.range_combo = QComboBox()
        self.range_combo.addItems(["±1V", "±2V", "±5V", "±10V"])
        self.range_combo.setCurrentIndex(2)
        self.range_combo.setStyleSheet(
            "QComboBox { background: #0f1f0f; color: #00ff88; "
            "border: 1px solid #00aa55; border-radius: 4px; padding: 4px; }"
        )
        controls.addWidget(self.range_combo)

        self.chb_btn = QPushButton("CH B: OFF")
        self.chb_btn.setObjectName("back_btn")
        self.chb_btn.setFixedWidth(90)
        self.chb_btn.clicked.connect(self._toggle_channel_b)
        controls.addWidget(self.chb_btn)

        if isinstance(self.device, MockScopeDevice):
            controls.addWidget(QLabel("Signal:"))
            self.wave_combo = QComboBox()
            self.wave_combo.addItems(["Sine", "Square", "Triangle"])
            self.wave_combo.setStyleSheet(
                "QComboBox { background: #0f1f0f; color: #00ff88; "
                "border: 1px solid #00aa55; border-radius: 4px; padding: 4px; }"
            )
            self.wave_combo.currentTextChanged.connect(
                lambda t: self.device.set_waveform_type(t.lower())
            )
            controls.addWidget(self.wave_combo)

        controls.addStretch()
        return controls

    def _build_measurements(self):
        frame = QFrame()
        frame.setObjectName("divider")
        frame.setFrameShape(QFrame.Shape.HLine)
        frame.setFixedHeight(1)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 4, 0, 0)

        self.meas_labels = {}
        for name in ["Freq", "Vpp", "Vmax", "Vmin", "Vrms"]:
            label = QLabel(f"{name}: --")
            label.setStyleSheet("color: #00aa55; font-size: 11px;")
            self.meas_labels[name] = label
            layout.addWidget(label)

        layout.addStretch()

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)
        container_layout.addWidget(frame)
        container_layout.addLayout(layout)
        return container

    # ── Device Connection ─────────────────────────────────────

    def _connect_device(self):
        if self.device.connect():
            info = self.device.get_device_info()
            self.info_label.setText(
                f"● {info['name']}  |  "
                f"BW: {int(info['bandwidth']/1e6)} MHz  |  "
                f"Max Rate: {int(info['max_sample_rate']/1e6)} MSPS  |  "
                f"CH: {info['channels']} analog + "
                f"{info['logic_channels']} logic"
            )
            self.info_label.setStyleSheet(
                "color: #00ff88; font-size: 11px;"
            )
        else:
            self.info_label.setText("● Device not found")
            self.info_label.setStyleSheet(
                "color: #ff4444; font-size: 11px;"
            )

    # ── Capture & Display ─────────────────────────────────────

    def _capture_and_update(self):
        if self.tabs.currentIndex() == 0:
            self._capture_scope()
        else:
            self._capture_logic()

    def _capture_scope(self):
        try:
            timebase_map = {
                0: (1e6,  1024),
                1: (1e6,  5120),
                2: (1e6,  10240),
                3: (500e3, 25000),
                4: (100e3, 10000),
                5: (20e3,  10000),
                6: (10e3,  10000),
                7: (2e3,   10000),
            }
            rate, samples = timebase_map.get(
                self.timebase_combo.currentIndex(), (10e3, 1024)
            )
            range_map = {0: 1.0, 1: 2.0, 2: 5.0, 3: 10.0}
            voltage_range = range_map.get(
                self.range_combo.currentIndex(), 5.0
            )
            data = self.device.capture_waveform(
                sample_rate=rate,
                num_samples=min(samples, 1024),
                voltage_range=voltage_range,
                channel_b=self.show_channel_b
            )
            self.waveform_view.update_waveform(data, self.show_channel_b)
            self._update_measurements(data)
        except Exception as e:
            print(f"[ScopeModule] Scope error: {e}")
            self._stop()

    def _capture_logic(self):
        try:
            rate    = self.logic_panel.get_sample_rate()
            samples = self.logic_panel.get_num_samples()
            data    = self.device.capture_logic(
                sample_rate=rate,
                num_samples=samples
            )
            self.logic_panel.update_logic(data)
        except Exception as e:
            print(f"[ScopeModule] Logic error: {e}")
            self._stop()

    def _update_measurements(self, data: WaveformData):
        ch = data.channel_a
        if len(ch) == 0:
            return

        vmax = float(np.max(ch))
        vmin = float(np.min(ch))
        vpp  = vmax - vmin
        vrms = float(np.sqrt(np.mean(ch ** 2)))

        crossings = np.where(np.diff(np.signbit(ch)))[0]
        if len(crossings) >= 2:
            period = (
                data.time_axis[crossings[-1]] -
                data.time_axis[crossings[0]]
            ) / (len(crossings) - 1) * 2
            freq = 1.0 / period if period > 0 else 0
            self.meas_labels["Freq"].setText(
                f"Freq: {freq:.1f} Hz" if freq < 1000
                else f"Freq: {freq/1000:.2f} kHz"
            )
        else:
            self.meas_labels["Freq"].setText("Freq: --")

        self.meas_labels["Vpp"].setText(f"Vpp:  {vpp:.2f}V")
        self.meas_labels["Vmax"].setText(f"Vmax: {vmax:.2f}V")
        self.meas_labels["Vmin"].setText(f"Vmin: {vmin:.2f}V")
        self.meas_labels["Vrms"].setText(f"Vrms: {vrms:.2f}V")

    # ── Button Handlers ───────────────────────────────────────

    def _toggle_run(self):
        if self.running:
            self._stop()
        else:
            self._start()

    def _start(self):
        self.running = True
        self.run_btn.setText("■  STOP")
        if self.tabs.currentIndex() == 0:
            self.timer.start(100)
        else:
            self.timer.start(200)

    def _stop(self):
        self.running = False
        self.run_btn.setText("▶  RUN")
        self.timer.stop()

    def _toggle_channel_b(self):
        self.show_channel_b = not self.show_channel_b
        self.chb_btn.setText(
            "CH B: ON" if self.show_channel_b else "CH B: OFF"
        )

    def _on_tab_changed(self, index: int):
        self._stop()

    def _on_back(self):
        self._stop()
        self.shell.show_screen("home")