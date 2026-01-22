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
    """

    # Position in pixels (center of sprite)
    x: float
    y: float

    # Visual state
    sprite_name: str  # Key into AssetManager sprites (e.g., 'npc_default')
    direction: int = 1  # 0=East, 1=South, 2=West, 3=North (default facing south)

    # Sprite dimensions (support non-square NPCs)
    sprite_width: int = 64
    sprite_height: int = 64

    # Conversation to trigger on interaction
    conversation_engine: Optional[ConversationEngine] = None

    # Unique identifier for tracking interaction state
    npc_id: str = ""

    # Room assignment (set by Dungeon when placed)
    room_id: Optional[int] = None

    @property
    def tile_col(self) -> int:
        """Get the tile column this NPC is in."""
        return int(self.x / TILE_SIZE)

    @property
    def tile_row(self) -> int:
        """Get the tile row this NPC is in."""
        return int(self.y / TILE_SIZE)


def distance_to_npc(hero_x: float, hero_y: float, npc: NPC) -> float:
    """Calculate Euclidean distance from a position to an NPC."""
    dx = npc.x - hero_x
    dy = npc.y - hero_y
    return math.sqrt(dx * dx + dy * dy)
