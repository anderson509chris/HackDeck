from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class WaveformData:
    """Container for captured waveform data."""
    channel_a:   np.ndarray      # Voltage samples channel A
    channel_b:   Optional[np.ndarray]  # Voltage samples channel B
    time_axis:   np.ndarray      # Time values in seconds
    sample_rate: float           # Actual sample rate used
    voltage_range: float         # Full scale voltage range


@dataclass
class LogicData:
    """Container for captured logic analyzer data."""
    channels:    np.ndarray      # 8 x N array of logic samples
    time_axis:   np.ndarray      # Time values in seconds
    sample_rate: float           # Actual sample rate used


class ScopeDevice(ABC):
    """
    Abstract base class for all scope backends.
    Both BitScopeDevice and AD3Device must implement this interface.
    The UI module only ever talks to this — never to hardware directly.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the device. Returns True if successful."""
        pass

    @abstractmethod
    def disconnect(self):
        """Cleanly disconnect from the device."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if device is currently connected."""
        pass

    @abstractmethod
    def get_device_info(self) -> dict:
        """Returns dict with device name, firmware version etc."""
        pass

    @abstractmethod
    def capture_waveform(
        self,
        sample_rate: float,
        num_samples: int,
        voltage_range: float,
        channel_b: bool = False
    ) -> WaveformData:
        """
        Capture analog waveform data.
        sample_rate:   samples per second
        num_samples:   number of samples to capture
        voltage_range: full scale range in volts
        channel_b:     also capture channel B if True
        """
        pass

    @abstractmethod
    def capture_logic(
        self,
        sample_rate: float,
        num_samples: int
    ) -> LogicData:
        """
        Capture 8-channel logic analyzer data.
        sample_rate:  samples per second
        num_samples:  number of samples to capture
        """
        pass

    @abstractmethod
    def set_trigger(
        self,
        level: float,
        channel: int = 0,
        edge: str = "rising"
    ):
        """
        Configure trigger.
        level:   voltage trigger level
        channel: 0=A, 1=B
        edge:    'rising' or 'falling'
        """
        pass