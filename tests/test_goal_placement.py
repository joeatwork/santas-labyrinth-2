"""Tests for dynamic goal placement and strategy reset."""

import pytest
import numpy as np

from dungeon.dungeon_gen import create_random_dungeon
from dungeon.world import TILE_SIZE
from dungeon.strategy import GoalSeekingStrategy
from dungeon.setup import create_dungeon_with_priest


class TestDungeonWithoutGoal:
    """Test that dungeons can be generated without a goal."""

    def test_dungeon_without_goal_has_no_goal_npc(self):
        """A dungeon generated with place_goal=False should have no goal NPC."""
        dungeon = create_random_dungeon(5, place_goal=False)

        goal_npc = dungeon.find_goal_npc()
        assert goal_npc is None, "Dungeon should have no goal NPC"

    def test_dungeon_with_goal_has_goal_npc(self):
        """A dungeon generated with place_goal=True should have a goal NPC."""
        dungeon = create_random_dungeon(5, place_goal=True)

        goal_npc = dungeon.find_goal_npc()
        assert goal_npc is not None, "Dungeon should have a goal NPC"
        assert goal_npc.is_goal is True

    def test_default_is_to_place_goal(self):
        """By default, dungeons should have a goal."""
        dungeon = create_random_dungeon(5)

        goal_npc = dungeon.find_goal_npc()
        assert goal_npc is not None, "Default should place a goal"


class TestPlaceGoal:
    """Test Dungeon.place_goal() method."""

    def test_place_goal_adds_goal_npc(self):
        """place_goal should add a goal NPC to the dungeon."""
        dungeon = create_random_dungeon(5, place_goal=False)

        # Verify no goal initially
        assert dungeon.find_goal_npc() is None

        # Place goal in room 2
        col, row = dungeon.place_goal(room_id=2)

        # Verify goal was placed
        goal_npc = dungeon.find_goal_npc()
        assert goal_npc is not None
        assert goal_npc.is_goal is True
        # Verify goal NPC is at the returned position
        assert goal_npc.tile_col == col
        assert goal_npc.tile_row == row

    def test_place_goal_replaces_existing_goal(self):
        """place_goal should remove any existing goal first."""
        dungeon = create_random_dungeon(5, place_goal=True)

        # Find original goal position
        original_goal_npc = dungeon.find_goal_npc()
        assert original_goal_npc is not None

        # Place goal in a different room
        dungeon.place_goal(room_id=1)

        # Should still have exactly one goal NPC
        goal_npcs = [npc for npc in dungeon.npcs if npc.is_goal]
        assert len(goal_npcs) == 1, "Should have exactly one goal NPC"

    def test_place_goal_in_invalid_room_raises(self):
        """place_goal with invalid room_id should raise RuntimeError."""
        dungeon = create_random_dungeon(3, place_goal=False)

        with pytest.raises(RuntimeError, match="does not exist"):
            dungeon.place_goal(room_id=999)


class TestRemoveGoal:
    """Test Dungeon.remove_goal() method."""

    def test_remove_goal_removes_goal_npc(self):
        """remove_goal should remove the goal NPC from the dungeon."""
        dungeon = create_random_dungeon(5, place_goal=True)

        # Verify goal exists
        assert dungeon.find_goal_npc() is not None

        # Remove goal
        dungeon.remove_goal()

        # Verify goal is gone
        assert dungeon.find_goal_npc() is None

    def test_remove_goal_on_dungeon_without_goal(self):
        """remove_goal should be safe to call when no goal exists."""
        dungeon = create_random_dungeon(5, place_goal=False)

        # Should not raise
        dungeon.remove_goal()

        # Still no goal
        assert dungeon.find_goal_npc() is None


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

    def test_dungeon_starts_without_goal(self):
        """Dungeon should not have a goal initially."""
        dungeon, priest, hero = create_dungeon_with_priest(5)

        goal_npc = dungeon.find_goal_npc()
        assert goal_npc is None, "Dungeon should start without goal"

    def test_priest_has_conversation_complete_callback(self):
        """Priest should have on_conversation_complete callback set."""
        dungeon, priest, hero = create_dungeon_with_priest(5)

        assert priest.on_conversation_complete is not None

    def test_callback_places_goal(self):
        """Calling the callback should place the goal."""
        dungeon, priest, hero = create_dungeon_with_priest(5)

        # No goal initially
        assert dungeon.find_goal_npc() is None

        # Trigger the callback
        priest.on_conversation_complete()

        # Now there should be a goal
        goal_npc = dungeon.find_goal_npc()
        assert goal_npc is not None
        assert goal_npc.is_goal is True

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

    def test_goal_not_placed_in_start_room(self):
        """The goal should not be placed in room 0 (the start room)."""
        # Run multiple times to check randomness
        for _ in range(10):
            dungeon, priest, hero = create_dungeon_with_priest(5)
            priest.on_conversation_complete()

            # Find the goal position
            goal_pos = dungeon.find_goal_position()
            assert goal_pos is not None

            # Check which room it's in
            goal_room = dungeon.get_room_id(goal_pos[0], goal_pos[1])
            assert goal_room != 0, "Goal should not be in the start room (room 0)"
