import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QSizePolicy, QComboBox,
    QPushButton
)
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import (
    QPainter, QPen, QColor, QFont, QFontMetrics
)
from .scope_device import LogicData


# ── Channel Colors ────────────────────────────────────────────
CHANNEL_COLORS = [
    "#00ff88",  # CH0 - green
    "#4488ff",  # CH1 - blue
    "#ff8844",  # CH2 - orange
    "#ff44ff",  # CH3 - pink
    "#44ffff",  # CH4 - cyan
    "#ffff44",  # CH5 - yellow
    "#ff4444",  # CH6 - red
    "#88ff44",  # CH7 - lime
]

CHANNEL_LABELS = ["L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7"]

# Protocol decode labels (placeholder for now)
PROTOCOLS = ["None", "UART", "SPI", "I2C", "CAN"]


# ── Single Channel Waveform Widget ────────────────────────────

class ChannelWidget(QWidget):
    """
    Renders a single digital channel as a logic waveform.
    High = top, Low = bottom, transitions drawn as vertical lines.
    """

    LABEL_WIDTH = 40
    PADDING_V   = 8
    ROW_HEIGHT  = 40

    def __init__(self, channel_index: int, parent=None):
        super().__init__(parent)
        self.channel_index = channel_index
        self.label = CHANNEL_LABELS[channel_index]
        self.color = QColor(CHANNEL_COLORS[channel_index])
        self.data  = None
        self.setFixedHeight(self.ROW_HEIGHT)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

    def set_data(self, samples: np.ndarray):
        self.data = samples
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor("#0a0a0f"))

        # Channel label
        label_font = QFont("Courier New", 9)
        painter.setFont(label_font)
        painter.setPen(QPen(self.color))
        painter.drawText(
            QRect(0, 0, self.LABEL_WIDTH, h),
            Qt.AlignmentFlag.AlignCenter,
            self.label
        )

        # Divider after label
        painter.setPen(QPen(QColor("#111122"), 1))
        painter.drawLine(self.LABEL_WIDTH, 0, self.LABEL_WIDTH, h)

        # Draw waveform if we have data
        if self.data is None or len(self.data) == 0:
            painter.setPen(QPen(QColor("#003322"), 1))
            painter.drawLine(self.LABEL_WIDTH, h // 2, w, h // 2)
            return

        # Waveform drawing area
        draw_x     = self.LABEL_WIDTH + 4
        draw_w     = w - draw_x - 4
        high_y     = self.PADDING_V
        low_y      = h - self.PADDING_V
        num_points = len(self.data)

        pen = QPen(self.color, 1)
        painter.setPen(pen)

        prev_x = draw_x
        prev_y = low_y if self.data[0] == 0 else high_y

        for i in range(1, num_points):
            curr_x = draw_x + int((i / num_points) * draw_w)
            curr_y = low_y if self.data[i] == 0 else high_y

            # Horizontal line
            painter.drawLine(prev_x, prev_y, curr_x, prev_y)

            # Vertical transition line
            if curr_y != prev_y:
                painter.setPen(QPen(self.color.lighter(150), 1))
                painter.drawLine(curr_x, prev_y, curr_x, curr_y)
                painter.setPen(pen)

            prev_x = curr_x
            prev_y = curr_y

        # Draw last horizontal segment
        painter.drawLine(prev_x, prev_y, draw_x + draw_w, prev_y)

        painter.end()


# ── Time Ruler Widget ─────────────────────────────────────────

class TimeRuler(QWidget):
    """Draws a time axis ruler above the logic channels."""

    LABEL_WIDTH = 40
    HEIGHT      = 24

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(self.HEIGHT)
        self.time_axis = None
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

    def set_time_axis(self, time_axis: np.ndarray):
        self.time_axis = time_axis
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        w = self.width()
        h = self.height()

        painter.fillRect(0, 0, w, h, QColor("#050510"))

        if self.time_axis is None or len(self.time_axis) == 0:
            return

        draw_x   = self.LABEL_WIDTH + 4
        draw_w   = w - draw_x - 4
        t_start  = self.time_axis[0]
        t_end    = self.time_axis[-1]
        duration = t_end - t_start

        if duration <= 0:
            return

        # Draw tick marks and labels
        num_ticks = 8
        font = QFont("Courier New", 8)
        painter.setFont(font)
        pen = QPen(QColor("#005533"), 1)
        painter.setPen(pen)

        for i in range(num_ticks + 1):
            t   = t_start + (duration * i / num_ticks)
            x   = draw_x + int((i / num_ticks) * draw_w)

            # Tick
            painter.drawLine(x, h - 6, x, h)

            # Label — auto scale to µs or ms
            if duration < 1e-3:
                label = f"{t * 1e6:.1f}µ"
            elif duration < 1:
                label = f"{t * 1e3:.2f}m"
            else:
                label = f"{t:.3f}s"

            painter.setPen(QPen(QColor("#005533")))
            painter.drawText(x - 14, 0, 32, h - 8,
                           Qt.AlignmentFlag.AlignCenter, label)

        painter.end()


# ── Logic Analyzer Panel ──────────────────────────────────────

class LogicAnalyzerPanel(QWidget):
    """
    Full logic analyzer UI panel showing 8 digital channels
    with time ruler, channel enable toggles, and protocol selector.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.channel_widgets = []
        self.channel_enabled = [True] * 8
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Top controls bar
        layout.addLayout(self._build_controls())

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #111122;")
        layout.addWidget(line)

        # Time ruler
        self.ruler = TimeRuler()
        layout.addWidget(self.ruler)

        # Channel display area in a scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: #0a0a0f; }
            QScrollBar:vertical {
                background: #0a0a0f;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: #003322;
                border-radius: 4px;
            }
        """)

        # Container for channel widgets
        channel_container = QWidget()
        channel_container.setStyleSheet("background: #0a0a0f;")
        channel_layout = QVBoxLayout(channel_container)
        channel_layout.setContentsMargins(0, 0, 0, 0)
        channel_layout.setSpacing(2)

        for i in range(8):
            ch_widget = ChannelWidget(i)
            self.channel_widgets.append(ch_widget)
            channel_layout.addWidget(ch_widget)

        channel_layout.addStretch()
        scroll.setWidget(channel_container)
        layout.addWidget(scroll, stretch=1)

        # Protocol decode bar
        layout.addWidget(self._build_decode_bar())

    def _build_controls(self):
        bar = QHBoxLayout()
        bar.setSpacing(8)

        # Sample rate selector
        bar.addWidget(QLabel("Rate:"))
        self.rate_combo = QComboBox()
        self.rate_combo.addItems([
            "1 MSPS", "2 MSPS", "5 MSPS",
            "10 MSPS", "20 MSPS", "40 MSPS"
        ])
        self.rate_combo.setCurrentIndex(2)
        self.rate_combo.setStyleSheet(
            "QComboBox { background: #0f1f0f; color: #00ff88; "
            "border: 1px solid #00aa55; border-radius: 4px; padding: 4px; }"
        )
        bar.addWidget(self.rate_combo)

        # Sample count
        bar.addWidget(QLabel("Samples:"))
        self.samples_combo = QComboBox()
        self.samples_combo.addItems(["256", "512", "1024", "2048", "4096"])
        self.samples_combo.setCurrentIndex(2)
        self.samples_combo.setStyleSheet(
            "QComboBox { background: #0f1f0f; color: #00ff88; "
            "border: 1px solid #00aa55; border-radius: 4px; padding: 4px; }"
        )
        bar.addWidget(self.samples_combo)

        bar.addStretch()

        # Channel enable toggles
        bar.addWidget(QLabel("CH:"))
        self.ch_buttons = []
        for i in range(8):
            btn = QPushButton(CHANNEL_LABELS[i])
            btn.setCheckable(True)
            btn.setChecked(True)
            btn.setFixedSize(32, 24)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: #0f1f0f;
                    border: 1px solid {CHANNEL_COLORS[i]};
                    border-radius: 4px;
                    color: {CHANNEL_COLORS[i]};
                    font-size: 9px;
                }}
                QPushButton:checked {{
                    background: {CHANNEL_COLORS[i]};
                    color: #0a0a0f;
                }}
            """)
            btn.toggled.connect(
                lambda checked, idx=i: self._toggle_channel(idx, checked)
            )
            self.ch_buttons.append(btn)
            bar.addWidget(btn)

        return bar

    def _build_decode_bar(self):
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: #050510; "
            "border-top: 1px solid #111122; }"
        )
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 4, 8, 4)

        layout.addWidget(QLabel("Protocol Decode:"))

        # Protocol selectors per channel pair
        self.protocol_combos = []
        pairs = ["L0/L1", "L2/L3", "L4/L5", "L6/L7"]
        for pair in pairs:
            layout.addWidget(QLabel(pair + ":"))
            combo = QComboBox()
            combo.addItems(PROTOCOLS)
            combo.setStyleSheet(
                "QComboBox { background: #0f1f0f; color: #00aa55; "
                "border: 1px solid #003322; border-radius: 4px; "
                "padding: 2px; font-size: 10px; }"
            )
            combo.setFixedWidth(80)
            self.protocol_combos.append(combo)
            layout.addWidget(combo)

        layout.addStretch()

        # Decode result label
        self.decode_label = QLabel("No decode active")
        self.decode_label.setStyleSheet(
            "color: #005533; font-size: 10px;"
        )
        layout.addWidget(self.decode_label)

        return frame

    def _toggle_channel(self, index: int, enabled: bool):
        self.channel_enabled[index] = enabled
        self.channel_widgets[index].setVisible(enabled)

    def update_logic(self, data: LogicData):
        """Update all channel displays with new logic data."""
        self.ruler.set_time_axis(data.time_axis)

        for i in range(min(8, data.channels.shape[0])):
            if self.channel_enabled[i]:
                self.channel_widgets[i].set_data(data.channels[i])

    def get_sample_rate(self) -> float:
        rate_map = {
            0: 1e6, 1: 2e6, 2: 5e6,
            3: 10e6, 4: 20e6, 5: 40e6
        }
        return rate_map.get(self.rate_combo.currentIndex(), 5e6)

    def get_num_samples(self) -> int:
        samples_map = {
            0: 256, 1: 512, 2: 1024,
            3: 2048, 4: 4096
        }
        return samples_map.get(self.samples_combo.currentIndex(), 1024)