"""Unit tests for NPC entity."""

import pytest
import math

from dungeon.npc import NPC, TILE_SIZE
from dungeon.conversation import ConversationPage, ScriptedConversation


def distance_to_npc(hero_x: float, hero_y: float, npc: NPC) -> float:
    """Calculate Euclidean distance from a position to an NPC."""
    dx = npc.x - hero_x
    dy = npc.y - hero_y
    return math.sqrt(dx * dx + dy * dy)


def make_test_conversation():
    """Create a simple conversation for testing."""
    return ScriptedConversation(
        [
            ConversationPage(text="Hello!", speaker="npc"),
        ]
    )


class TestNPC:
    """Tests for NPC dataclass."""

    def test_npc_has_position(self):
        """NPC has x and y pixel coordinates."""
        npc = NPC(x=100.0, y=200.0, sprite_name="npc_default")
        assert npc.x == 100.0
        assert npc.y == 200.0

    def test_npc_default_direction(self):
        """NPC defaults to facing south (direction=1)."""
        npc = NPC(x=100.0, y=200.0, sprite_name="npc_default")
        assert npc.direction == 1

    def test_npc_default_sprite_size(self):
        """NPC defaults to 64x64 sprite size."""
        npc = NPC(x=100.0, y=200.0, sprite_name="npc_default")
        assert npc.sprite_width == 64
        assert npc.sprite_height == 64

    def test_npc_custom_sprite_size(self):
        """NPC accepts custom sprite dimensions."""
        npc = NPC(
            x=100.0,
            y=200.0,
            sprite_name="big_npc",
            sprite_width=128,
            sprite_height=96,
        )
        assert npc.sprite_width == 128
        assert npc.sprite_height == 96

    def test_npc_tile_position(self):
        """NPC calculates tile position from pixel position."""
        # Center of tile (3, 5)
        x = 5 * TILE_SIZE + TILE_SIZE / 2  # col 5
        y = 3 * TILE_SIZE + TILE_SIZE / 2  # row 3
        npc = NPC(x=x, y=y, sprite_name="npc_default")

        assert npc.tile_col == 5
        assert npc.tile_row == 3

    def test_npc_conversation_engine(self):
        """NPC can have a conversation engine."""
        conv = make_test_conversation()
        npc = NPC(
            x=100.0,
            y=200.0,
            sprite_name="npc_default",
            conversation_engine=conv,
        )
        assert npc.conversation_engine is conv

    def test_npc_optional_id(self):
        """NPC has optional npc_id for tracking."""
        npc = NPC(x=100.0, y=200.0, sprite_name="npc_default")
        assert npc.npc_id == ""

        npc_with_id = NPC(
            x=100.0, y=200.0, sprite_name="npc_default", npc_id="wizard_1"
        )
        assert npc_with_id.npc_id == "wizard_1"


class TestMultiTileNPC:
    """Tests for multi-tile NPC support."""

    def test_default_base_size_matches_sprite(self):
        """By default, base size equals sprite size for backwards compatibility."""
        npc = NPC(x=100.0, y=100.0, sprite_name="npc_default")
        assert npc.base_width == 64
        assert npc.base_height == 64

    def test_custom_base_size(self):
        """NPC can have different base and sprite sizes."""
        npc = NPC(
            x=100.0,
            y=100.0,
            sprite_name="robot_priest",
            sprite_width=128,
            sprite_height=192,
            base_width=128,
            base_height=64,
        )
        assert npc.sprite_width == 128
        assert npc.sprite_height == 192
        assert npc.base_width == 128
        assert npc.base_height == 64

    def test_base_tile_dimensions(self):
        """NPC calculates base tile dimensions correctly."""
        # 128x64 base = 2 tiles wide, 1 tile tall
        npc = NPC(
            x=128.0,  # Center of 2-tile-wide base
            y=32.0,   # Center of 1-tile-tall base
            sprite_name="robot_priest",
            base_width=128,
            base_height=64,
        )
        assert npc.base_tile_width == 2
        assert npc.base_tile_height == 1

    def test_tile_col_for_multi_tile_npc(self):
        """tile_col returns leftmost tile for multi-tile NPC."""
        # Position center of 2-tile base at x=128 (center of tiles 0 and 1)
        npc = NPC(
            x=TILE_SIZE,  # 64 - center of 128-wide base starting at x=0
            y=TILE_SIZE / 2,
            sprite_name="robot_priest",
            base_width=128,
            base_height=64,
        )
        assert npc.tile_col == 0  # Leftmost tile

    def test_occupies_tile_single_tile(self):
        """Single-tile NPC occupies only its tile."""
        # Center of tile (2, 3)
        x = 3 * TILE_SIZE + TILE_SIZE / 2
        y = 2 * TILE_SIZE + TILE_SIZE / 2
        npc = NPC(x=x, y=y, sprite_name="npc_default")

        assert npc.occupies_tile(2, 3) is True
        assert npc.occupies_tile(2, 2) is False
        assert npc.occupies_tile(2, 4) is False
        assert npc.occupies_tile(1, 3) is False
        assert npc.occupies_tile(3, 3) is False

    def test_occupies_tile_multi_tile(self):
        """Multi-tile NPC occupies all base tiles."""
        # 2-tile-wide NPC at tiles (3, 4) and (3, 5)
        x = 4 * TILE_SIZE + TILE_SIZE  # Center of tiles 4 and 5
        y = 3 * TILE_SIZE + TILE_SIZE / 2  # Center of row 3
        npc = NPC(
            x=x,
            y=y,
            sprite_name="robot_priest",
            base_width=128,
            base_height=64,
        )

        # Should occupy tiles (3, 4) and (3, 5)
        assert npc.occupies_tile(3, 4) is True
        assert npc.occupies_tile(3, 5) is True
        # Should not occupy adjacent tiles
        assert npc.occupies_tile(3, 3) is False
        assert npc.occupies_tile(3, 6) is False
        assert npc.occupies_tile(2, 4) is False
        assert npc.occupies_tile(4, 4) is False


class TestDistanceToNPC:
    """Tests for distance_to_npc function."""

    def test_distance_zero_at_npc_position(self):
        """Distance is zero when at NPC position."""
        npc = NPC(x=100.0, y=100.0, sprite_name="npc_default")
        assert distance_to_npc(100.0, 100.0, npc) == 0.0

    def test_distance_horizontal(self):
        """Distance is correct for horizontal offset."""
        npc = NPC(x=100.0, y=100.0, sprite_name="npc_default")
        assert distance_to_npc(200.0, 100.0, npc) == 100.0

    def test_distance_vertical(self):
        """Distance is correct for vertical offset."""
        npc = NPC(x=100.0, y=100.0, sprite_name="npc_default")
        assert distance_to_npc(100.0, 200.0, npc) == 100.0

    def test_distance_diagonal(self):
        """Distance is correct for diagonal offset (3-4-5 triangle)."""
        npc = NPC(x=100.0, y=100.0, sprite_name="npc_default")
        # 3-4-5 triangle: distance should be 5
        dist = distance_to_npc(103.0, 104.0, npc)
        assert abs(dist - 5.0) < 0.001
