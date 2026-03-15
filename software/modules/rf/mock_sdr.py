import numpy as np
import threading
import time
from typing import Callable, Optional
from .sdr_device import SDRDevice, SDRConfig, SignalInfo


class MockSDRDevice(SDRDevice):
    """
    Simulated SDR device for development without HackRF.
    Generates realistic looking spectrum data with fake signals.
    """

    def __init__(self):
        self._connected  = False
        self._streaming  = False
        self._recording  = False
        self._fm_active  = False
        self._config     = SDRConfig()
        self._stream_thread: Optional[threading.Thread] = None
        self._fft_callback: Optional[Callable] = None

        # Fake signals to show in the spectrum
        # Each tuple: (offset_from_center_hz, strength, bandwidth_hz)
        self._fake_signals = [
            (-800e3, 0.85, 200e3),   # Strong signal left
            ( 200e3, 0.60, 50e3),    # Medium signal right of center
            ( 600e3, 0.40, 25e3),    # Weaker narrow signal
            (-300e3, 0.30, 100e3),   # Weak wide signal
        ]

    # ── Connection ────────────────────────────────────────────

    def connect(self) -> bool:
        time.sleep(0.2)
        self._connected = True
        print("[MockSDR] Connected to simulated HackRF One")
        return True

    def disconnect(self):
        self.stop_stream()
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_device_info(self) -> dict:
        return {
            "name":         "HackRF One (SIMULATED)",
            "serial":       "0000000000000000",
            "firmware":     "2024.02.1-SIM",
            "freq_min":     1e6,
            "freq_max":     6e9,
            "sample_rates": [2e6, 4e6, 8e6, 10e6, 12.5e6, 16e6, 20e6],
            "gain_range":   (0, 62),
        }

    # ── Configuration ─────────────────────────────────────────

    def set_config(self, config: SDRConfig):
        self._config = config

    def get_config(self) -> SDRConfig:
        return self._config

    # ── FFT Generation ────────────────────────────────────────

    def _generate_fft(self) -> np.ndarray:
        """Generate a realistic looking FFT frame with fake signals."""
        n      = self._config.fft_size
        result = np.zeros(n, dtype=np.float32)

        # Noise floor with some variation
        noise = np.random.normal(0.008, 0.002, n).astype(np.float32)
        noise = np.abs(noise)
        result += noise

        # Add fake signals as Gaussian peaks
        freqs = np.linspace(
            -self._config.bandwidth / 2,
             self._config.bandwidth / 2,
             n
        )

        for offset, strength, bw in self._fake_signals:
            # Gaussian peak centered at offset
            sigma  = bw / (2 * np.sqrt(2 * np.log(2)))
            signal = strength * np.exp(-0.5 * ((freqs - offset) / sigma) ** 2)
            # Add slight time variation to make it look alive
            variation = 1.0 + np.random.normal(0, 0.05)
            result   += signal * variation

        # Add occasional burst signals
        if np.random.random() < 0.05:
            burst_freq  = np.random.uniform(
                -self._config.bandwidth * 0.4,
                 self._config.bandwidth * 0.4
            )
            burst_sigma = np.random.uniform(10e3, 50e3)
            burst       = 0.7 * np.exp(
                -0.5 * ((freqs - burst_freq) / burst_sigma) ** 2
            )
            result += burst

        return result

    # ── Streaming ─────────────────────────────────────────────

    def start_stream(self, fft_callback: Callable):
        if self._streaming:
            return
        self._fft_callback = fft_callback
        self._streaming    = True
        self._stream_thread = threading.Thread(
            target=self._stream_loop,
            daemon=True
        )
        self._stream_thread.start()
        print("[MockSDR] Stream started")

    def _stream_loop(self):
        """Generate FFT frames at ~10fps."""
        while self._streaming:
            if self._fft_callback:
                fft_data = self._generate_fft()
                self._fft_callback(fft_data)
            time.sleep(0.1)  # 10 fps

    def stop_stream(self):
        self._streaming = False
        if self._stream_thread:
            self._stream_thread.join(timeout=1.0)
        print("[MockSDR] Stream stopped")

    def is_streaming(self) -> bool:
        return self._streaming

    # ── Recording ─────────────────────────────────────────────

    def start_recording(self, filepath: str) -> bool:
        print(f"[MockSDR] Recording to {filepath} (simulated)")
        self._recording  = True
        self._record_path = filepath
        return True

    def stop_recording(self):
        print(f"[MockSDR] Recording stopped (simulated)")
        self._recording = False

    def is_recording(self) -> bool:
        return self._recording

    # ── FM Receiver ───────────────────────────────────────────

    def start_fm_receiver(self, frequency: float,
                          audio_callback: Callable):
        print(f"[MockSDR] FM receiver started at "
              f"{frequency/1e6:.3f} MHz (simulated)")
        self._fm_active = True

    def stop_fm_receiver(self):
        self._fm_active = False

    # ── Scanner ───────────────────────────────────────────────

    def scan_frequencies(self, start_freq: float, end_freq: float,
                         step: float, callback: Callable):
        """Simulate a frequency scan."""
        print(f"[MockSDR] Scanning {start_freq/1e6:.1f} - "
              f"{end_freq/1e6:.1f} MHz (simulated)")
        freq = start_freq
        while freq <= end_freq:
            # Random signal strength with occasional strong signals
            strength = np.random.uniform(-90, -60)
            if np.random.random() < 0.1:
                strength = np.random.uniform(-60, -30)
            callback(freq, strength)
            freq += step
            time.sleep(0.02)