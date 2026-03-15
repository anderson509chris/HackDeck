from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Callable
import numpy as np


@dataclass
class SDRConfig:
    """Configuration parameters for SDR capture."""
    center_freq:  float = 100e6    # Hz
    sample_rate:  float = 2e6     # samples/sec
    gain:         float = 40.0    # dB
    fft_size:     int   = 1024    # FFT bins
    bandwidth:    float = 2e6     # Hz display bandwidth


@dataclass
class SignalInfo:
    """Information about a detected signal."""
    frequency:  float   # Hz
    strength:   float   # dBFS
    bandwidth:  float   # Hz estimate
    label:      str = ""


class SDRDevice(ABC):
    """
    Abstract base class for all SDR backends.
    HackRFDevice and MockSDRDevice both implement this interface.
    The UI module never talks directly to hardware.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Connect to SDR device. Returns True if successful."""
        pass

    @abstractmethod
    def disconnect(self):
        """Cleanly disconnect and stop any running streams."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def get_device_info(self) -> dict:
        """Returns dict with device name, serial, firmware etc."""
        pass

    @abstractmethod
    def set_config(self, config: SDRConfig):
        """Apply new SDR configuration."""
        pass

    @abstractmethod
    def get_config(self) -> SDRConfig:
        """Get current SDR configuration."""
        pass

    @abstractmethod
    def start_stream(self, fft_callback: Callable):
        """
        Start streaming FFT data.
        fft_callback(fft_data: np.ndarray) called for each FFT frame.
        """
        pass

    @abstractmethod
    def stop_stream(self):
        """Stop the FFT stream."""
        pass

    @abstractmethod
    def is_streaming(self) -> bool:
        pass

    @abstractmethod
    def start_recording(self, filepath: str) -> bool:
        """Start recording raw IQ data to file."""
        pass

    @abstractmethod
    def stop_recording(self):
        """Stop recording."""
        pass

    @abstractmethod
    def is_recording(self) -> bool:
        pass

    @abstractmethod
    def start_fm_receiver(self,
                          frequency: float,
                          audio_callback: Callable):
        """
        Start FM demodulation.
        audio_callback(audio_data: np.ndarray) called with audio samples.
        """
        pass

    @abstractmethod
    def stop_fm_receiver(self):
        pass

    @abstractmethod
    def scan_frequencies(self,
                         start_freq: float,
                         end_freq:   float,
                         step:       float,
                         callback:   Callable):
        """
        Scan a frequency range and report signals found.
        callback(freq, strength) called for each step.
        """
        pass