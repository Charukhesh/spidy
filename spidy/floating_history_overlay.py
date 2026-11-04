"""Backward compatibility alias for Spidy TopBarGlassHUD.
Redirects FloatingHistoryCard to TopBarGlassHUD.
"""

from spidy.top_bar_hud import TopBarGlassHUD, TopBarState

# Backward compatibility alias
FloatingHistoryCard = TopBarGlassHUD

__all__ = ["TopBarGlassHUD", "FloatingHistoryCard", "TopBarState"]
