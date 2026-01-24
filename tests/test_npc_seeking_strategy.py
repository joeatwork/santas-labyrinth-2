"""Unit tests for NPCSeekingStrategy."""

import pytest

from dungeon.npc import NPC, TILE_SIZE
from dungeon.strategy import NPCSeekingStrategy, MoveCommand, InteractCommand
from dungeon.conversation import ConversationPage, ScriptedConversation
from dungeon.world import Dungeon
from dungeon.dungeon_gen import create_random_dungeon


def make_test_conversation():
    """Create a simple conversation for testing."""
    return ScriptedConversation(
        [ConversationPage(text="Hello!", speaker="npc")]
    )


class TestNPCSeekingStrategy:
    """Tests for NPCSeekingStrategy."""

    def test_returns_interact_when_adjacent_to_npc(self):
        """Strategy returns InteractCommand when hero is adjacent to NPC."""
        dungeon = create_random_dungeon(num_rooms=2)

        # Place NPC in room 1
        npc_col, npc_row = 5, 5
        npc = NPC(
            x=npc_col * TILE_SIZE + TILE_SIZE / 2,
            y=npc_row * TILE_SIZE + TILE_SIZE / 2,
            sprite_name="npc_default",
            conversation_engine=make_test_conversation(),
        )
        dungeon.add_npc(npc)

        strategy = NPCSeekingStrategy(target_npc=npc)

        # Place hero adjacent to NPC (one tile south)
        hero_x = npc_col * TILE_SIZE + TILE_SIZE / 2
        hero_y = (npc_row + 1) * TILE_SIZE + TILE_SIZE / 2

        # Ensure the tile is walkable for the test
        if not dungeon.is_tile_walkable(npc_row + 1, npc_col):
            pytest.skip("Test tile not walkable in generated dungeon")

        command = strategy.decide_next_move(hero_x, hero_y, dungeon)

        assert isinstance(command, InteractCommand)
        assert command.npc is npc

    def test_returns_move_when_not_adjacent(self):
        """Strategy returns MoveCommand when hero is not adjacent to NPC."""
        dungeon = create_random_dungeon(num_rooms=5)

        # Place NPC somewhere in the dungeon
        # Find a suitable floor tile first
        from dungeon.dungeon_gen import Tile

        npc_col, npc_row = None, None
        for row in range(dungeon.rows):
            for col in range(dungeon.cols):
                if dungeon.map[row, col] == Tile.FLOOR:
                    # Check there's an adjacent floor tile
                    if dungeon.is_tile_walkable(row + 1, col):
                        npc_col, npc_row = col, row
                        break
            if npc_col is not None:
                break

        if npc_col is None:
            pytest.skip("Could not find suitable NPC position")

        npc = NPC(
            x=npc_col * TILE_SIZE + TILE_SIZE / 2,
            y=npc_row * TILE_SIZE + TILE_SIZE / 2,
            sprite_name="npc_default",
            conversation_engine=make_test_conversation(),
        )
        dungeon.add_npc(npc)

        strategy = NPCSeekingStrategy(target_npc=npc)

        # Hero starts at dungeon start position (likely far from NPC)
        hero_x, hero_y = dungeon.start_pos

        # If hero happens to be adjacent to NPC, skip
        hero_row = int(hero_y / TILE_SIZE)
        hero_col = int(hero_x / TILE_SIZE)
        if dungeon.is_adjacent_to_npc(hero_row, hero_col, npc):
            pytest.skip("Hero starts adjacent to NPC")

        command = strategy.decide_next_move(hero_x, hero_y, dungeon)

        assert isinstance(command, MoveCommand)

    def test_delegates_to_goal_after_interaction(self):
        """After interacting, strategy delegates to GoalSeekingStrategy."""
        dungeon = create_random_dungeon(num_rooms=2)

        npc = NPC(
            x=100.0,
            y=100.0,
            sprite_name="npc_default",
            conversation_engine=make_test_conversation(),
        )

        strategy = NPCSeekingStrategy(target_npc=npc)

        # Simulate that interaction already happened
        strategy.has_interacted = True

        # Now the strategy should delegate to goal seeking
        hero_x, hero_y = dungeon.start_pos
        command = strategy.decide_next_move(hero_x, hero_y, dungeon)

        # Should get a MoveCommand toward the goal (not InteractCommand)
        assert command is None or isinstance(command, MoveCommand)

    def test_adjacent_to_multi_tile_npc(self):
        """Strategy can interact with multi-tile NPCs from any adjacent tile."""
        dungeon = create_random_dungeon(num_rooms=5)

        # Find a good position for a 2-tile-wide NPC
        from dungeon.dungeon_gen import Tile

        npc_col, npc_row = None, None
        for row in range(2, dungeon.rows - 2):
            for col in range(2, dungeon.cols - 2):
                # Need two adjacent floor tiles for the NPC base
                if (dungeon.map[row, col] == Tile.FLOOR and
                    dungeon.map[row, col + 1] == Tile.FLOOR):
                    # And a walkable tile south of one of them
                    if dungeon.is_tile_walkable(row + 1, col):
                        npc_col, npc_row = col, row
                        break
            if npc_col is not None:
                break

        if npc_col is None:
            pytest.skip("Could not find suitable position for 2-tile NPC")

        # Create 2-tile-wide NPC
        npc = NPC(
            x=npc_col * TILE_SIZE + TILE_SIZE,  # Center of 2 tiles
            y=npc_row * TILE_SIZE + TILE_SIZE / 2,
            sprite_name="robot_priest",
            base_width=128,
            base_height=64,
            conversation_engine=make_test_conversation(),
        )
        dungeon.add_npc(npc)

        strategy = NPCSeekingStrategy(target_npc=npc)

        # Place hero south of the left tile of the NPC
        hero_x = npc_col * TILE_SIZE + TILE_SIZE / 2
        hero_y = (npc_row + 1) * TILE_SIZE + TILE_SIZE / 2

        command = strategy.decide_next_move(hero_x, hero_y, dungeon)

        assert isinstance(command, InteractCommand)
        assert command.npc is npc
