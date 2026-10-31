"""Windows Multimedia API (winmm.dll) Audio Recorder for Clicky.

Captures microphone audio at 16kHz 16-bit Mono PCM directly into memory
with zero external C-extension dependencies and microsecond latency.
Includes live audio power level calculation for the waveform animation.
"""

import os
import wave
import math
import struct
import ctypes
from ctypes import (
    wintypes,
    Structure,
    c_uint32,
    c_uint16,
    c_void_p,
    POINTER,
    byref,
    WINFUNCTYPE,
)
import threading
import logging
from typing import Optional, Callable, List

logger = logging.getLogger("clicky.audio")


class WAVEFORMATEX(Structure):
    _fields_ = [
        ("wFormatTag", c_uint16),
        ("nChannels", c_uint16),
        ("nSamplesPerSec", c_uint32),
        ("nAvgBytesPerSec", c_uint32),
        ("nBlockAlign", c_uint16),
        ("wBitsPerSample", c_uint16),
        ("cbSize", c_uint16),
    ]


class WAVEHDR(Structure):
    pass


LPWAVEHDR = POINTER(WAVEHDR)

WAVEHDR._fields_ = [
    ("lpData", c_void_p),
    ("dwBufferLength", c_uint32),
    ("dwBytesRecorded", c_uint32),
    ("dwUser", c_void_p),
    ("dwFlags", c_uint32),
    ("dwLoops", c_uint32),
    ("lpNext", LPWAVEHDR),
    ("reserved", c_void_p),
]

WIM_DATA = 0x3C0
WAVE_MAPPER = 0xFFFFFFFF
CALLBACK_FUNCTION = 0x00030000

WAVEINPROC = WINFUNCTYPE(None, c_void_p, wintypes.UINT, c_void_p, LPWAVEHDR, c_void_p)


class AudioRecorder:
    """Low-latency audio recorder using native Windows winmm.dll."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        bits_per_sample: int = 16,
        on_audio_level: Optional[Callable[[float], None]] = None,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample
        self.bytes_per_sample = bits_per_sample // 8
        self.block_align = self.channels * self.bytes_per_sample
        self.avg_bytes_per_sec = self.sample_rate * self.block_align
        self.on_audio_level = on_audio_level

        self._winmm = ctypes.windll.winmm
        self._setup_winmm_types()

        self._is_recording = False
        self._audio_chunks: List[bytes] = []
        self._h_wave_in = c_void_p()
        self._headers: List[WAVEHDR] = []
        self._buffers: List[ctypes.Array] = []
        self._callback_ref = None
        self._lock = threading.Lock()
        self.current_power_level = 0.0

    def _setup_winmm_types(self):
        self._winmm.waveInOpen.argtypes = [
            POINTER(c_void_p),
            c_uint32,
            POINTER(WAVEFORMATEX),
            c_void_p,
            c_void_p,
            c_uint32,
        ]
        self._winmm.waveInPrepareHeader.argtypes = [c_void_p, c_void_p, c_uint32]
        self._winmm.waveInUnprepareHeader.argtypes = [c_void_p, c_void_p, c_uint32]
        self._winmm.waveInAddBuffer.argtypes = [c_void_p, c_void_p, c_uint32]
        self._winmm.waveInStart.argtypes = [c_void_p]
        self._winmm.waveInStop.argtypes = [c_void_p]
        self._winmm.waveInReset.argtypes = [c_void_p]
        self._winmm.waveInClose.argtypes = [c_void_p]

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def start(self) -> bool:
        """Start recording audio."""
        if self._is_recording:
            return True

        with self._lock:
            self._audio_chunks = []
            self.current_power_level = 0.0

            wfx = WAVEFORMATEX()
            wfx.wFormatTag = 1  # WAVE_FORMAT_PCM
            wfx.nChannels = self.channels
            wfx.nSamplesPerSec = self.sample_rate
            wfx.nAvgBytesPerSec = self.avg_bytes_per_sec
            wfx.nBlockAlign = self.block_align
            wfx.wBitsPerSample = self.bits_per_sample
            wfx.cbSize = 0

            def wave_in_proc(h_wi, u_msg, dw_instance, dw_param1, dw_param2):
                if u_msg == WIM_DATA and self._is_recording and dw_param1:
                    hdr_ptr = ctypes.cast(dw_param1, LPWAVEHDR)
                    hdr = hdr_ptr.contents
                    if hdr.dwBytesRecorded > 0:
                        raw = ctypes.string_at(hdr.lpData, hdr.dwBytesRecorded)
                        self._audio_chunks.append(raw)
                        self._calculate_audio_level(raw)
                    # Re-queue buffer
                    if self._is_recording:
                        self._winmm.waveInAddBuffer(self._h_wave_in, hdr_ptr, ctypes.sizeof(WAVEHDR))

            self._callback_ref = WAVEINPROC(wave_in_proc)

            res = self._winmm.waveInOpen(
                byref(self._h_wave_in),
                WAVE_MAPPER,
                byref(wfx),
                ctypes.cast(self._callback_ref, c_void_p).value,
                0,
                CALLBACK_FUNCTION,
            )
            if res != 0:
                logger.error(f"waveInOpen failed with error code: {res}")
                return False

            # Create 4 rotating buffers (50ms each for smooth live audio visualization)
            buffer_size = int(self.sample_rate * 0.05 * self.block_align)
            self._headers = []
            self._buffers = []

            for _ in range(4):
                buf = (ctypes.c_char * buffer_size)()
                self._buffers.append(buf)

                hdr = WAVEHDR()
                hdr.lpData = ctypes.cast(buf, c_void_p).value
                hdr.dwBufferLength = buffer_size
                hdr.dwFlags = 0
                self._headers.append(hdr)

                self._winmm.waveInPrepareHeader(self._h_wave_in, byref(hdr), ctypes.sizeof(WAVEHDR))
                self._winmm.waveInAddBuffer(self._h_wave_in, byref(hdr), ctypes.sizeof(WAVEHDR))

            res = self._winmm.waveInStart(self._h_wave_in)
            if res != 0:
                logger.error(f"waveInStart failed: {res}")
                return False

            self._is_recording = True
            logger.info("Push-to-talk audio recording started.")
            return True

    def stop(self) -> bytes:
        """Stop recording and return raw PCM bytes."""
        if not self._is_recording:
            return b"".join(self._audio_chunks)

        with self._lock:
            self._is_recording = False
            self.current_power_level = 0.0
            if self.on_audio_level:
                self.on_audio_level(0.0)

            self._winmm.waveInStop(self._h_wave_in)
            self._winmm.waveInReset(self._h_wave_in)

            for hdr in self._headers:
                self._winmm.waveInUnprepareHeader(self._h_wave_in, byref(hdr), ctypes.sizeof(WAVEHDR))

            self._winmm.waveInClose(self._h_wave_in)
            self._headers = []
            self._buffers = []
            self._callback_ref = None

            full_audio = b"".join(self._audio_chunks)
            self._audio_chunks = []
            logger.info(f"Recorded {len(full_audio)} bytes of PCM audio.")
            return full_audio

    def save_wav(self, file_path: str, pcm_bytes: Optional[bytes] = None) -> bool:
        """Save captured audio as a standard 16kHz mono 16-bit WAV file."""
        data = pcm_bytes if pcm_bytes is not None else b"".join(self._audio_chunks)
        try:
            with wave.open(file_path, "wb") as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.bytes_per_sample)
                wf.setframerate(self.sample_rate)
                wf.writeframes(data)
            return True
        except Exception as e:
            logger.error(f"Failed to save WAV file: {e}")
            return False

    def _calculate_audio_level(self, raw_pcm: bytes):
        """Compute RMS audio volume normalized 0.0 to 1.0."""
        count = len(raw_pcm) // 2
        if count == 0:
            return
        shorts = struct.unpack(f"<{count}h", raw_pcm)
        sum_sq = sum(s * s for s in shorts)
        rms = math.sqrt(sum_sq / count)
        # Scale to 0.0 - 1.0 range (human voice usually peaks around 10,000 - 20,000)
        level = min(1.0, max(0.0, rms / 8000.0))
        self.current_power_level = level
        if self.on_audio_level:
            try:
                self.on_audio_level(level)
            except Exception:
                pass

