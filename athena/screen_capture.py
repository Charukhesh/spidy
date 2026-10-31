"""Multi-monitor screen capture utility for Clicky Windows.

Captures screenshots as JPEG bytes with explicit pixel dimensions
so Grok's vision coordinate space maps 1:1 with screen points.
Includes graceful multi-method fallbacks:
1. mss (Fastest native desktop capture)
2. PIL.ImageGrab
3. Windows PowerShell System.Drawing
4. Fallback canvas if display context is locked/headless
"""

import io
import os
import subprocess
import logging
from dataclasses import dataclass
from typing import List, Optional
from PIL import Image

logger = logging.getLogger("clicky.screen_capture")


@dataclass
class ScreenCaptureResult:
    image_bytes: bytes
    width: int
    height: int
    display_index: int
    is_primary: bool
    left: int
    top: int


class ScreenCaptureUtility:
    """Robust multi-monitor screenshot capture with multi-tier fallbacks."""

    @classmethod
    def capture_all_screens(cls) -> List[ScreenCaptureResult]:
        # Method 1: mss
        try:
            import mss

            results = []
            with mss.mss() as sct:
                monitors = sct.monitors[1:] if len(sct.monitors) > 1 else sct.monitors
                for idx, monitor in enumerate(monitors, start=1):
                    sct_img = sct.grab(monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=85, optimize=True)
                    results.append(
                        ScreenCaptureResult(
                            image_bytes=buf.getvalue(),
                            width=img.width,
                            height=img.height,
                            display_index=idx,
                            is_primary=(idx == 1),
                            left=monitor["left"],
                            top=monitor["top"],
                        )
                    )
            if results:
                return results
        except Exception as e:
            logger.debug(f"mss capture notice: {e}")

        # Method 2: PIL.ImageGrab
        try:
            from PIL import ImageGrab

            img = ImageGrab.grab(all_screens=True)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85, optimize=True)
            return [
                ScreenCaptureResult(
                    image_bytes=buf.getvalue(),
                    width=img.width,
                    height=img.height,
                    display_index=1,
                    is_primary=True,
                    left=0,
                    top=0,
                )
            ]
        except Exception as e:
            logger.debug(f"ImageGrab capture notice: {e}")

        # Method 3: PowerShell System.Drawing
        try:
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                tmp_path = tf.name

            ps_cmd = f"""
Add-Type -AssemblyName System.Drawing, System.Windows.Forms
$bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($bounds.Left, $bounds.Top, 0, 0, $bmp.Size)
$bmp.Save('{tmp_path.replace("'", "''")}')
$g.Dispose()
$bmp.Dispose()
"""
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                timeout=5,
            )

            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 100:
                with Image.open(tmp_path) as img:
                    buf = io.BytesIO()
                    img.convert("RGB").save(buf, format="JPEG", quality=85)
                    w, h = img.size
                os.remove(tmp_path)
                return [
                    ScreenCaptureResult(
                        image_bytes=buf.getvalue(),
                        width=w,
                        height=h,
                        display_index=1,
                        is_primary=True,
                        left=0,
                        top=0,
                    )
                ]
        except Exception as e:
            logger.debug(f"PowerShell capture notice: {e}")

        # Method 4: Fallback placeholder canvas (for headless/locked background sessions)
        logger.warning("Using fallback canvas for screen context.")
        w, h = 1920, 1080
        img = Image.new("RGB", (w, h), color=(30, 30, 35))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return [
            ScreenCaptureResult(
                image_bytes=buf.getvalue(),
                width=w,
                height=h,
                display_index=1,
                is_primary=True,
                left=0,
                top=0,
            )
        ]
