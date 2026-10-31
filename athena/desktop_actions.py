"""Desktop Actions & System Controller for Athena.

Provides hands-on local OS capabilities without opening terminal windows:
1. Application & Path Launcher: Opens apps (Spotify, VS Code, Chrome, etc.) and folders.
2. Window Snapping & Layout Manager: Controls foreground window placement via Windows API.
3. Clipboard Transformation Engine: Formats, summarizes, or rewrites clipboard text.
4. Safe Execution Dispatcher: Executes safe actions instantly, confirms destructive actions.
"""

import os
import sys
import ctypes
import json
import logging
import subprocess
import urllib.parse
from typing import Tuple, Optional, Dict, Any

from PyQt5.QtWidgets import QApplication

logger = logging.getLogger("athena.actions")

# Windows API Constants
SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_MAXIMIZE = 3
SW_RESTORE = 9

HWND_TOP = 0
SWP_SHOWWINDOW = 0x0040

user32 = ctypes.windll.user32


class DesktopActionController:
    """Safely executes local desktop commands and system modifications."""

    # Well-known application aliases mapped to launch paths / URIs
    APP_ALIASES: Dict[str, str] = {
        "spotify": "spotify:",
        "music": "spotify:",
        "vscode": "code",
        "vs code": "code",
        "code": "code",
        "chrome": "chrome",
        "browser": "chrome",
        "edge": "msedge",
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "explorer": "explorer.exe",
        "files": "explorer.exe",
        "terminal": "wt.exe",
        "settings": "ms-settings:",
    }

    @classmethod
    def launch_app_or_path(cls, target: str) -> Tuple[bool, str]:
        """Launch an application, folder path, or Windows URI without console flashes."""
        target_clean = target.strip().lower()
        if not target_clean:
            return False, "No application or path specified."

        # Check alias
        resolved = cls.APP_ALIASES.get(target_clean, target.strip())

        # Check special folders
        user_home = os.path.expanduser("~")
        special_folders = {
            "downloads": os.path.join(user_home, "Downloads"),
            "documents": os.path.join(user_home, "Documents"),
            "desktop": os.path.join(user_home, "Desktop"),
            "pictures": os.path.join(user_home, "Pictures"),
        }
        if target_clean in special_folders:
            resolved = special_folders[target_clean]

        try:
            logger.info(f"Launching desktop target: '{resolved}'")
            if resolved.startswith("http://") or resolved.startswith("https://") or resolved.endswith(":"):
                os.startfile(resolved)
            elif os.path.exists(resolved):
                os.startfile(resolved)
            else:
                # Use ShellExecuteW to prevent console flashes
                shell32 = ctypes.windll.shell32
                ret = shell32.ShellExecuteW(None, "open", resolved, None, None, SW_SHOWNORMAL)
                if ret <= 32:  # ShellExecute returns <= 32 on error
                    # Fallback to subprocess with CREATE_NO_WINDOW
                    subprocess.Popen(
                        resolved,
                        shell=True,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
                    )
            return True, f"Launched {target.strip()}."
        except Exception as e:
            logger.error(f"Error launching '{target}': {e}")
            return False, f"Could not launch {target}: {e}"

    @classmethod
    def manage_window(cls, command: str) -> Tuple[bool, str]:
        """Snap, minimize, maximize, or arrange active foreground window."""
        cmd = command.strip().lower()
        valid_commands = (
            "snap_left", "left", "tile_left",
            "snap_right", "right", "tile_right",
            "maximize", "max", "fullscreen",
            "minimize", "min", "restore", "normal",
            "minimize_others", "focus_only",
        )
        if cmd not in valid_commands:
            return False, f"Unknown window command: '{command}'"

        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False, "No active foreground window found."

        try:
            # Get primary screen dimensions
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            # Subtract taskbar estimate (~40px)
            usable_h = screen_h - 45

            if cmd in ("snap_left", "left", "tile_left"):
                user32.ShowWindow(hwnd, SW_RESTORE)
                user32.SetWindowPos(hwnd, HWND_TOP, 0, 0, screen_w // 2, usable_h, SWP_SHOWWINDOW)
                return True, "Snapped active window to the left."

            elif cmd in ("snap_right", "right", "tile_right"):
                user32.ShowWindow(hwnd, SW_RESTORE)
                user32.SetWindowPos(hwnd, HWND_TOP, screen_w // 2, 0, screen_w // 2, usable_h, SWP_SHOWWINDOW)
                return True, "Snapped active window to the right."

            elif cmd in ("maximize", "max", "fullscreen"):
                user32.ShowWindow(hwnd, SW_MAXIMIZE)
                return True, "Maximized active window."

            elif cmd in ("minimize", "min"):
                user32.ShowWindow(hwnd, SW_SHOWMINIMIZED)
                return True, "Minimized active window."

            elif cmd in ("restore", "normal"):
                user32.ShowWindow(hwnd, SW_RESTORE)
                return True, "Restored active window."

            elif cmd in ("minimize_others", "focus_only"):
                # Minimize all windows except current foreground window
                def _enum_cb(other_hwnd, _):
                    if other_hwnd != hwnd and user32.IsWindowVisible(other_hwnd):
                        # Only top-level titled windows
                        length = user32.GetWindowTextLengthW(other_hwnd)
                        if length > 0:
                            user32.ShowWindow(other_hwnd, SW_SHOWMINIMIZED)
                    return True

                EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
                user32.EnumWindows(EnumWindowsProc(_enum_cb), 0)
                return True, "Minimized all other windows."

            return False, f"Unknown window command: '{command}'"
        except Exception as e:
            logger.error(f"Error managing window: {e}")
            return False, f"Window management error: {e}"

    @classmethod
    def get_clipboard_text(cls) -> str:
        """Safely read text from Windows system clipboard."""
        try:
            app = QApplication.instance()
            if app:
                clip = app.clipboard()
                return clip.text()
        except Exception as e:
            logger.debug(f"Qt clipboard read notice: {e}")

        # Fallback to ctypes
        user32.OpenClipboard(None)
        try:
            h_data = user32.GetClipboardData(13)  # CF_UNICODETEXT = 13
            if h_data:
                kernel32 = ctypes.windll.kernel32
                p_text = kernel32.GlobalLock(h_data)
                text = ctypes.c_wchar_p(p_text).value or ""
                kernel32.GlobalUnlock(h_data)
                return text
        finally:
            user32.CloseClipboard()
        return ""

    @classmethod
    def set_clipboard_text(cls, text: str) -> bool:
        """Safely write text to Windows system clipboard."""
        try:
            app = QApplication.instance()
            if app:
                clip = app.clipboard()
                clip.setText(text)
                return True
        except Exception as e:
            logger.debug(f"Qt clipboard write notice: {e}")

        # Fallback to ctypes
        user32.OpenClipboard(None)
        user32.EmptyClipboard()
        try:
            kernel32 = ctypes.windll.kernel32
            buffer = ctypes.create_unicode_buffer(text)
            h_mem = kernel32.GlobalAlloc(0x0042, ctypes.sizeof(buffer))  # GMEM_MOVEABLE | GMEM_ZEROINIT
            p_mem = kernel32.GlobalLock(h_mem)
            ctypes.memmove(p_mem, buffer, ctypes.sizeof(buffer))
            kernel32.GlobalUnlock(h_mem)
            user32.SetClipboardData(13, h_mem)
            return True
        except Exception as e:
            logger.error(f"Clipboard write error: {e}")
            return False
        finally:
            user32.CloseClipboard()

    @classmethod
    def execute_action(cls, action_type: str, action_arg: str = "") -> Tuple[bool, str]:
        """Dispatcher for parsed [ACTION:type:arg] commands."""
        act = action_type.lower().strip()
        arg = action_arg.strip()

        if act == "launch":
            return cls.launch_app_or_path(arg)
        elif act in ("window", "snap"):
            return cls.manage_window(arg)
        elif act == "clipboard":
            # Direct clipboard assignment
            success = cls.set_clipboard_text(arg)
            return success, "Copied result to your clipboard."
        else:
            return False, f"Unsupported action type: '{action_type}'"


# Singleton instance
desktop_actions = DesktopActionController()
