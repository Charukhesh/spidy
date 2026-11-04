"""Visual Scratchpad & High-Resolution OCR Extraction Engine for Spidy.

Provides:
1. Focal Mouse Cropping: Crops high-resolution regions around the mouse cursor for target OCR.
2. Uncopyable Text Extraction: Extracts text from images, video frames, and locked UI fields.
3. Diagram-to-Code: Converts on-screen diagrams to Mermaid.js code.
4. Table-to-Markdown: Converts on-screen tables into clean Markdown or CSV.
5. Instant Clipboard Sync: Directly loads extracted content onto the Windows clipboard.
"""

import io
import logging
from typing import List, Optional, Tuple
from PIL import Image

from spidy.screen_capture import ScreenCaptureResult
from spidy.desktop_actions import desktop_actions
from spidy.sound_effects import sounds

logger = logging.getLogger("spidy.scratchpad")


class VisualScratchpad:
    """Handles mouse-centric visual crops and structured OCR data extraction."""

    @staticmethod
    def crop_region_around_point(
        screen_captures: List[ScreenCaptureResult],
        global_x: int,
        global_y: int,
        crop_width: int = 480,
        crop_height: int = 320,
    ) -> Optional[bytes]:
        """Crop a high-resolution sub-rectangle centered around (global_x, global_y)."""
        if not screen_captures:
            return None

        # 1. Identify which monitor contains (global_x, global_y)
        target_cap = None
        for cap in screen_captures:
            if (cap.left <= global_x < cap.left + cap.width) and (cap.top <= global_y < cap.top + cap.height):
                target_cap = cap
                break

        # Fallback to primary screen
        if not target_cap:
            target_cap = next((c for c in screen_captures if c.is_primary), screen_captures[0])

        try:
            # Load full image from capture bytes
            img = Image.open(io.BytesIO(target_cap.image_bytes))

            # Convert global coords to screen-local coords
            local_x = global_x - target_cap.left
            local_y = global_y - target_cap.top

            # Calculate crop box clamped to screen boundaries
            half_w = crop_width // 2
            half_h = crop_height // 2

            left = max(0, local_x - half_w)
            top = max(0, local_y - half_h)
            right = min(target_cap.width, left + crop_width)
            bottom = min(target_cap.height, top + crop_height)

            # Adjust if near right or bottom edge
            if right - left < crop_width:
                left = max(0, right - crop_width)
            if bottom - top < crop_height:
                top = max(0, bottom - crop_height)

            cropped = img.crop((left, top, right, bottom))

            # Encode to JPEG
            out_buf = io.BytesIO()
            cropped.save(out_buf, format="JPEG", quality=95)
            logger.info(f"Cropped focal region ({crop_width}x{crop_height}) around ({global_x}, {global_y})")
            return out_buf.getvalue()

        except Exception as e:
            logger.error(f"Error cropping focal screen region: {e}")
            return None

    @staticmethod
    def load_extracted_to_clipboard(text: str) -> bool:
        """Place extracted text onto Windows clipboard and play subtle arrival sound."""
        clean_text = text.strip()
        if not clean_text:
            return False
        success = desktop_actions.set_clipboard_text(clean_text)
        if success:
            sounds.play_arrival()
            logger.info(f"Loaded {len(clean_text)} characters onto clipboard via Visual Scratchpad.")
        return success


# Singleton instance
scratchpad = VisualScratchpad()

