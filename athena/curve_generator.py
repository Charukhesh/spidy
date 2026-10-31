"""Mathematical Curve and Visual Trajectory Generator for Athena.

Generates smooth 2D polylines for mathematical functions, geometric curves,
and visual demonstrations centered directly around a specified anchor point
(e.g., the user's current mouse cursor position).
"""

import math
from typing import List, Tuple, Dict, Any, Optional
from PyQt5.QtCore import QPointF


class CurveGenerator:
    """Generates coordinate arrays for mathematical functions and visual trajectories."""

    @staticmethod
    def generate_curve(
        curve_type: str,
        center_x: float,
        center_y: float,
        width: float = 280.0,
        height: float = 160.0,
        num_samples: int = 70,
    ) -> List[Tuple[float, float]]:
        """Generate a list of (x, y) global screen coordinates for a given curve type.
        
        Args:
            curve_type: Type of curve ('cubic', 'parabola', 'quadratic', 'sine', 'cosine',
                        'bell', 'gaussian', 'spiral', 'circle', 'heart', 'exponential', 'log')
            center_x: Global screen X coordinate of origin/center (e.g. mouse cursor X)
            center_y: Global screen Y coordinate of origin/center (e.g. mouse cursor Y)
            width: Horizontal span in pixels
            height: Vertical span in pixels
            num_samples: Number of discrete interpolation points along the curve
            
        Returns:
            List of (x, y) global coordinates
        """
        c_type = curve_type.lower().strip()
        points: List[Tuple[float, float]] = []

        half_w = width / 2.0
        half_h = height / 2.0

        if c_type in ("cubic", "cubic_curve", "x^3", "x3"):
            # y = x^3 normalized: x in [-1, 1], y in [-1, 1]
            # In screen coords: y is inverted (top is negative)
            for i in range(num_samples):
                t = i / (num_samples - 1)  # 0 .. 1
                norm_x = (t * 2.0) - 1.0   # -1 .. 1
                norm_y = norm_x ** 3       # -1 .. 1
                
                screen_x = center_x + (norm_x * half_w)
                screen_y = center_y - (norm_y * half_h)  # inverted for screen
                points.append((screen_x, screen_y))

        elif c_type in ("parabola", "quadratic", "x^2", "x2"):
            # y = x^2 normalized: x in [-1, 1], y in [0, 1]
            for i in range(num_samples):
                t = i / (num_samples - 1)
                norm_x = (t * 2.0) - 1.0
                norm_y = (norm_x ** 2) * 2.0 - 1.0  # mapped to [-1, 1]
                
                screen_x = center_x + (norm_x * half_w)
                screen_y = center_y - (norm_y * half_h)
                points.append((screen_x, screen_y))

        elif c_type in ("sine", "sin", "wave"):
            # y = sin(2*pi*x), 1.5 cycles
            for i in range(num_samples):
                t = i / (num_samples - 1)
                norm_x = (t * 2.0) - 1.0
                angle = norm_x * math.pi * 1.5
                norm_y = math.sin(angle)
                
                screen_x = center_x + (norm_x * half_w)
                screen_y = center_y - (norm_y * half_h)
                points.append((screen_x, screen_y))

        elif c_type in ("cosine", "cos"):
            for i in range(num_samples):
                t = i / (num_samples - 1)
                norm_x = (t * 2.0) - 1.0
                angle = norm_x * math.pi * 1.5
                norm_y = math.cos(angle)
                
                screen_x = center_x + (norm_x * half_w)
                screen_y = center_y - (norm_y * half_h)
                points.append((screen_x, screen_y))

        elif c_type in ("bell", "gaussian", "normal", "distribution"):
            # Gaussian bell curve: y = exp(-3.5 * x^2)
            for i in range(num_samples):
                t = i / (num_samples - 1)
                norm_x = (t * 2.0) - 1.0
                norm_y = math.exp(-3.5 * (norm_x ** 2)) * 2.0 - 1.0
                
                screen_x = center_x + (norm_x * half_w)
                screen_y = center_y - (norm_y * half_h)
                points.append((screen_x, screen_y))

        elif c_type in ("spiral", "archimedean"):
            # Archimedean spiral: r = a * theta
            max_theta = 3.5 * math.pi
            for i in range(num_samples):
                t = i / (num_samples - 1)
                theta = t * max_theta
                r = (t * half_w * 0.9)
                screen_x = center_x + (r * math.cos(theta))
                screen_y = center_y + (r * math.sin(theta))
                points.append((screen_x, screen_y))

        elif c_type in ("circle", "loop"):
            for i in range(num_samples):
                t = i / (num_samples - 1)
                angle = t * 2.0 * math.pi
                r = min(half_w, half_h) * 0.85
                screen_x = center_x + (r * math.cos(angle))
                screen_y = center_y + (r * math.sin(angle))
                points.append((screen_x, screen_y))

        elif c_type in ("heart", "cardioid"):
            # Parametric heart: x = 16 sin^3(t), y = 13 cos(t) - 5 cos(2t) - 2 cos(3t) - cos(4t)
            scale = min(half_w, half_h) / 18.0
            for i in range(num_samples):
                t = (i / (num_samples - 1)) * 2.0 * math.pi
                hx = 16.0 * (math.sin(t) ** 3)
                hy = (
                    13.0 * math.cos(t)
                    - 5.0 * math.cos(2.0 * t)
                    - 2.0 * math.cos(3.0 * t)
                    - math.cos(4.0 * t)
                )
                screen_x = center_x + (hx * scale)
                screen_y = center_y - (hy * scale)
                points.append((screen_x, screen_y))

        elif c_type in ("exponential", "exp"):
            # y = e^x - 1 normalized
            for i in range(num_samples):
                t = i / (num_samples - 1)
                norm_x = (t * 2.0) - 1.0  # -1 .. 1
                norm_y = (math.exp(norm_x * 1.5) - 0.22) / 4.2 * 2.0 - 1.0
                screen_x = center_x + (norm_x * half_w)
                screen_y = center_y - (norm_y * half_h)
                points.append((screen_x, screen_y))

        else:
            # Default fallback to smooth S-curve
            for i in range(num_samples):
                t = i / (num_samples - 1)
                norm_x = (t * 2.0) - 1.0
                norm_y = norm_x ** 3
                screen_x = center_x + (norm_x * half_w)
                screen_y = center_y - (norm_y * half_h)
                points.append((screen_x, screen_y))

        return points

    @staticmethod
    def parse_curve_identifier(query_or_label: str) -> Optional[str]:
        """Detect which curve type is implied by user query or label."""
        text = query_or_label.lower()
        if any(w in text for w in ("cubic", "x^3", "x3", "s curve", "s-curve")):
            return "cubic"
        if any(w in text for w in ("parabola", "quadratic", "x^2", "x2")):
            return "parabola"
        if any(w in text for w in ("sine", "sin wave", "wave", "cosine", "cos")):
            return "sine"
        if any(w in text for w in ("bell", "gaussian", "normal distribution", "bell curve")):
            return "bell"
        if any(w in text for w in ("spiral", "vortex")):
            return "spiral"
        if any(w in text for w in ("circle", "loop", "oval")):
            return "circle"
        if any(w in text for w in ("heart", "love")):
            return "heart"
        if any(w in text for w in ("exponential", "exp")):
            return "exponential"
        return None

