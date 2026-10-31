# 🏛️ Athena Technical Architecture & Design Document

This document provides an exhaustive technical breakdown of Athena's internal subsystems, reverse-engineered mechanics, and Windows-native design patterns.

---

## 1. System Components & File Layout

```
Athena-Everyday-Agent/
├── athena/
│   ├── __init__.py              # Package initializer
│   ├── main.py                  # High-DPI PyQt5 entry point & lifecycle
│   ├── companion_manager.py     # Pipeline coordinator & dual hotkey polling thread
│   ├── companion_panel.py       # Modern dark 330px settings panel & test suite
│   ├── cursor_overlay.py        # Transparent click-through overlay with Bézier flight
│   ├── ai_vision_client.py      # Universal Gemini / Groq / Grok multimodal client
│   ├── grok_client.py           # Compatibility wrapper
│   ├── dictation_manager.py     # Global push-to-talk voice typing & text injection
│   ├── context_inspector.py     # Active foreground window, process, & selected text
│   ├── sound_effects.py         # Zero-latency in-memory modern chimes audio engine
│   ├── floating_history_overlay.py # Glassmorphic answer HUD with 1-click copy & hover pause
│   ├── audio_recorder.py        # Pure ctypes winmm.dll low-latency PCM recorder
│   ├── screen_capture.py        # Multi-monitor screen capture engine (MSS / PIL / GDI)
│   ├── stt_engine.py            # Faster-Whisper in-memory float32 NumPy transcriber
│   ├── tts_engine.py            # Edge Neural TTS async streamer & player
│   ├── tray_manager.py          # Windows notification area system tray integration
│   └── config.py                # ~/.athena/config.json persistence & migration
├── run_athena.py                # Python workspace launcher
├── build_exe.py                 # PyInstaller standalone build script
├── requirements.txt             # Pinned dependencies
├── README.md                    # User guide & project overview
├── ARCHITECTURE.md              # Detailed architecture breakdown (this file)
└── API_SETUP.md                 # Multimodal API key guide
```

---

## 2. Multi-Monitor Coordinate System & Math

### The Problem in Windows Multi-Display Setups
In Windows dual-monitor configurations, the secondary display often carries negative coordinate origins. For instance:
* `DISPLAY2` (Primary): `(0, 0, 1920, 1080)`
* `DISPLAY1` (Secondary, placed to the left): `(-1920, -71, 1920, 1080)`

Painting at unmapped Windows global coordinates on a secondary monitor causes an offset of exactly `1,920` pixels because the overlay window expects coordinates local to its widget viewport.

### The Solution: `mapFromGlobal()`
Athena translates all incoming global cursor and element coordinates via PyQt5:

$$\mathbf{p}_{\text{local}} = \mathbf{W}_{\text{overlay}}.\text{mapFromGlobal}(\mathbf{p}_{\text{global}})$$

During screen capture, each display's bounding rect is recorded. When the multimodal vision model outputs a coordinate tag:

$$\text{[POINT:} x, y \text{:label:screen} N \text{]}$$

Athena translates $(x, y)$ back into global desktop space:

$$X_{\text{global}} = \text{Screen}_N.\text{left} + x$$
$$Y_{\text{global}} = \text{Screen}_N.\text{top} + y$$

---

## 3. Quadratic Bézier Flight Animation

When Athena points at a UI element, it does not snap or teleport. It executes a smooth quadratic Bézier flight curve:

$$\mathbf{B}(t) = (1 - t)^2 \mathbf{P}_0 + 2(1 - t)t \mathbf{P}_1 + t^2 \mathbf{P}_2, \quad t \in [0, 1]$$

Where:
* $\mathbf{P}_0$: Starting position (mouse cursor spring offset).
* $\mathbf{P}_1$: Arc midpoint offset by a perpendicular swoop vector $\mathbf{v}_{\text{arc}} = (- \Delta y \cdot 0.35, \Delta x \cdot 0.35)$.
* $\mathbf{P}_2$: Target UI element position.

A cubic ease-out transfer function ($f(t) = 1 - (1 - t)^3$) governs the progression, creating an organic, energetic swooping motion matching the original macOS companion design.

---

## 4. Hardware-Level Push-to-Talk via `GetAsyncKeyState`

Traditional global hotkey libraries (`keyboard`, `pynput`) hook the Windows message queue via `SetWindowsHookEx`. This causes dropped key-up events during modifier release reordering (`Shift` released before `Ctrl`) and freezes when elevated windows have focus.

Athena uses a dedicated 100 Hz hardware polling thread querying `user32.GetAsyncKeyState()`:

```python
ctrl_pressed = bool(user32.GetAsyncKeyState(0x11) & 0x8000)
shift_pressed = bool(user32.GetAsyncKeyState(0x10) & 0x8000)
is_down = ctrl_pressed and shift_pressed
```

* **Pressed Edge**: Starts the ctypes audio recorder and switches the cursor state to `VoiceState.LISTENING` (pulsing red triangle + 5-bar volume waveform).
* **Released Edge**: Stops recording immediately, captures active screens, and triggers the transcription and AI pipeline.

---

## 5. In-Memory Zero-Copy Audio Pipeline

### Recording via Pure ctypes `winmm.dll`
Bypassing PyAudio and PortAudio, Athena uses Windows Multimedia APIs (`waveInOpen`, `waveInPrepareHeader`, `waveInAddBuffer`, `waveInStart`):
* Sample Rate: `16,000 Hz` (optimal for Whisper)
* Bit Depth: `16-bit Signed Integer (PCM)`
* Channel: `1 (Mono)`
* Latency: Sub-10ms buffer turnaround.

### RMS Audio Power Metering
A sliding window computes the live Root Mean Square (RMS) decibel level:

$$\text{RMS} = \sqrt{\frac{1}{N} \sum_{i=1}^N x_i^2}$$

This drives the 5 animated waveform bars rendered directly below the cursor in real time.

### In-Memory Faster-Whisper Transcription
To circumvent the breaking change in `PyAV 19.0.2` (`TypeError: open() got unexpected keyword argument metadata_errors`), Athena bypasses file I/O and container decoding completely by converting raw PCM bytes directly into a float32 NumPy array:

$$\mathbf{A}_{\text{audio}} = \frac{\text{np.frombuffer}(\text{pcm\_data}, \text{dtype}=\text{int16})}{32768.0}$$

This is passed directly into `WhisperModel.transcribe(audio_array)`, achieving instant speech-to-text with zero disk latency.

---

## 6. Multimodal Vision Routing

[`athena/ai_vision_client.py`](file:///c:/Users/charu/Downloads/Projects/Athena%20Agent/athena/ai_vision_client.py) dynamically resolves endpoints based on key signatures:

| Key Prefix | Target Endpoint | Active Vision Model | Context / Quota |
| :--- | :--- | :--- | :--- |
| `AQ.` or `AIza...` | `generativelanguage.googleapis.com` | `gemini-3.5-flash` | **1,000,000 TPM** (1.5k requests/day free) |
| `gsk_...` | `api.groq.com/openai/v1` | `qwen/qwen3.8-27b` | Free Tier LPU (~15,000 TPM) |
| `xai-...` | `api.x.ai/v1` | `grok-2-vision-1212` | Paid xAI Credits |

---

## 7. Everyday Power Pack Subsystems

### 1. Global Voice Dictation (`athena/dictation_manager.py`)
* Activated by holding `Ctrl + Alt`.
* Displays a compact floating status pill (`🎙️ Dictating...`) above the mouse cursor.
* On release, audio is transcribed using Faster-Whisper, and the resulting text is directly injected into the active foreground window via simulated `Ctrl + V` paste.
* Prior user clipboard data is automatically captured and restored after a 200ms delay, guaranteeing non-destructive voice typing without losing clipboard items.

### 2. Deep Context Awareness (`athena/context_inspector.py`)
* Leverages Win32 `GetForegroundWindow()`, `GetWindowTextW()`, and process query APIs.
* Inspects active application process executable and maps to user-friendly titles (e.g. `Code.exe` -> `Visual Studio Code`).
* Safe highlighted text capture: non-destructively probes selected text in the active window by sending `Ctrl + C` against a temporary probe marker and restoring prior clipboard content.
* Injects formatted context into Gemini prompt:
  ```
  [ACTIVE APPLICATION CONTEXT]
  Foreground App: Visual Studio Code (Code.exe)
  Window Title: main.py - Athena Agent
  Highlighted/Selected Text: ...
  ```

### 3. Modern Sound Cues Engine (`athena/sound_effects.py`)
* Zero-latency in-memory 16-bit PCM WAV audio synthesizer and player.
* Employs native Windows WASAPI/DirectSound via `winsound.PlaySound` (SND_MEMORY | SND_ASYNC).
* Smooth musical chimes:
  * **Activate**: Rising soft two-tone chime ($587\text{ Hz} \to 880\text{ Hz}$).
  * **Thinking**: Gentle ambient harmonic pulse ($523\text{ Hz} + 659\text{ Hz}$).
  * **Target Arrival**: Crystal chime on pointing landing ($880\text{ Hz} \to 1046\text{ Hz} \to 1318\text{ Hz}$).
  * **Dictation Start/Stop**: Soft tactile pops ($440\text{ Hz} \leftrightarrow 659\text{ Hz}$).

### 4. Floating Answer & History HUD (`athena/floating_history_overlay.py`)
* Translucent glassmorphic acrylic HUD positioned in the bottom-right corner of the primary display.
* Displays latest spoken AI answers and user queries.
* Features a 1-click **"📋 Copy Answer"** button.
* Smooth 8-second auto-fade countdown that automatically pauses when the user's mouse hovers over the card, resuming with a 3-second delay on mouse leave.

