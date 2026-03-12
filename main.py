import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget,
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGridLayout, QFrame
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor

# ── Stylesheet ────────────────────────────────────────────────
STYLE = """
    QMainWindow, QWidget {
        background-color: #0a0a0f;
        color: #00ff88;
        font-family: "Courier New", monospace;
    }
    QLabel {
        color: #00ff88;
    }
    QLabel#title {
        font-size: 28px;
        font-weight: bold;
        color: #00ff88;
    }
    QLabel#subtitle {
        font-size: 12px;
        color: #005533;
        letter-spacing: 3px;
    }
    QLabel#status_ok {
        color: #00ff88;
        font-size: 11px;
    }
    QLabel#status_err {
        color: #ff4444;
        font-size: 11px;
    }
    QPushButton#module_btn {
        background-color: #0f1f0f;
        border: 1px solid #00aa55;
        border-radius: 10px;
        padding: 18px;
        font-size: 13px;
        color: #00ff88;
        text-align: left;
    }
    QPushButton#module_btn:hover {
        background-color: #1a3a1a;
        border: 1px solid #00ff88;
    }
    QPushButton#module_btn:pressed {
        background-color: #00ff88;
        color: #0a0a0f;
    }
    QPushButton#back_btn {
        background-color: transparent;
        border: 1px solid #005533;
        border-radius: 6px;
        padding: 6px 14px;
        color: #00aa55;
        font-size: 12px;
    }
    QPushButton#back_btn:hover {
        border-color: #00ff88;
        color: #00ff88;
    }
    QFrame#divider {
        color: #003322;
        background-color: #003322;
    }
    QFrame#status_bar {
        background-color: #050510;
        border-top: 1px solid #003322;
    }
"""

# ── Status Bar (shared across screens) ───────────────────────
class StatusBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("status_bar")
        self.setFixedHeight(32)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)

        # Hardware status indicators
        self.hw_status = {
            "HackRF":  self._make_indicator("HackRF"),
            "RFID":    self._make_indicator("RFID"),
            "AD3":     self._make_indicator("AD3"),
        }
        for label in self.hw_status.values():
            layout.addWidget(label)

        layout.addStretch()

        # System info right side
        self.sys_label = QLabel("HackDeck v0.1")
        self.sys_label.setObjectName("status_ok")
        layout.addWidget(self.sys_label)

    def _make_indicator(self, name):
        label = QLabel(f"● {name}")
        label.setObjectName("status_err")  # Red by default (not connected)
        return label

    def set_connected(self, device, connected):
        label = self.hw_status.get(device)
        if label:
            label.setObjectName("status_ok" if connected else "status_err")
            label.style().unpolish(label)
            label.style().polish(label)


# ── Home Screen ───────────────────────────────────────────────
class HomeScreen(QWidget):
    def __init__(self, shell):
        super().__init__()
        self.shell = shell
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 20)
        layout.setSpacing(8)

        # Header
        title = QLabel("HACKDECK")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("PORTABLE SECURITY RESEARCH PLATFORM")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(20)

        # Divider
        line = QFrame()
        line.setObjectName("divider")
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        layout.addWidget(line)
        layout.addSpacing(20)

        # Module grid — 2 columns
        grid = QGridLayout()
        grid.setSpacing(12)

        modules = [
            ("📡  RF / SDR",        "HackRF spectrum\nanalysis & replay",  "rf"),
            ("🔖  RFID / NFC",      "Read, write &\nemulate tags",         "rfid"),
            ("📊  Scope / Logic",   "Oscilloscope &\nlogic analyzer",      "scope"),
            ("🌐  Network",         "Scan, sniff &\nanalyze traffic",      "network"),
            ("⚙️   System",          "Settings, power\n& device info",      "system"),
            ("📁  Logs",            "Captured data\n& session logs",       "logs"),
        ]

        for i, (name, desc, module_id) in enumerate(modules):
            btn = QPushButton(f"{name}\n{desc}")
            btn.setObjectName("module_btn")
            btn.setMinimumHeight(90)
            btn.clicked.connect(lambda checked, m=module_id: self.shell.show_screen(m))
            grid.addWidget(btn, i // 2, i % 2)

        layout.addLayout(grid)
        layout.addStretch()


# ── Placeholder Module Screen ─────────────────────────────────
class PlaceholderScreen(QWidget):
    def __init__(self, shell, title):
        super().__init__()
        self.shell = shell
        self._build_ui(title)

    def _build_ui(self, title):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Top bar with back button and title
        top_bar = QHBoxLayout()
        back_btn = QPushButton("◀  Home")
        back_btn.setObjectName("back_btn")
        back_btn.setFixedWidth(100)
        back_btn.clicked.connect(lambda: self.shell.show_screen("home"))

        screen_title = QLabel(title)
        screen_title.setObjectName("title")
        screen_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        top_bar.addWidget(back_btn)
        top_bar.addWidget(screen_title, stretch=1)
        top_bar.addSpacing(100)  # Balance the back button

        layout.addLayout(top_bar)
        layout.addSpacing(20)

        # Placeholder content
        placeholder = QLabel("[ Module under construction ]")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #005533; font-size: 16px;")
        layout.addWidget(placeholder, stretch=1)


# ── Main Shell ────────────────────────────────────────────────
class HackDeckShell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HackDeck")
        self.resize(800, 480)  # Target device resolution

        self.stack = QStackedWidget()
        self.screens = {}

        # Status bar at bottom
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(self.stack)

        self.status_bar = StatusBar()
        container_layout.addWidget(self.status_bar)

        self.setCentralWidget(container)

        # Register screens
        self._add_screen("home",    HomeScreen(self))
        self._add_screen("rf",      PlaceholderScreen(self, "RF / SDR"))
        self._add_screen("rfid",    PlaceholderScreen(self, "RFID / NFC"))
        self._add_screen("scope",   PlaceholderScreen(self, "Scope / Logic"))
        self._add_screen("network", PlaceholderScreen(self, "Network"))
        self._add_screen("system",  PlaceholderScreen(self, "System"))
        self._add_screen("logs",    PlaceholderScreen(self, "Logs"))

        self.show_screen("home")

    def _add_screen(self, name, widget):
        self.screens[name] = widget
        self.stack.addWidget(widget)

    def show_screen(self, name):
        if name in self.screens:
            self.stack.setCurrentWidget(self.screens[name])


# ── Entry Point ───────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)

    shell = HackDeckShell()
    shell.show()

    sys.exit(app.exec())