"""Spidy 3D Scene Specification.

Defines the declarative data structure for interactive 3D WebGL scenes:
- Real-time procedural 3D geometries (gears, engines, DNA, atoms, circuits, solar systems)
- PBR metallic/roughness materials and studio lighting
- Dynamic clip-plane cutaways
- 3D screen-space label callouts
- Zero-compute on-demand rendering loop
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class Scene3DSpec:
    """Declarative specification for an interactive 3D WebGL scene."""
    title: str
    entity: str = "generic"  # "turbofan", "f35", "dna_helix", "differential_gears", "heart_pump", "solar_system", "atom", "neural_net", "robot_arm", "circuit_board", "generic"
    subtitle: str = ""
    cutaway: bool = False
    cutaway_plane: str = "x"
    camera_preset: str = "iso"
    orbit_controls: bool = True
    primitives: List[Dict[str, Any]] = field(default_factory=list)
    callouts: List[Dict[str, Any]] = field(default_factory=list)  # [{"pos": [x, y, z], "label": "..."}]
    animation: str = "spin"  # "spin", "spin_slow", "pulse", "oscillate", "hover", "none"
    anchor_coords: Optional[Tuple[int, int]] = None
    raw_payload: str = ""
    options: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "entity": self.entity,
            "subtitle": self.subtitle,
            "cutaway": self.cutaway,
            "cutaway_plane": self.cutaway_plane,
            "camera_preset": self.camera_preset,
            "orbit_controls": self.orbit_controls,
            "primitives": self.primitives,
            "callouts": self.callouts,
            "animation": self.animation,
            "anchor_coords": self.anchor_coords,
            "options": self.options,
        }
