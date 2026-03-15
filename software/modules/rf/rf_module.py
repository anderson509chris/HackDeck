import os
import numpy as np
from datetime import datetime
from queue import Queue, Empty

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSlider, QComboBox, QFrame, QSizePolicy,
    QGraphicsOpacityEffect
)
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation,
    QEasingCurve, Signal, QThread, QObject
)
from PySide6.QtGui import (
    QPainter, QColor, QFont, QLinearGradient
)

from .sdr_device import SDRDevice, SDRConfig
from .mock_sdr import MockSDRDevice
from .waterfall_widget import WaterfallWidget, SpectrumWidget, ColorScaleWidget


# ── FFT Worker ────────────────────────────────────────────────

class FFTWorker(QObject):
    """
    Runs in a separate thread.
    Receives FFT data from SDR device and emits to UI thread via signal.
    This keeps the UI responsive while streaming high rate FFT data.
    """
    fft_ready = Signal(object)  # emits np.ndarray

    def __init__(self, device: SDRDevice):
        super().__init__()
        self.device = device
        self._queue = Queue(maxsize=32)

    def _on_fft(self, fft_data: np.ndarray):
        """Called from SDR thread — puts data in queue."""
        try:
            self._queue.put_nowait(fft_data.copy())
        except Exception:
            pass  # Drop frame if queue full

    def start(self):
        self.device.start_stream(self._on_fft)

    def stop(self):
        self.device.stop_stream()

    def get_fft(self) -> np.ndarray:
        """Called from UI timer — gets latest FFT from queue."""
        try:
            return self._queue.get_nowait()
        except Empty:
            return None


# ── Controls Panel ────────────────────────────────────────────

class ControlsPanel(QWidget):
    """
    Slide-up controls panel.
    Hidden by default, revealed by swiping up from bottom.
    """

    # Signals emitted when user changes settings
    freq_changed    = Signal(float)
    gain_changed    = Signal(float)
    bw_changed      = Signal(float)
    mode_changed    = Signal(str)
    record_toggled  = Signal(bool)
    replay_clicked  = Signal()
    scan_clicked    = Signal()
    fm_toggled      = Signal(bool)

    PANEL_HEIGHT = 220

    def __init__(self, config: SDRConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setFixedHeight(self.PANEL_HEIGHT)
        self._build_ui()
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(5, 5, 20, 230);
                border-top: 1px solid #003322;
            }
            QLabel {
                color: #00aa55;
                font-size: 11px;
                background: transparent;
                border: none;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #003322;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #00ff88;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #00ff88;
                border-radius: 2px;
            }
        """)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)

        # Drag handle indicator
        handle = QLabel("▲  CONTROLS  ▲")
        handle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        handle.setStyleSheet(
            "color: #005533; font-size: 10px; "
            "background: transparent; border: none;"
        )
        layout.addWidget(handle)

        # Frequency row
        freq_row = QHBoxLayout()
        freq_row.addWidget(QLabel("FREQ:"))

        self.freq_label = QLabel(
            f"{self.config.center_freq/1e6:.3f} MHz"
        )
        self.freq_label.setStyleSheet(
            "color: #00ff88; font-size: 14px; "
            "font-weight: bold; background: transparent; border: none;"
        )
        freq_row.addWidget(self.freq_label)
        freq_row.addStretch()

        # Frequency step buttons
        for step_mhz in [0.1, 1, 10, 100]:
            btn_down = QPushButton(f"◀{step_mhz}")
            btn_up   = QPushButton(f"{step_mhz}▶")
            for btn in (btn_down, btn_up):
                btn.setFixedHeight(28)
                btn.setStyleSheet(
                    "QPushButton { background: #0f1f0f; "
                    "border: 1px solid #003322; border-radius: 4px; "
                    "color: #00aa55; font-size: 10px; padding: 2px 6px; }"
                    "QPushButton:pressed { background: #00ff88; "
                    "color: #000000; }"
                )
            step_hz = step_mhz * 1e6
            btn_down.clicked.connect(
                lambda _, s=step_hz: self._adjust_freq(-s)
            )
            btn_up.clicked.connect(
                lambda _, s=step_hz: self._adjust_freq(s)
            )
            freq_row.addWidget(btn_down)
            freq_row.addWidget(btn_up)

        layout.addLayout(freq_row)

        # Gain row
        gain_row = QHBoxLayout()
        gain_row.addWidget(QLabel("GAIN:"))
        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_slider.setRange(0, 62)
        self.gain_slider.setValue(int(self.config.gain))
        self.gain_slider.valueChanged.connect(self._on_gain_changed)
        self.gain_label = QLabel(f"{self.config.gain:.0f} dB")
        self.gain_label.setFixedWidth(50)
        self.gain_label.setStyleSheet(
            "color: #00ff88; background: transparent; border: none;"
        )
        gain_row.addWidget(self.gain_slider, stretch=1)
        gain_row.addWidget(self.gain_label)
        layout.addLayout(gain_row)

        # Bandwidth + Mode row
        bw_mode_row = QHBoxLayout()
        bw_mode_row.addWidget(QLabel("BW:"))

        self.bw_combo = QComboBox()
        self.bw_combo.addItems([
            "200 kHz", "500 kHz", "1 MHz", "2 MHz",
            "5 MHz", "10 MHz", "20 MHz"
        ])
        self.bw_combo.setCurrentIndex(3)  # 2 MHz default
        self.bw_combo.currentIndexChanged.connect(self._on_bw_changed)
        self.bw_combo.setStyleSheet(
            "QComboBox { background: #0f1f0f; color: #00ff88; "
            "border: 1px solid #003322; border-radius: 4px; "
            "padding: 4px; }"
        )
        bw_mode_row.addWidget(self.bw_combo)
        bw_mode_row.addSpacing(16)
        bw_mode_row.addWidget(QLabel("MODE:"))

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Spectrum", "FM Radio", "Scanner"])
        self.mode_combo.currentTextChanged.connect(self.mode_changed)
        self.mode_combo.setStyleSheet(
            "QComboBox { background: #0f1f0f; color: #00ff88; "
            "border: 1px solid #003322; border-radius: 4px; "
            "padding: 4px; }"
        )
        bw_mode_row.addWidget(self.mode_combo)
        bw_mode_row.addStretch()
        layout.addLayout(bw_mode_row)

        # Action buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.record_btn = self._make_action_btn("⬤  RECORD", "#ff4444")
        self.record_btn.setCheckable(True)
        self.record_btn.toggled.connect(self.record_toggled)
        btn_row.addWidget(self.record_btn)

        self.replay_btn = self._make_action_btn("▶  REPLAY", "#4488ff")
        self.replay_btn.clicked.connect(self.replay_clicked)
        btn_row.addWidget(self.replay_btn)

        self.scan_btn = self._make_action_btn("⟳  SCAN", "#ffaa00")
        self.scan_btn.clicked.connect(self.scan_clicked)
        btn_row.addWidget(self.scan_btn)

        self.fm_btn = self._make_action_btn("FM  RADIO", "#aa44ff")
        self.fm_btn.setCheckable(True)
        self.fm_btn.toggled.connect(self.fm_toggled)
        btn_row.addWidget(self.fm_btn)

        layout.addLayout(btn_row)

    def _make_action_btn(self, label: str, color: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedHeight(32)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: #0a0a15;
                border: 1px solid {color};
                border-radius: 6px;
                color: {color};
                font-size: 11px;
                padding: 4px 8px;
            }}
            QPushButton:checked, QPushButton:pressed {{
                background: {color};
                color: #000000;
            }}
        """)
        return btn

    def _adjust_freq(self, delta_hz: float):
        self.config.center_freq += delta_hz
        self.config.center_freq = max(1e6,
            min(6e9, self.config.center_freq))
        self.freq_label.setText(
            f"{self.config.center_freq/1e6:.3f} MHz"
        )
        self.freq_changed.emit(self.config.center_freq)

    def _on_gain_changed(self, value: int):
        self.config.gain = float(value)
        self.gain_label.setText(f"{value} dB")
        self.gain_changed.emit(float(value))

    def _on_bw_changed(self, index: int):
        bw_map = {
            0: 200e3, 1: 500e3, 2: 1e6, 3: 2e6,
            4: 5e6,   5: 10e6,  6: 20e6
        }
        bw = bw_map.get(index, 2e6)
        self.config.bandwidth = bw
        self.bw_changed.emit(bw)

    def update_freq_display(self, freq: float):
        self.freq_label.setText(f"{freq/1e6:.3f} MHz")


# ── RF Module ─────────────────────────────────────────────────

class RFModule(QWidget):
    """
    RF / SDR module — full screen waterfall with slide-up controls.
    Primary interface for spectrum analysis, FM radio,
    signal recording/replay and frequency scanning.
    """

    def __init__(self, shell, device: SDRDevice = None):
        super().__init__()
        self.shell          = shell
        self.device         = device or MockSDRDevice()
        self.config         = SDRConfig()
        self.worker         = FFTWorker(self.device)
        self.running        = False
        self.controls_visible = False
        self._swipe_start_y = None

        self._build_ui()
        self._connect_device()
        self._connect_signals()

        # UI update timer — polls FFT queue and updates display
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self._update_display)

    # ── UI Construction ───────────────────────────────────────

    def _build_ui(self):
        # Main layout — no margins for full screen feel
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top chrome bar — always visible, slim
        layout.addWidget(self._build_top_bar())

        # Main display area
        display_container = QWidget()
        display_layout    = QHBoxLayout(display_container)
        display_layout.setContentsMargins(0, 0, 0, 0)
        display_layout.setSpacing(0)

        # Left side — waterfall + spectrum stacked
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.waterfall = WaterfallWidget()
        self.spectrum  = SpectrumWidget()

        left_layout.addWidget(self.waterfall, stretch=4)
        left_layout.addWidget(self.spectrum,  stretch=1)

        # Right side — color scale
        self.color_scale = ColorScaleWidget()

        display_layout.addWidget(left_widget,      stretch=1)
        display_layout.addWidget(self.color_scale)

        layout.addWidget(display_container, stretch=1)

        # Controls panel — overlays bottom of screen
        self.controls = ControlsPanel(self.config, self)
        self.controls.hide()

        # Status bar at very bottom
        layout.addWidget(self._build_status_bar())

    def _build_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(40)
        bar.setStyleSheet(
            "background-color: rgba(5, 5, 16, 220); "
            "border-bottom: 1px solid #003322;"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 0, 8, 0)

        back_btn = QPushButton("◀  Home")
        back_btn.setObjectName("back_btn")
        back_btn.setFixedWidth(90)
        back_btn.clicked.connect(self._on_back)

        self.title_label = QLabel("RF / SDR")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(
            "color: #00ff88; font-size: 16px; "
            "font-weight: bold; font-family: 'Courier New';"
            "background: transparent;"
        )

        self.run_btn = QPushButton("▶  RUN")
        self.run_btn.setObjectName("module_btn")
        self.run_btn.setFixedWidth(90)
        self.run_btn.clicked.connect(self._toggle_run)

        # Frequency display in top bar
        self.freq_display = QLabel("100.000 MHz")
        self.freq_display.setStyleSheet(
            "color: #00ff88; font-size: 13px; "
            "font-family: 'Courier New';"
            "background: transparent;"
        )
        self.freq_display.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(back_btn)
        layout.addWidget(self.title_label)
        layout.addWidget(self.freq_display, stretch=1)
        layout.addWidget(self.run_btn)
        return bar

    def _build_status_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(24)
        bar.setStyleSheet(
            "background-color: #050510; "
            "border-top: 1px solid #003322;"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 0, 8, 0)

        self.status_label = QLabel(
            "● Simulated HackRF  |  Swipe up for controls"
        )
        self.status_label.setStyleSheet(
            "color: #005533; font-size: 10px; background: transparent;"
        )

        self.rec_label = QLabel("")
        self.rec_label.setStyleSheet(
            "color: #ff4444; font-size: 10px; background: transparent;"
        )

        layout.addWidget(self.status_label, stretch=1)
        layout.addWidget(self.rec_label)
        return bar

    # ── Device Connection ─────────────────────────────────────

    def _connect_device(self):
        if self.device.connect():
            info = self.device.get_device_info()
            self.status_label.setText(
                f"● {info['name']}  |  Swipe up for controls"
            )
            self.device.set_config(self.config)
        else:
            self.status_label.setText("● Device not found")

    def _connect_signals(self):
        self.controls.freq_changed.connect(self._on_freq_changed)
        self.controls.gain_changed.connect(self._on_gain_changed)
        self.controls.bw_changed.connect(self._on_bw_changed)
        self.controls.mode_changed.connect(self._on_mode_changed)
        self.controls.record_toggled.connect(self._on_record_toggled)
        self.controls.replay_clicked.connect(self._on_replay)
        self.controls.scan_clicked.connect(self._on_scan)
        self.controls.fm_toggled.connect(self._on_fm_toggled)

    # ── Swipe Gesture ─────────────────────────────────────────

    def mousePressEvent(self, event):
        self._swipe_start_y = event.position().y()

    def mouseReleaseEvent(self, event):
        if self._swipe_start_y is None:
            return
        delta_y = event.position().y() - self._swipe_start_y
        # Swipe up — show controls
        if delta_y < -40 and not self.controls_visible:
            self._show_controls()
        # Swipe down or tap on waterfall — hide controls
        elif delta_y > 20 and self.controls_visible:
            self._hide_controls()
        elif abs(delta_y) < 10 and self.controls_visible:
            self._hide_controls()
        self._swipe_start_y = None

    def _show_controls(self):
        self.controls_visible = True
        self.controls.setParent(self)
        self.controls.resize(self.width(), ControlsPanel.PANEL_HEIGHT)
        self.controls.move(
            0, self.height() - ControlsPanel.PANEL_HEIGHT - 24
        )
        self.controls.show()
        self.controls.raise_()

        # Animate slide up
        self.anim = QPropertyAnimation(self.controls, b"pos")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setStartValue(
            self.controls.pos().__class__(
                0, self.height()
            )
        )
        self.anim.setEndValue(self.controls.pos())
        self.anim.start()

    def _hide_controls(self):
        self.controls_visible = False

        # Animate slide down
        self.anim = QPropertyAnimation(self.controls, b"pos")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.anim.setStartValue(self.controls.pos())
        self.anim.setEndValue(
            self.controls.pos().__class__(
                0, self.height()
            )
        )
        self.anim.finished.connect(self.controls.hide)
        self.anim.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.controls_visible:
            self.controls.resize(
                self.width(), ControlsPanel.PANEL_HEIGHT
            )
            self.controls.move(
                0,
                self.height() - ControlsPanel.PANEL_HEIGHT - 24
            )

    # ── Run / Stop ────────────────────────────────────────────

    def _toggle_run(self):
        if self.running:
            self._stop()
        else:
            self._start()

    def _start(self):
        self.running = True
        self.run_btn.setText("■  STOP")
        self.worker.start()
        self.ui_timer.start(66)  # ~15fps UI updates

    def _stop(self):
        self.running = False
        self.run_btn.setText("▶  RUN")
        self.worker.stop()
        self.ui_timer.stop()

    # ── Display Update ────────────────────────────────────────

    def _update_display(self):
        """Called by UI timer — pulls FFT data and updates widgets."""
        fft_data = self.worker.get_fft()
        if fft_data is not None:
            self.waterfall.add_fft_row(fft_data)
            self.spectrum.update_fft(
                fft_data,
                self.config.center_freq,
                self.config.bandwidth
            )

    # ── Control Handlers ──────────────────────────────────────

    def _on_freq_changed(self, freq: float):
        self.config.center_freq = freq
        self.freq_display.setText(f"{freq/1e6:.3f} MHz")
        self.waterfall.set_parameters(
            freq, self.config.bandwidth, self.config.fft_size
        )
        try:
            self.device.set_config(self.config)
        except NotImplementedError:
            pass

    def _on_gain_changed(self, gain: float):
        self.config.gain = gain
        try:
            self.device.set_config(self.config)
        except NotImplementedError:
            pass

    def _on_bw_changed(self, bw: float):
        self.config.bandwidth = bw
        self.waterfall.set_parameters(
            self.config.center_freq, bw, self.config.fft_size
        )
        self.spectrum.bandwidth = bw
        try:
            self.device.set_config(self.config)
        except NotImplementedError:
            pass

    def _on_mode_changed(self, mode: str):
        self.title_label.setText(f"RF / {mode.upper()}")

    def _on_record_toggled(self, recording: bool):
        if recording:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath  = os.path.expanduser(
                f"~/HackDeck/captures/iq_{timestamp}.bin"
            )
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            try:
                self.device.start_recording(filepath)
                self.rec_label.setText("⬤ REC")
            except NotImplementedError:
                self.rec_label.setText("⬤ REC (sim)")
        else:
            try:
                self.device.stop_recording()
            except NotImplementedError:
                pass
            self.rec_label.setText("")

    def _on_replay(self):
        print("[RFModule] Replay clicked — file picker TODO")

    def _on_scan(self):
        print("[RFModule] Scan clicked — scanner UI TODO")

    def _on_fm_toggled(self, active: bool):
        if active:
            try:
                self.device.start_fm_receiver(
                    self.config.center_freq,
                    lambda audio: None
                )
                self.title_label.setText("RF / FM RADIO")
            except NotImplementedError:
                self.title_label.setText("RF / FM (sim)")
        else:
            try:
                self.device.stop_fm_receiver()
            except NotImplementedError:
                pass
            self.title_label.setText("RF / SDR")

    def _on_back(self):
        self._stop()
        self.shell.show_screen("home")