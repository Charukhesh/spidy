"""Multi-monitor screen capture utility for Spidy Windows.

Captures screenshots as JPEG bytes with explicit pixel dimensions
so vision coordinate space maps 1:1 with screen points.
Includes graceful multi-method fallbacks:
0. Native PyQt5 QScreen (zero-process, instant in-memory capture)
1. mss (Fast desktop capture)
2. PIL.ImageGrab (Pure Python fallback)
3. Fallback canvas if display context is locked/headless
"""

import io
import os
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
        # Method 0: PyQt5 native QScreen grabWindow (Fastest & direct in-memory, ~100ms)
        try:
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtCore import QBuffer

            app = QApplication.instance()
            if app:
                results = []
                screens = app.screens()
                primary_screen = app.primaryScreen()
                for idx, s in enumerate(screens, start=1):
                    pix = s.grabWindow(0)
                    if not pix.isNull():
                        buf = QBuffer()
                        buf.open(QBuffer.WriteOnly)
                        pix.save(buf, "JPEG", quality=75)
                        geom = s.geometry()
                        results.append(
                            ScreenCaptureResult(
                                image_bytes=buf.data().data(),
                                width=pix.width(),
                                height=pix.height(),
                                display_index=idx,
                                is_primary=(s == primary_screen),
                                left=geom.left(),
                                top=geom.top(),
                            )
                        )
                if results:
                    return results
        except Exception as e:
            logger.debug(f"Qt screen grab notice: {e}")

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
                    img.save(buf, format="JPEG", quality=75, optimize=False)
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
            img.save(buf, format="JPEG", quality=75, optimize=False)
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

        # Method 3: Fallback placeholder canvas (for headless/locked background sessions)
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
