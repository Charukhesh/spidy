"""Athena Active Window & Context Inspector.

Provides Deep Context situational awareness to Athena:
- Inspects active foreground window title
- Identifies focused application executable and friendly app name
- Captures currently highlighted/selected text in active window (non-destructively)
- Formats context block to feed Gemini alongside screenshot
"""

import os
import time
import ctypes
from ctypes import wintypes
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("athena.context")

# Win32 Constants
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
VK_CONTROL = 0x11
VK_C = 0x43
KEYEVENTF_KEYUP = 0x0002
CF_UNICODETEXT = 13

# Friendly application names lookup
APP_FRIENDLY_NAMES = {
    "code.exe": "Visual Studio Code",
    "devenv.exe": "Visual Studio",
    "chrome.exe": "Google Chrome",
    "msedge.exe": "Microsoft Edge",
    "firefox.exe": "Mozilla Firefox",
    "brave.exe": "Brave Browser",
    "slack.exe": "Slack",
    "discord.exe": "Discord",
    "teams.exe": "Microsoft Teams",
    "ms-teams.exe": "Microsoft Teams",
    "notepad.exe": "Notepad",
    "notepad++.exe": "Notepad++",
    "windowsterminal.exe": "Windows Terminal",
    "cmd.exe": "Command Prompt",
    "powershell.exe": "PowerShell",
    "pwsh.exe": "PowerShell Core",
    "explorer.exe": "Windows File Explorer",
    "excel.exe": "Microsoft Excel",
    "winword.exe": "Microsoft Word",
    "powerpnt.exe": "Microsoft PowerPoint",
    "outlook.exe": "Microsoft Outlook",
    "spotify.exe": "Spotify",
    "obs64.exe": "OBS Studio",
    "telegram.exe": "Telegram",
    "whatsapp.exe": "WhatsApp",
    "postman.exe": "Postman",
    "pycharm64.exe": "PyCharm",
    "clion64.exe": "CLion",
    "sublime_text.exe": "Sublime Text",
}


@dataclass
class WindowContext:
    hwnd: int
    process_id: int
    process_name: str
    app_name: str
    window_title: str
    selected_text: Optional[str] = None

    def to_prompt_text(self) -> str:
        """Format as contextual string for LLM injection."""
        lines = ["[ACTIVE APPLICATION CONTEXT]"]
        if self.app_name:
            lines.append(f"Foreground App: {self.app_name} ({self.process_name})")
        if self.window_title:
            lines.append(f"Window Title: \"{self.window_title}\"")
        if self.selected_text and self.selected_text.strip():
            # Truncate if exceptionally huge to preserve prompt budget
            sel = self.selected_text.strip()
            if len(sel) > 3000:
                sel = sel[:3000] + "... [truncated]"
            lines.append(f"Highlighted/Selected Text:\n```\n{sel}\n```")
        return "\n".join(lines)


class ContextInspector:
    """Inspects the foreground window, process, and highlighted text on Windows."""

    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32

    def get_foreground_window(self) -> int:
        return self.user32.GetForegroundWindow()

    def get_window_title(self, hwnd: int) -> str:
        if not hwnd:
            return ""
        length = self.user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value

    def get_process_name(self, hwnd: int) -> tuple[int, str, str]:
        """Returns (pid, executable_name, friendly_app_name)."""
        if not hwnd:
            return 0, "", ""

        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return 0, "", ""

        exe_name = ""
        # Open process to query image path
        h_process = self.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if h_process:
            try:
                buf = ctypes.create_unicode_buffer(1024)
                size = wintypes.DWORD(1024)
                if self.kernel32.QueryFullProcessImageNameW(h_process, 0, buf, ctypes.byref(size)):
                    full_path = buf.value
                    exe_name = os.path.basename(full_path)
            finally:
                self.kernel32.CloseHandle(h_process)

        # Fallback to psutil if available
        if not exe_name:
            try:
                import psutil
                p = psutil.Process(pid.value)
                exe_name = p.name()
            except Exception:
                pass

        friendly_name = APP_FRIENDLY_NAMES.get(exe_name.lower(), exe_name.replace(".exe", "").capitalize())
        return pid.value, exe_name, friendly_name

    def _read_clipboard_text(self) -> Optional[str]:
        """Read plain text from clipboard via Qt Application instance."""
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                clip = app.clipboard()
                return clip.text() if clip else None
        except Exception:
            pass
        return None

    def _set_clipboard_text(self, text: str) -> bool:
        """Set plain text into clipboard via Qt Application instance."""
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                clip = app.clipboard()
                if clip:
                    clip.setText(text)
                    return True
        except Exception:
            pass
        return False

    def capture_selected_text(self) -> Optional[str]:
        """Safely captures highlighted text by sending Ctrl+C and restoring original clipboard."""
        # 1. Snapshot previous clipboard content
        original_clip = self._read_clipboard_text()

        # 2. Place a unique marker so we know if Ctrl+C copied new content
        marker = f"__ATHENA_PROBE_{time.time()}__"
        self._set_clipboard_text(marker)

        # 3. Simulate Ctrl+C
        self.user32.keybd_event(VK_CONTROL, 0, 0, 0)
        self.user32.keybd_event(VK_C, 0, 0, 0)
        self.user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
        self.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

        # 4. Wait briefly for application to process copy
        time.sleep(0.045)

        new_clip = self._read_clipboard_text()
        captured_text = None

        if new_clip and new_clip != marker:
            # User had text highlighted and copy succeeded!
            captured_text = new_clip

        # 5. Restore original clipboard content non-destructively
        if original_clip is not None:
            self._set_clipboard_text(original_clip)
        elif new_clip == marker:
            # Empty out the probe marker if nothing was copied
            if self.user32.OpenClipboard(0):
                self.user32.EmptyClipboard()
                self.user32.CloseClipboard()

        return captured_text

    def capture_active_context(self, include_selected_text: bool = True) -> WindowContext:
        """Capture full foreground window context."""
        hwnd = self.get_foreground_window()
        title = self.get_window_title(hwnd)
        pid, exe_name, app_name = self.get_process_name(hwnd)

        selected_text = None
        if include_selected_text:
            try:
                selected_text = self.capture_selected_text()
            except Exception as e:
                logger.debug(f"Failed to capture selected text: {e}")

        return WindowContext(
            hwnd=hwnd,
            process_id=pid,
            process_name=exe_name,
            app_name=app_name,
            window_title=title,
            selected_text=selected_text,
        )


# Global singleton
inspector = ContextInspector()
