"""Grok Client wrapper (Alias to AIVisionClient for backward compatibility)."""

from athena.ai_vision_client import (
    AIVisionClient,
    AIVisionResponse,
    GrokClient,
    GrokResponse,
    PointingTarget,
    ATHENA_SYSTEM_PROMPT,
    OFFICIAL_CLICKY_SYSTEM_PROMPT,
)

__all__ = [
    "AIVisionClient",
    "AIVisionResponse",
    "GrokClient",
    "GrokResponse",
    "PointingTarget",
    "ATHENA_SYSTEM_PROMPT",
    "OFFICIAL_CLICKY_SYSTEM_PROMPT",
]
