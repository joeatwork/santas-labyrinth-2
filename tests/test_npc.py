"""Unit tests for NPC entity."""

import pytest

from dungeon.npc import NPC, distance_to_npc, TILE_SIZE
from dungeon.conversation import ConversationPage, ScriptedConversation


def make_test_conversation():
    """Create a simple conversation for testing."""
    return ScriptedConversation([
        ConversationPage(text="Hello!", speaker="npc"),
    ])


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
