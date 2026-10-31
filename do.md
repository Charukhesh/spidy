# 🚀 Athena Next-Gen Capabilities & Roadmap: The Everyday Desktop Superpower Plan

This plan outlines high-impact capability upgrades to evolve Athena from an advisory companion into an indispensable, proactive everyday desktop assistant.

---

## 1. Five High-Impact Capability Pillars

### 🖥️ Pillar 1: Hands-On Desktop Actions & System Control (The "Doer" Assistant)
Currently, Athena is observational and advisory. Giving Athena safe, hands-on OS capabilities enables her to perform tasks directly on your behalf without opening terminal windows.
- **Application & File Launcher**:
  - Voice trigger: *"Open Spotify"*, *"Launch VS Code on the Athena project"*, *"Open my Downloads folder"*.
  - Uses Windows `os.startfile` and `ShellExecute` to launch target apps smoothly in the background.
- **Window Snapping & Layout Organization**:
  - Voice trigger: *"Snap this window to the left"*, *"Minimize everything except my code editor"*, *"Bring Chrome to the front"*.
  - Uses `ctypes.windll.user32` to orchestrate clean window arrangements.
- **Clipboard Transformation Engine**:
  - Voice trigger: *"Rewrite what's on my clipboard into a concise email"*, *"Format this JSON on my clipboard"*, *"Convert this raw text into bullet points"*.
  - Athena reads the clipboard, processes it with Gemini, replaces the clipboard content, and plays the arrival chime.

---

### 🧠 Pillar 2: Persistent Long-Term Memory (The "Agent That Remembers You")
Currently, Athena's conversation history resets when the process ends. A persistent, privacy-first local memory database allows Athena to understand your long-term context across days and weeks.
- **Local SQLite Knowledge Store (`~/.athena/memory.db`)**:
  - Completely local, offline, and private.
  - Stores:
    - User preferences: Preferred tech stacks (Python, PyTorch, React), coding styles, tone preferences.
    - Project context: Names of active repos, key goals, deadlines.
    - Work logs: What was accomplished in previous sessions.
- **Natural Recall & Continuity**:
  - *"Remember that I prefer type annotations on all Python functions"*.
  - *"What was I working on yesterday afternoon?"* -> Athena recalls active window context and project titles from previous sessions.
  - Automatically injects relevant memories into Gemini's prompt context when matching topics arise.

---

### 🔍 Pillar 3: Visual Data Extraction & OCR (The "Visual Scratchpad")
Often, information on your screen is trapped inside images, video frames, PDFs, or software interfaces where text cannot be selected or copied.
- **Uncopyable Text to Clipboard**:
  - Point your mouse near an image or video: *"Copy the text in this image to my clipboard"*.
  - Athena crops the bounding box around your mouse cursor, extracts the exact text via Gemini Vision, and loads it straight into your clipboard.
- **Image / Diagram to Structured Code**:
  - Voice trigger: *"Turn this flowchart on my screen into Mermaid.js code"*, *"Convert this table into a markdown table"*.
  - Athena formats the result and provides a 1-click "Copy Code" pill in the top glass HUD.

---

### 📚 Pillar 4: Proactive Reading & Deep Research Assistant
Enhancing the existing web search with active reading comprehension and multi-source synthesis.
- **Active Reading Helper (Element Hover Zoom)**:
  - When reading research papers, complex math, or documentation:
  - Hold `Ctrl + Alt`: *"Explain this equation right here"* or *"What does this function do?"*.
  - Athena inspects the exact element your mouse is hovering over and breaks it down intuitively.
- **Multi-Source Comparative Research**:
  - When asked complex questions (*"Compare the top 3 vision models in 2026"*):
  - Athena retrieves multiple sources, synthesizes a concise comparative table, and presents it copy-ready in the glass HUD.

---

### 🎙️ Pillar 5: Voice Interruptibility & Hands-Free Option
- **Instant Barge-In / Speech Silencing**:
  - Tapping `Ctrl + Alt` while Athena is speaking instantly silences the TTS without lag, readying her for your next question immediately.
- **Optional Hands-Free Wake Word Mode**:
  - For moments when your hands are busy (cooking, typing, gaming):
  - Optional low-power offline wake-word detector (e.g., *"Hey Athena"*) alongside the unified `Ctrl + Alt` push-to-talk.

---

## 2. Implementation Status & Verification

All phases are fully implemented and verified with exhaustive test coverage:

1. **Phase 1: Hands-On Desktop Actions & Clipboard Engine** (`athena/desktop_actions.py`)
   - ✅ Safe app, directory, and URL launcher with path validation.
   - ✅ Windows window management: snap left, snap right, maximize, restore, minimize others.
   - ✅ Clipboard reading, transformation, and writing with audio confirmation chimes.
   - ✅ Verified via `test_desktop_actions.py` (4/4 tests passed).

2. **Phase 2: Persistent Local Long-Term Memory Store** (`athena/memory_store.py`)
   - ✅ Local, private SQLite database at `~/.athena/memory.db`.
   - ✅ Key-value preferences, project context, and interaction logging.
   - ✅ Dynamic prompt injection `[REMEMBERED USER PREFERENCES & CONTEXT]`.
   - ✅ Tag parsing `[REMEMBER:category:key:content]` auto-updates memory.
   - ✅ Verified via `test_memory_store.py` (3/3 tests passed).

3. **Phase 3: Visual Scratchpad & Focal OCR Cropper** (`athena/visual_scratchpad.py`)
   - ✅ High-resolution crop centered at mouse coordinates (`crop_region_around_point`).
   - ✅ Uncopyable text, markdown tables, and Mermaid.js flowchart extraction.
   - ✅ Immediate clipboard loading via `load_extracted_to_clipboard()`.
   - ✅ Verified via `test_visual_scratchpad.py` (3/3 tests passed).

4. **Phase 4: Proactive Reading & Research Assistant**
   - ✅ Mouse-coordinate visual context injection into Gemini Vision prompt.
   - ✅ Web search grounding and synthesis formatting with copy-ready HUD display.
   - ✅ Verified via `test_pointing_and_drawing.py` (8/8 tests passed).

5. **Phase 5: Voice Interruptibility & Hands-Free Option** (`athena/wake_word.py`)
   - ✅ Instant speech barge-in on `Ctrl + Alt` (immediate `tts_engine.stop()`).
   - ✅ Optional wake-word listener thread configurable in `config.json`.
   - ✅ Verified via `test_everyday_features.py` (11/11 tests passed).


