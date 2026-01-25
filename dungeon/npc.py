"""
NPC entity for dungeon interactions.

NPCs have a fixed position and can be interacted with to trigger conversations.
"""

import math
from dataclasses import dataclass, field
from typing import Optional, Callable

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

    The sprite attributes (width, height, offsets) are automatically extracted
    from SPRITE_OFFSETS based on sprite_name. Base dimensions must be provided
    explicitly as they define the logical footprint, not the visual appearance.
    """

    # Position in pixels (center of logical base)
    x: float
    y: float

    # Visual state
    sprite_name: str  # Key into AssetManager sprites (e.g., 'npc_default')
    direction: int = 1  # 0=East, 1=South, 2=West, 3=North (default facing south)

    # Logical base dimensions (for collision/interaction)
    base_width: int = field(init=False)
    base_height: int = field(init=False)

    # Sprite dimensions (for rendering) - auto-populated from sprite_name
    sprite_width: int = field(init=False)
    sprite_height: int = field(init=False)

    # Offsets - auto-populated from sprite_name
    sprite_offset_x: int = field(init=False)
    sprite_offset_y: int = field(init=False)

    # Conversation to trigger on interaction
    conversation_engine: Optional[ConversationEngine] = None

    # Callback invoked when conversation with this NPC completes
    # Receives no arguments; use closure to capture needed state
    # TODO: should on_conversation_complete live in a ConversationEngine?
    on_conversation_complete: Optional[Callable[[], None]] = field(default=None, repr=False)

    # Callback invoked when the hero interacts with this NPC (before conversation starts)
    # For NPCs without conversation_engine (like Goal), this handles the interaction
    # Receives no arguments; use closure to capture needed state
    on_interact: Optional[Callable[[], None]] = field(default=None, repr=False)

    # Unique identifier for tracking interaction state
    npc_id: str = ""

    # Whether this NPC is the goal (special handling for goal-seeking strategy)
    is_goal: bool = False

    # Room assignment (set by Dungeon when placed)
    room_id: Optional[int] = None

    def __post_init__(self) -> None:
        """Extract sprite attributes from SPRITE_OFFSETS."""
        from .animation import SPRITE_OFFSETS

        if self.sprite_name not in SPRITE_OFFSETS:
            raise KeyError(f"Sprite '{self.sprite_name}' not found in SPRITE_OFFSETS")

        cfg = SPRITE_OFFSETS[self.sprite_name]
        self.sprite_width = cfg["w"]
        self.sprite_height = cfg["h"]
        self.base_width = cfg.get("base_width", 64)
        self.base_height = cfg.get("base_height", 64)
        self.sprite_offset_x = cfg.get("offset_x", 0)
        self.sprite_offset_y = cfg.get("offset_y", 0)

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
