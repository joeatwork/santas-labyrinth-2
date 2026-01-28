"""Tests for dynamic goal placement and strategy reset."""

import pytest
import numpy as np

from dungeon.world import TILE_SIZE
from dungeon.strategy import GoalSeekingStrategy
from dungeon.setup import create_dungeon_with_priest


class TestStrategyReset:
    """Test GoalSeekingStrategy.reset_search_state()."""

    def test_reset_clears_lru_doors(self):
        """reset_search_state should clear the LRU door tracking."""
        strategy = GoalSeekingStrategy()

        # Simulate some door tracking
        strategy.lru_doors[(5, 10)] = None
        strategy.lru_doors[(3, 8)] = None
        assert len(strategy.lru_doors) == 2

        strategy.reset_search_state()

        assert len(strategy.lru_doors) == 0

    def test_reset_clears_path_state(self):
        """reset_search_state should clear path and goal state."""
        strategy = GoalSeekingStrategy()

        # Set some state
        strategy.next_goal_row = 10
        strategy.next_goal_col = 5
        strategy.current_path = [(1, 2), (3, 4)]
        strategy.path_index = 1
        strategy._path_target = (10, 5)

        strategy.reset_search_state()

        assert strategy.next_goal_row is None
        assert strategy.next_goal_col is None
        assert strategy.current_path is None
        assert strategy.path_index == 0
        assert strategy._path_target is None


class TestCreateDungeonWithPriest:
    """Test the create_dungeon_with_priest factory function."""

    def test_returns_dungeon_priest_and_hero(self):
        """Should return a tuple of (dungeon, priest, hero)."""
        dungeon, priest, hero = create_dungeon_with_priest(5)

        assert dungeon is not None
        assert priest is not None
        assert hero is not None

    def test_dungeon_starts_with_goal_behind_gate(self):
        """Dungeon should have a goal from the start, blocked by a gate."""
        dungeon, priest, hero = create_dungeon_with_priest(5)

        # Goal should be present
        goal_npc = dungeon.find_goal_npc()
        assert goal_npc is not None, "Dungeon should have goal from the start"

        # Gate should be blocking the goal
        gate_npc = None
        for npc in dungeon.npcs:
            if npc.npc_id == "north_gate":
                gate_npc = npc
                break
        assert gate_npc is not None, "Gate should be blocking the goal"

    def test_priest_has_conversation_complete_callback(self):
        """Priest should have on_conversation_complete callback set."""
        dungeon, priest, hero = create_dungeon_with_priest(5)

        assert priest.on_conversation_complete is not None

    def test_callback_removes_gate(self):
        """Calling the callback should remove the gate blocking the goal."""
        dungeon, priest, hero = create_dungeon_with_priest(5)

        # Gate should exist initially
        gate_exists = any(npc.npc_id == "north_gate" for npc in dungeon.npcs)
        assert gate_exists, "Gate should exist before callback"

        # Trigger the callback
        priest.on_conversation_complete()

        # Gate should be removed
        gate_exists = any(npc.npc_id == "north_gate" for npc in dungeon.npcs)
        assert not gate_exists, "Gate should be removed after callback"

        # Goal should still be present
        goal_npc = dungeon.find_goal_npc()
        assert goal_npc is not None

    def test_callback_resets_hero_strategy(self):
        """Calling the callback should reset the hero's strategy state."""
        dungeon, priest, hero = create_dungeon_with_priest(5)

        # Simulate some strategy state
        hero.strategy.lru_doors[(5, 10)] = None
        hero.strategy.next_goal_row = 10

        # Trigger the callback
        priest.on_conversation_complete()

        # Strategy should be reset
        assert len(hero.strategy.lru_doors) == 0
        assert hero.strategy.next_goal_row is None

    def test_goal_placed_in_gated_room(self):
        """The goal should be placed in a separate goal room with a gate."""
        dungeon, priest, hero = create_dungeon_with_priest(5)

        # Find the goal position
        goal_pos = dungeon.find_goal_position()
        assert goal_pos is not None

        # Check which room it's in (should be in the goal room, not the start room)
        goal_room = dungeon.get_room_id(goal_pos[0], goal_pos[1])
        assert goal_room != 0, "Goal should not be in the start room (room 0)"
