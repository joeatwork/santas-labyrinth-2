"""
NPC entity for dungeon interactions.

NPCs have a fixed position and can be interacted with to trigger conversations.
"""

import math
from dataclasses import dataclass
from typing import Optional

from .conversation import ConversationEngine

TILE_SIZE: int = 64


@dataclass
class NPC:
    """
    A non-player character in the dungeon.

    NPCs have a fixed position and can be interacted with to trigger conversations.
    The hero's strategy decides when to interact with an NPC.

    For large NPCs (like the robot priest), the sprite may be larger than the
    logical base. The base_width and base_height define the footprint that
    blocks movement, while sprite_width and sprite_height define the visual size.

    Position (x, y) is the center of the logical base, not the sprite center.
    For a 128x192 sprite with a 128x64 base, the sprite extends 128 pixels
    above the base center.
    """

    # Position in pixels (center of logical base)
    x: float
    y: float

    # Visual state
    sprite_name: str  # Key into AssetManager sprites (e.g., 'npc_default')
    direction: int = 1  # 0=East, 1=South, 2=West, 3=North (default facing south)

    # Sprite dimensions (for rendering)
    sprite_width: int = 64
    sprite_height: int = 64

    # Logical base dimensions (for collision/interaction)
    # Default to sprite size for backwards compatibility
    base_width: int = 64
    base_height: int = 64

    # Conversation to trigger on interaction
    conversation_engine: Optional[ConversationEngine] = None

    # Unique identifier for tracking interaction state
    npc_id: str = ""

    # Room assignment (set by Dungeon when placed)
    room_id: Optional[int] = None

    @property
    def tile_col(self) -> int:
        """Get the leftmost tile column of this NPC's base."""
        # x is center of base, so leftmost tile is at x - base_width/2
        left_edge = self.x - self.base_width / 2
        return int(left_edge / TILE_SIZE)

    @property
    def tile_row(self) -> int:
        """Get the topmost tile row of this NPC's base."""
        # y is center of base, so topmost tile is at y - base_height/2
        top_edge = self.y - self.base_height / 2
        return int(top_edge / TILE_SIZE)

    @property
    def base_tile_width(self) -> int:
        """Number of tiles wide the base occupies."""
        return max(1, self.base_width // TILE_SIZE)

    @property
    def base_tile_height(self) -> int:
        """Number of tiles tall the base occupies."""
        return max(1, self.base_height // TILE_SIZE)

    def occupies_tile(self, row: int, col: int) -> bool:
        """Check if this NPC's base occupies the given tile."""
        return (
            self.tile_col <= col < self.tile_col + self.base_tile_width
            and self.tile_row <= row < self.tile_row + self.base_tile_height
        )
