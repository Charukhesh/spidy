"""Speech-To-Text (STT) Engine using Faster-Whisper with Windows SAPI fallback.
Completely free, offline, zero API cost.

Directly converts raw 16kHz 16-bit Mono PCM audio into float32 numpy arrays,
bypassing PyAV container decoding to prevent AV metadata_errors bugs and
maximizing transcription speed on Windows.
"""

import os
import sys
import logging
import threading
import numpy as np

# Prevent OpenMP runtime collision on Windows with multiple runtime DLLs
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

logger = logging.getLogger("clicky.stt")

_WHISPER_MODEL = None
_MODEL_LOCK = threading.Lock()


def get_whisper_model(model_size: str = "base.en"):
    global _WHISPER_MODEL
    with _MODEL_LOCK:
        if _WHISPER_MODEL is None:
            try:
                from faster_whisper import WhisperModel
                logger.info(f"Loading faster-whisper model '{model_size}' on CPU/int8...")
                _WHISPER_MODEL = WhisperModel(
                    model_size,
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=4,
                )
                logger.info("Faster-whisper model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load faster-whisper model: {e}")
                _WHISPER_MODEL = None
    return _WHISPER_MODEL


class SpeechToText:
    def __init__(self, model_size: str = "base.en"):
        self.model_size = model_size
        # Pre-warm model in background thread
        threading.Thread(target=get_whisper_model, args=(self.model_size,), daemon=True).start()

    def transcribe_pcm(self, raw_pcm: bytes) -> str:
        """Transcribe 16kHz 16-bit Mono PCM bytes directly via numpy array."""
        if not raw_pcm or len(raw_pcm) < 3200:  # <0.1s audio
            return ""

        try:
            # Convert raw 16-bit PCM bytes to float32 normalized [-1.0, 1.0]
            audio_array = np.frombuffer(raw_pcm, dtype=np.int16).astype(np.float32) / 32768.0

            model = get_whisper_model(self.model_size)
            if model:
                segments, info = model.transcribe(
                    audio_array,
                    beam_size=3,
                    language="en",
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=300),
                )
                text = " ".join([seg.text.strip() for seg in segments]).strip()
                if text:
                    logger.info(f"Whisper transcript: '{text}' (lang={info.language})")
                    return text
        except Exception as e:
            logger.error(f"Whisper numpy transcription notice: {e}")

        # Fallback to Windows SAPI
        return self._transcribe_with_windows_sapi_pcm(raw_pcm)

    def transcribe_wav(self, wav_path: str) -> str:
        """Transcribe WAV file by reading PCM frames into numpy array."""
        if not os.path.exists(wav_path):
            return ""

        try:
            import wave
            with wave.open(wav_path, "rb") as wf:
                pcm_data = wf.readframes(wf.getnframes())
            return self.transcribe_pcm(pcm_data)
        except Exception as e:
            logger.error(f"Error reading WAV for transcription: {e}")
            return ""

    def _transcribe_with_windows_sapi_pcm(self, raw_pcm: bytes) -> str:
        """Windows native System.Speech fallback."""
        import tempfile
        import subprocess

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            wav_path = tf.name

        try:
            import wave
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(raw_pcm)

            escaped_path = os.path.abspath(wav_path).replace("'", "''")
            ps_script = f"""
Add-Type -AssemblyName System.Speech
try {{
    $sre = New-Object System.Speech.Recognition.SpeechRecognitionEngine
    $sre.SetInputToWaveFile('{escaped_path}')
    $grammar = New-Object System.Speech.Recognition.DictationGrammar
    $sre.LoadGrammar($grammar)
    $res = $sre.Recognize()
    if ($res -ne $null -and $res.Text -ne $null) {{
        Write-Output ("RESULT:" + $res.Text)
    }} else {{
        Write-Output "RESULT:"
    }}
    $sre.Dispose()
}} catch {{
    Write-Output ("ERROR:" + $_.Exception.Message)
}}
"""
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=8,
            )
            for line in res.stdout.splitlines():
                if line.startswith("RESULT:"):
                    return line[len("RESULT:") :].strip()
        except Exception as e:
            logger.error(f"Windows SAPI fallback speech error: {e}")
        finally:
            if os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except Exception:
                    pass
        return ""
