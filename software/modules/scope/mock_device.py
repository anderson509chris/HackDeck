import numpy as np
import time
from .scope_device import ScopeDevice, WaveformData, LogicData


class MockScopeDevice(ScopeDevice):
    """
    Simulated scope device for development without hardware.
    Generates realistic sine waves, square waves and logic patterns.
    """

    def __init__(self):
        self._connected = False
        self._trigger_level = 0.0
        self._trigger_edge = "rising"
        self._waveform_type = "sine"   # sine, square, triangle
        self._frequency = 1000.0       # Hz
        self._noise_level = 0.05       # Volts

    # ── Connection ────────────────────────────────────────────

    def connect(self) -> bool:
        time.sleep(0.3)  # Simulate connection delay
        self._connected = True
        print("[MockScope] Connected to simulated BS05u")
        return True

    def disconnect(self):
        self._connected = False
        print("[MockScope] Disconnected")

    def is_connected(self) -> bool:
        return self._connected

    def get_device_info(self) -> dict:
        return {
            "name":     "BitScope Micro BS05u (SIMULATED)",
            "model":    "BS05u",
            "firmware": "2.0-SIM",
            "channels": 2,
            "logic_channels": 8,
            "max_sample_rate": 40e6,
            "bandwidth": 20e6,
        }

    # ── Waveform Generation ───────────────────────────────────

    def _generate_waveform(self, time_axis, frequency, amplitude=1.0):
        """Generate a waveform with some noise."""
        noise = np.random.normal(0, self._noise_level, len(time_axis))

        if self._waveform_type == "sine":
            signal = amplitude * np.sin(2 * np.pi * frequency * time_axis)
        elif self._waveform_type == "square":
            signal = amplitude * np.sign(
                np.sin(2 * np.pi * frequency * time_axis)
            )
        elif self._waveform_type == "triangle":
            signal = amplitude * (
                2 * np.abs(
                    2 * (time_axis * frequency -
                         np.floor(time_axis * frequency + 0.5))
                ) - 1
            )
        else:
            signal = np.zeros(len(time_axis))

        return signal + noise

    # ── Capture Methods ───────────────────────────────────────

    def capture_waveform(
        self,
        sample_rate=1e6,
        num_samples=1024,
        voltage_range=5.0,
        channel_b=False
    ) -> WaveformData:

        time_axis = np.linspace(
            0, num_samples / sample_rate, num_samples
        )

        # Channel A — primary signal
        ch_a = self._generate_waveform(
            time_axis, self._frequency, amplitude=voltage_range * 0.4
        )

        # Channel B — slightly different frequency if enabled
        ch_b = None
        if channel_b:
            ch_b = self._generate_waveform(
                time_axis, self._frequency * 1.5,
                amplitude=voltage_range * 0.25
            )

        return WaveformData(
            channel_a=ch_a,
            channel_b=ch_b,
            time_axis=time_axis,
            sample_rate=sample_rate,
            voltage_range=voltage_range
        )

    def capture_logic(
        self,
        sample_rate=10e6,
        num_samples=1024
    ) -> LogicData:

        time_axis = np.linspace(
            0, num_samples / sample_rate, num_samples
        )

        # Generate 8 channels of logic data at different frequencies
        channels = np.zeros((8, num_samples), dtype=np.uint8)
        freqs = [1e3, 2e3, 4e3, 8e3, 500, 250, 125, 62.5]

        for i, freq in enumerate(freqs):
            signal = np.sin(2 * np.pi * freq * time_axis)
            channels[i] = (signal > 0).astype(np.uint8)

        return LogicData(
            channels=channels,
            time_axis=time_axis,
            sample_rate=sample_rate
        )

    def set_trigger(self, level=0.0, channel=0, edge="rising"):
        self._trigger_level = level
        self._trigger_edge = edge
        print(f"[MockScope] Trigger set: {level}V {edge} on CH{'A' if channel == 0 else 'B'}")

    # ── Mock-specific controls ────────────────────────────────

    def set_waveform_type(self, waveform_type: str):
        """Mock only — switch between sine/square/triangle."""
        if waveform_type in ("sine", "square", "triangle"):
            self._waveform_type = waveform_type

    def set_frequency(self, frequency: float):
        """Mock only — set simulated signal frequency."""
        self._frequency = frequency