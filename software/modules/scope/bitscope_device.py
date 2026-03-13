from .scope_device import ScopeDevice, WaveformData, LogicData
import numpy as np


class BitScopeDevice(ScopeDevice):
    """
    Real BitScope BS05u hardware backend.
    Requires bitscope-library_2.0 installed on Linux.
    This is completed on Kali during hardware integration.
    """

    def __init__(self, port: str = "USB:/dev/ttyUSB0"):
        self._port = port
        self._connected = False
        # self._bl = None  # BitScope library handle — uncomment on Kali

    def connect(self) -> bool:
        # TODO on Kali:
        # from bitlib import BL_Open, BL_Count, BL_COUNT_DEVICE
        # return bool(BL_Open(self._port, 1))
        raise NotImplementedError("BitScope backend requires Kali + bitscope-library_2.0")

    def disconnect(self):
        # TODO on Kali:
        # from bitlib import BL_Close
        # BL_Close()
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_device_info(self) -> dict:
        # TODO on Kali:
        # from bitlib import BL_Version, BL_VERSION_LIBRARY
        # return {"name": "BitScope BS05u", "firmware": BL_Version(...)}
        raise NotImplementedError

    def capture_waveform(self, sample_rate=1e6, num_samples=1024,
                         voltage_range=5.0, channel_b=False) -> WaveformData:
        # TODO on Kali — full bitlib capture sequence:
        # BL_Mode(BL_MODE_FAST)
        # BL_Rate(sample_rate)
        # BL_Size(num_samples)
        # BL_Trace(BL_TRACE_FORCED, BL_SYNCHRONOUS)
        # data = BL_Acquire()
        raise NotImplementedError

    def capture_logic(self, sample_rate=10e6,
                      num_samples=1024) -> LogicData:
        # TODO on Kali — logic capture sequence
        raise NotImplementedError

    def set_trigger(self, level=0.0, channel=0, edge="rising"):
        # TODO on Kali:
        # from bitlib import BL_Level, BL_Edge
        # BL_Level(level)
        raise NotImplementedError