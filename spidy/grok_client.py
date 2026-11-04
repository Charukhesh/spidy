"""Grok Client wrapper (Alias to AIVisionClient for backward compatibility)."""

from spidy.ai_vision_client import (
    AIVisionClient,
    AIVisionResponse,
    GrokClient,
    GrokResponse,
    PointingTarget,
    SPIDY_SYSTEM_PROMPT,
    OFFICIAL_CLICKY_SYSTEM_PROMPT,
)

__all__ = [
    "AIVisionClient",
    "AIVisionResponse",
    "GrokClient",
    "GrokResponse",
    "PointingTarget",
    "SPIDY_SYSTEM_PROMPT",
    "OFFICIAL_CLICKY_SYSTEM_PROMPT",
]
