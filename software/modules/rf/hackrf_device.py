import numpy as np
import threading
from typing import Callable, Optional
from .sdr_device import SDRDevice, SDRConfig


class HackRFDevice(SDRDevice):
    """
    Real HackRF One backend using GNU Radio.
    Requires GNU Radio and gr-osmosdr installed on Kali.
    Completed during Kali hardware integration.
    """

    def __init__(self):
        self._connected   = False
        self._streaming   = False
        self._recording   = False
        self._config      = SDRConfig()
        self._tb          = None  # GNU Radio top block
        self._fft_callback: Optional[Callable] = None

    def connect(self) -> bool:
        # TODO on Kali:
        # import osmosdr
        # Check HackRF is present
        # self._connected = True
        raise NotImplementedError(
            "HackRF backend requires Kali + GNU Radio + gr-osmosdr"
        )

    def disconnect(self):
        self.stop_stream()
        if self._tb:
            self._tb.stop()
            self._tb.wait()
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_device_info(self) -> dict:
        # TODO on Kali:
        # return hackrf device info via osmosdr
        raise NotImplementedError

    def set_config(self, config: SDRConfig):
        self._config = config
        # TODO on Kali: apply to running flowgraph if active
        # self._source.set_center_freq(config.center_freq)
        # self._source.set_sample_rate(config.sample_rate)
        # self._source.set_gain(config.gain)

    def get_config(self) -> SDRConfig:
        return self._config

    def start_stream(self, fft_callback: Callable):
        # TODO on Kali — GNU Radio flowgraph:
        #
        # from gnuradio import gr, blocks, fft
        # import osmosdr
        #
        # class SpectrumFlowgraph(gr.top_block):
        #     def __init__(self, config, callback):
        #         gr.top_block.__init__(self)
        #         self.source = osmosdr.source("hackrf=0")
        #         self.source.set_center_freq(config.center_freq)
        #         self.source.set_sample_rate(config.sample_rate)
        #         self.source.set_gain(config.gain)
        #         self.fft_block = fft.logpwrfft_c(
        #             sample_rate=config.sample_rate,
        #             fft_size=config.fft_size,
        #             ref_scale=2,
        #             frame_rate=15,
        #             avg_alpha=0.5,
        #             average=True
        #         )
        #         self.sink = blocks.vector_sink_f(config.fft_size)
        #         self.connect(self.source, self.fft_block, self.sink)
        #
        raise NotImplementedError

    def stop_stream(self):
        self._streaming = False
        if self._tb:
            self._tb.stop()
            self._tb.wait()

    def is_streaming(self) -> bool:
        return self._streaming

    def start_recording(self, filepath: str) -> bool:
        # TODO on Kali — add file_sink to flowgraph
        raise NotImplementedError

    def stop_recording(self):
        raise NotImplementedError

    def is_recording(self) -> bool:
        return self._recording

    def start_fm_receiver(self, frequency: float,
                          audio_callback: Callable):
        # TODO on Kali — GNU Radio WBFM flowgraph:
        #
        # from gnuradio import analog, audio, filter
        # source → low_pass_filter → wbfm_receive → rational_resampler → audio_sink
        #
        raise NotImplementedError

    def stop_fm_receiver(self):
        raise NotImplementedError

    def scan_frequencies(self, start_freq, end_freq,
                         step, callback):
        # TODO on Kali — retune source for each step,
        # capture short burst, measure peak power, callback
        raise NotImplementedError