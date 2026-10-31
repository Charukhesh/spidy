"""Backward compatibility alias for Athena TopBarGlassHUD.
Redirects FloatingHistoryCard to TopBarGlassHUD.
"""

from athena.top_bar_hud import TopBarGlassHUD, TopBarState

# Backward compatibility alias
FloatingHistoryCard = TopBarGlassHUD

__all__ = ["TopBarGlassHUD", "FloatingHistoryCard", "TopBarState"]
