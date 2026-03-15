import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, QRect, QPoint, QSize
from PySide6.QtGui import (
    QPainter, QColor, QImage, QPixmap,
    QPen, QFont, QLinearGradient
)


# ── Colormap ──────────────────────────────────────────────────
# Maps 0.0-1.0 signal strength to RGB color
# Black → Purple → Blue → Cyan → Green → Yellow → Red → White
COLORMAP = [
    (0.00, (0,   0,   0  )),   # Black    - noise floor
    (0.15, (32,  0,   64 )),   # Purple
    (0.30, (0,   0,   180)),   # Blue
    (0.45, (0,   180, 180)),   # Cyan
    (0.60, (0,   180, 0  )),   # Green
    (0.75, (180, 180, 0  )),   # Yellow
    (0.88, (220, 80,  0  )),   # Orange
    (1.00, (255, 255, 255)),   # White    - strongest signal
]


def magnitude_to_color(value: float) -> tuple:
    """Map a 0.0-1.0 magnitude value to an RGB tuple using the colormap."""
    value = max(0.0, min(1.0, value))
    for i in range(len(COLORMAP) - 1):
        t0, c0 = COLORMAP[i]
        t1, c1 = COLORMAP[i + 1]
        if t0 <= value <= t1:
            # Linear interpolation between colors
            ratio = (value - t0) / (t1 - t0)
            r = int(c0[0] + ratio * (c1[0] - c0[0]))
            g = int(c0[1] + ratio * (c1[1] - c0[1]))
            b = int(c0[2] + ratio * (c1[2] - c0[2]))
            return (r, g, b)
    return COLORMAP[-1][1]


def build_colormap_lut(size: int = 256) -> np.ndarray:
    """Build a lookup table of RGB values for fast colormap application."""
    lut = np.zeros((size, 3), dtype=np.uint8)
    for i in range(size):
        r, g, b = magnitude_to_color(i / (size - 1))
        lut[i] = [r, g, b]
    return lut


# Pre-build the LUT once at module load
COLOR_LUT = build_colormap_lut(256)


# ── Spectrum Widget ───────────────────────────────────────────

class SpectrumWidget(QWidget):
    """
    Draws a single FFT spectrum line graph.
    Shows the most recent FFT snapshot as a filled line graph.
    Sits below the waterfall display.
    """

    LABEL_HEIGHT = 20
    PADDING      = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fft_data    = None
        self.center_freq = 100e6    # Hz
        self.bandwidth   = 2e6      # Hz
        self.ref_level   = -20      # dBFS top of display
        self.range_db    = 80       # dB range shown
        self.setMinimumHeight(80)
        self.setMaximumHeight(120)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

    def update_fft(self, fft_data: np.ndarray,
                   center_freq: float, bandwidth: float):
        self.fft_data    = fft_data
        self.center_freq = center_freq
        self.bandwidth   = bandwidth
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor("#050510"))

        draw_h = h - self.LABEL_HEIGHT
        draw_w = w - self.PADDING * 2

        # Draw grid lines
        painter.setPen(QPen(QColor("#111122"), 1))
        for i in range(5):
            y = int(self.PADDING + (i / 4) * (draw_h - self.PADDING * 2))
            painter.drawLine(self.PADDING, y, w - self.PADDING, y)

        # Draw dB labels on right side
        font = QFont("Courier New", 8)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#004422")))
        for i in range(5):
            db = self.ref_level - (i / 4) * self.range_db
            y  = int(self.PADDING + (i / 4) * (draw_h - self.PADDING * 2))
            painter.drawText(w - 36, y + 4, f"{db:.0f}")

        # Draw frequency labels at bottom
        freq_start = (self.center_freq - self.bandwidth / 2) / 1e6
        freq_end   = (self.center_freq + self.bandwidth / 2) / 1e6
        for i in range(5):
            freq = freq_start + (i / 4) * (freq_end - freq_start)
            x    = int(self.PADDING + (i / 4) * draw_w)
            painter.drawText(x - 20, h - 4, f"{freq:.2f}")

        if self.fft_data is None or len(self.fft_data) == 0:
            return

        # Normalize FFT data to 0.0-1.0 range for display
        data      = np.array(self.fft_data, dtype=np.float32)
        db_values = 20 * np.log10(np.maximum(data, 1e-10))
        normalized = np.clip(
            (db_values - (self.ref_level - self.range_db)) / self.range_db,
            0.0, 1.0
        )

        # Build polygon points for filled spectrum
        num_points = len(normalized)
        points_x   = [
            int(self.PADDING + (i / (num_points - 1)) * draw_w)
            for i in range(num_points)
        ]
        points_y = [
            int(draw_h - normalized[i] * (draw_h - self.PADDING * 2))
            for i in range(num_points)
        ]

        # Draw filled area
        from PySide6.QtGui import QPolygon
        from PySide6.QtCore import QPoint

        # Fill gradient
        gradient = QLinearGradient(0, 0, 0, draw_h)
        gradient.setColorAt(0.0, QColor(0, 200, 100, 180))
        gradient.setColorAt(1.0, QColor(0, 80,  40,  40))

        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.moveTo(self.PADDING, draw_h)
        for x, y in zip(points_x, points_y):
            path.lineTo(x, y)
        path.lineTo(w - self.PADDING, draw_h)
        path.closeSubpath()

        painter.fillPath(path, gradient)

        # Draw spectrum line on top
        pen = QPen(QColor("#00ff88"), 1)
        painter.setPen(pen)
        for i in range(1, num_points):
            painter.drawLine(
                points_x[i-1], points_y[i-1],
                points_x[i],   points_y[i]
            )

        painter.end()


# ── Waterfall Widget ──────────────────────────────────────────

class WaterfallWidget(QWidget):
    """
    Scrolling waterfall display.
    Each new FFT row is added at the top and older rows scroll down.
    Color represents signal strength using the SDR colormap.
    """

    LABEL_WIDTH  = 0
    FREQ_HEIGHT  = 20

    def __init__(self, parent=None):
        super().__init__(parent)
        self.center_freq  = 100e6
        self.bandwidth    = 2e6
        self.ref_level    = -20
        self.range_db     = 80
        self.fft_size     = 1024
        self._history     = None    # numpy array of waterfall rows
        self._pixmap      = None    # cached rendered pixmap
        self._dirty       = True    # needs re-render
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

    def set_parameters(self, center_freq: float,
                       bandwidth: float, fft_size: int = 1024):
        self.center_freq = center_freq
        self.bandwidth   = bandwidth
        self.fft_size    = fft_size
        self._history    = None
        self._dirty      = True
        self.update()

    def add_fft_row(self, fft_data: np.ndarray):
        """Add a new FFT row to the top of the waterfall."""
        h = max(1, self.height() - self.FREQ_HEIGHT)

        # Initialize history buffer on first call or resize
        if (self._history is None or
                self._history.shape != (h, len(fft_data))):
            self._history = np.zeros((h, len(fft_data)),
                                     dtype=np.float32)

        # Scroll down — shift all rows down by one
        self._history = np.roll(self._history, 1, axis=0)

        # Normalize new row to 0-255
        data      = np.array(fft_data, dtype=np.float32)
        db_values = 20 * np.log10(np.maximum(data, 1e-10))
        normalized = np.clip(
            (db_values - (self.ref_level - self.range_db)) / self.range_db,
            0.0, 1.0
        ) * 255

        self._history[0] = normalized.astype(np.float32)
        self._dirty      = True
        self.update()

    def _render_pixmap(self):
        """Render the waterfall history to a QPixmap for display."""
        if self._history is None:
            return

        h, w_data = self._history.shape
        w_display = self.width()

        # Build RGB image from history using color LUT
        indices = self._history.astype(np.uint8)

        # Map each value through the LUT
        rgb_image = COLOR_LUT[indices]  # shape: (h, w_data, 3)

        # Resize to display width if needed
        if w_data != w_display:
            from PIL import Image
            img = Image.fromarray(rgb_image, 'RGB')
            img = img.resize((w_display, h), Image.NEAREST)
            rgb_image = np.array(img)

        # Convert to QImage
        h_img, w_img, _ = rgb_image.shape
        bytes_per_line   = w_img * 3
        q_image = QImage(
            rgb_image.tobytes(),
            w_img, h_img,
            bytes_per_line,
            QImage.Format.Format_RGB888
        )
        self._pixmap = QPixmap.fromImage(q_image)
        self._dirty  = False

    def paintEvent(self, event):
        painter = QPainter(self)
        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor("#000008"))

        draw_h = h - self.FREQ_HEIGHT

        if self._history is not None:
            if self._dirty:
                self._render_pixmap()
            if self._pixmap:
                painter.drawPixmap(0, 0, w, draw_h, self._pixmap)

        # Draw frequency axis at bottom
        self._draw_freq_axis(painter, w, h, draw_h)

        # Draw center frequency marker
        painter.setPen(QPen(QColor("#ff4444"), 1,
                            Qt.PenStyle.DashLine))
        painter.drawLine(w // 2, 0, w // 2, draw_h)

        painter.end()

    def _draw_freq_axis(self, painter, w, h, draw_h):
        """Draw frequency labels and tick marks at bottom."""
        painter.fillRect(0, draw_h, w, self.FREQ_HEIGHT,
                         QColor("#050510"))

        font = QFont("Courier New", 8)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#005533")))

        freq_start = (self.center_freq - self.bandwidth / 2) / 1e6
        freq_end   = (self.center_freq + self.bandwidth / 2) / 1e6

        num_labels = 7
        for i in range(num_labels):
            freq = freq_start + (i / (num_labels - 1)) * \
                   (freq_end - freq_start)
            x    = int((i / (num_labels - 1)) * w)
            painter.drawLine(x, draw_h, x, draw_h + 4)
            painter.drawText(x - 20, draw_h + 6, 42,
                             self.FREQ_HEIGHT - 6,
                             Qt.AlignmentFlag.AlignCenter,
                             f"{freq:.3f}")

    def resizeEvent(self, event):
        self._history = None
        self._dirty   = True
        super().resizeEvent(event)


# ── Color Scale Widget ────────────────────────────────────────

class ColorScaleWidget(QWidget):
    """
    Vertical color scale bar showing the signal strength
    mapping from noise floor to maximum signal.
    Displayed on the right edge of the waterfall.
    """

    WIDTH = 24

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ref_level = -20
        self.range_db  = 80
        self.setFixedWidth(self.WIDTH)
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Expanding
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        w = self.width()
        h = self.height()

        # Draw gradient bar
        for y in range(h):
            value    = 1.0 - (y / h)
            r, g, b  = magnitude_to_color(value)
            painter.setPen(QPen(QColor(r, g, b)))
            painter.drawLine(0, y, w - 20, y)

        # Draw dB labels
        font = QFont("Courier New", 7)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#888888")))

        num_labels = 5
        for i in range(num_labels):
            y  = int((i / (num_labels - 1)) * h)
            db = self.ref_level - (i / (num_labels - 1)) * self.range_db
            painter.drawText(w - 18, y + 4, f"{db:.0f}")

        painter.end()