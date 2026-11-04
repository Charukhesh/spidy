"""Spidy Sound Effects & Audio Cues Engine.

Provides pleasant, zero-latency modern chimes for interaction states:
- Activate (rising dual-tone on push-to-talk press)
- Thinking (subtle gentle harmonic pulse)
- Target Arrival (bright crystal chime when pointer arrives)
- Dictation Start / Stop (soft tactile pop)

Uses native Windows WASAPI/DirectSound via standard winsound/wave in memory.
Zero third-party dependencies, zero latency, no conflicts with mic recording.
"""

import io
import math
import struct
import wave
import threading
import logging
from typing import Optional

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

from spidy.config import load_config

logger = logging.getLogger("spidy.sound")


def _generate_tone_wav(
    frequencies: list[tuple[float, float, float]],  # list of (freq_hz, duration_sec, volume 0-1)
    sample_rate: int = 44100,
    fade_edges_sec: float = 0.015,
) -> bytes:
    """Generate in-memory PCM 16-bit Mono WAV bytes for musical tones."""
    total_samples = int(sum(dur for _, dur, _ in frequencies) * sample_rate)
    raw_samples = []

    for freq, duration, volume in frequencies:
        num_samples = int(duration * sample_rate)
        fade_samples = max(1, int(fade_edges_sec * sample_rate))
        
        for i in range(num_samples):
            # Smooth cosine envelope to eliminate pops/clicks
            env = 1.0
            if i < fade_samples:
                env = 0.5 * (1.0 - math.cos(math.pi * i / fade_samples))
            elif i > num_samples - fade_samples:
                remaining = num_samples - i
                env = 0.5 * (1.0 - math.cos(math.pi * remaining / fade_samples))

            # Tone waveform (fundamental + gentle 2nd harmonic for warmth)
            t = float(i) / sample_rate
            val = math.sin(2.0 * math.pi * freq * t) + 0.25 * math.sin(4.0 * math.pi * freq * t)
            sample = int(val * volume * env * 32767.0 * 0.7)
            sample = max(-32768, min(32767, sample))
            raw_samples.append(sample)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # Pack raw 16-bit PCM samples
        packed = struct.pack(f"<{len(raw_samples)}h", *raw_samples)
        wf.writeframes(packed)

    return buf.getvalue()


class SoundEffectsEngine:
    """Thread-safe sound effects player with pre-cached audio waveforms."""

    _instance: Optional["SoundEffectsEngine"] = None

    def __init__(self):
        self.enabled = True
        self._cache: dict[str, bytes] = {}
        self._lock = threading.Lock()
        self._pregenerate_sounds()

    @classmethod
    def get_instance(cls) -> "SoundEffectsEngine":
        if cls._instance is None:
            cls._instance = SoundEffectsEngine()
        return cls._instance

    def _pregenerate_sounds(self):
        """Pre-render audio chimes into memory for zero latency."""
        try:
            # 1. Activate Chime: Soft rising modern chime (D5 587Hz -> A5 880Hz)
            self._cache["activate"] = _generate_tone_wav([
                (587.33, 0.07, 0.45),
                (880.00, 0.12, 0.55),
            ])

            # 2. Thinking Pulse: Gentle ambient chord swell
            self._cache["thinking"] = _generate_tone_wav([
                (523.25, 0.08, 0.35),
                (659.25, 0.12, 0.40),
            ])

            # 3. Target Arrival Chime: Crystal retro sparkle (A5 880Hz -> C6 1046Hz -> E6 1318Hz)
            self._cache["arrival"] = _generate_tone_wav([
                (880.00, 0.05, 0.40),
                (1046.50, 0.06, 0.50),
                (1318.51, 0.14, 0.60),
            ])

            # 4. Dictation Start: Soft warm pop
            self._cache["dictation_start"] = _generate_tone_wav([
                (440.00, 0.04, 0.35),
                (659.25, 0.06, 0.45),
            ])

            # 5. Dictation Stop / Done: Soft descending confirmation
            self._cache["dictation_stop"] = _generate_tone_wav([
                (659.25, 0.04, 0.40),
                (440.00, 0.08, 0.35),
            ])
        except Exception as e:
            logger.warning(f"Failed to pre-render sound effects: {e}")

    def is_enabled(self) -> bool:
        cfg = load_config()
        return cfg.get("sound_effects_enabled", True) and self.enabled

    def play(self, sound_name: str):
        """Play a cached sound asynchronously without blocking."""
        if not self.is_enabled() or not HAS_WINSOUND:
            return

        wav_bytes = self._cache.get(sound_name)
        if not wav_bytes:
            return

        def _play_worker():
            with self._lock:
                try:
                    winsound.PlaySound(
                        wav_bytes,
                        winsound.SND_MEMORY | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
                    )
                except Exception as e:
                    logger.debug(f"Sound playback error: {e}")

        threading.Thread(target=_play_worker, daemon=True).start()

    def play_activate(self):
        self.play("activate")

    def play_thinking(self):
        self.play("thinking")

    def play_arrival(self):
        self.play("arrival")

    def play_dictation_start(self):
        self.play("dictation_start")

    def play_dictation_stop(self):
        self.play("dictation_stop")

    def play_ding(self):
        """Soft pleasant ding / sparkle chime on successful copy or action."""
        self.play("arrival")


# Global singleton access
sounds = SoundEffectsEngine.get_instance()

