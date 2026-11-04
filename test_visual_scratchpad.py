"""Automated Unit Tests for Spidy Visual Scratchpad & Focal OCR Cropper."""

import sys
import io
import unittest
from pathlib import Path
from PIL import Image

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt5.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from spidy.screen_capture import ScreenCaptureResult
from spidy.visual_scratchpad import scratchpad, VisualScratchpad
from spidy.desktop_actions import desktop_actions


class TestVisualScratchpad(unittest.TestCase):

    def setUp(self):
        # Create synthetic 1920x1080 image
        img = Image.new("RGB", (1920, 1080), color=(30, 30, 40))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        self.mock_cap = ScreenCaptureResult(
            image_bytes=buf.getvalue(),
            width=1920,
            height=1080,
            left=0,
            top=0,
            display_index=1,
            is_primary=True,
        )

    def test_01_crop_around_point_dimensions(self):
        """Verify focal cropping centered at mouse cursor produces correct resolution."""
        crop_bytes = scratchpad.crop_region_around_point([self.mock_cap], global_x=500, global_y=400, crop_width=400, crop_height=250)
        self.assertIsNotNone(crop_bytes)

        # Verify cropped image dimensions
        cropped_img = Image.open(io.BytesIO(crop_bytes))
        self.assertEqual(cropped_img.size, (400, 250))

    def test_02_crop_near_edges_clamping(self):
        """Verify edge clamping when cursor is near top-left screen boundary."""
        crop_bytes = scratchpad.crop_region_around_point([self.mock_cap], global_x=10, global_y=10, crop_width=300, crop_height=200)
        self.assertIsNotNone(crop_bytes)

        cropped_img = Image.open(io.BytesIO(crop_bytes))
        self.assertEqual(cropped_img.size, (300, 200))

    def test_03_load_extracted_to_clipboard(self):
        """Verify clipboard loading with arrival chime."""
        text = "Extracted table data: | Col1 | Col2 |\n| Val1 | Val2 |"
        ok = scratchpad.load_extracted_to_clipboard(text)
        self.assertTrue(ok)
        self.assertEqual(desktop_actions.get_clipboard_text(), text)


if __name__ == "__main__":
    unittest.main()

