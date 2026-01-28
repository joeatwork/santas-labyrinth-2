"""Tests for dynamic goal placement and strategy reset."""

import pytest
import numpy as np

from dungeon.world import TILE_SIZE
from dungeon.strategy import GoalSeekingStrategy
from dungeon.setup import create_dungeon_with_priest
from dungeon.event_system import EventBus, Event


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

    def test_returns_dungeon_with_hero(self):
        """Should return a dungeon with hero attached."""
        dungeon = create_dungeon_with_priest(5)

        assert dungeon is not None
        assert dungeon.hero is not None

    def test_dungeon_starts_with_goal_behind_gate(self):
        """Dungeon should have a goal from the start, blocked by a gate."""
        dungeon = create_dungeon_with_priest(5)

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

    def test_dungeon_has_event_handler_setup(self):
        """Dungeon should have _event_handler_setup function for event system."""
        dungeon = create_dungeon_with_priest(5)

        assert hasattr(dungeon, '_event_handler_setup')
        assert callable(dungeon._event_handler_setup)

    def test_event_handler_removes_gate_on_priest_conversation_end(self):
        """Event system should remove gate when priest conversation ends."""
        dungeon = create_dungeon_with_priest(5)

        # Set up event bus and handlers
        event_bus = EventBus()
        dungeon.set_event_bus(event_bus)
        dungeon._event_handler_setup(event_bus)  # type: ignore

        # Gate should exist initially
        gate_exists = any(npc.npc_id == "north_gate" for npc in dungeon.npcs)
        assert gate_exists, "Gate should exist before event"

        # Emit conversation end event for priest
        event_bus.emit(Event.CONVERSATION_END, npc_id="robot_priest")

        # Gate should be removed
        gate_exists = any(npc.npc_id == "north_gate" for npc in dungeon.npcs)
        assert not gate_exists, "Gate should be removed after event"

        # Goal should still be present
        goal_npc = dungeon.find_goal_npc()
        assert goal_npc is not None

    def test_event_handler_resets_hero_strategy(self):
        """Event system should reset hero strategy when priest conversation ends."""
        dungeon = create_dungeon_with_priest(5)

        # Set up event bus and handlers
        event_bus = EventBus()
        dungeon.set_event_bus(event_bus)
        dungeon._event_handler_setup(event_bus)  # type: ignore

        hero = dungeon.hero
        assert hero is not None

        # Simulate some strategy state
        hero.strategy.lru_doors[(5, 10)] = None
        hero.strategy.next_goal_row = 10

        # Emit conversation end event for priest
        event_bus.emit(Event.CONVERSATION_END, npc_id="robot_priest")

        # Strategy should be reset
        assert len(hero.strategy.lru_doors) == 0
        assert hero.strategy.next_goal_row is None

    def test_event_handler_ignores_other_npc_conversations(self):
        """Event system should only respond to priest NPC, not others."""
        dungeon = create_dungeon_with_priest(5)

        # Set up event bus and handlers
        event_bus = EventBus()
        dungeon.set_event_bus(event_bus)
        dungeon._event_handler_setup(event_bus)  # type: ignore

        # Gate should exist initially
        gate_exists = any(npc.npc_id == "north_gate" for npc in dungeon.npcs)
        assert gate_exists

        # Emit conversation end for a different NPC
        event_bus.emit(Event.CONVERSATION_END, npc_id="some_other_npc")

        # Gate should still exist
        gate_exists = any(npc.npc_id == "north_gate" for npc in dungeon.npcs)
        assert gate_exists, "Gate should not be removed for other NPCs"

    def test_goal_placed_in_gated_room(self):
        """The goal should be placed in a separate goal room with a gate."""
        dungeon = create_dungeon_with_priest(5)

        # Find the goal position
        goal_pos = dungeon.find_goal_position()
        assert goal_pos is not None

        # Check which room it's in (should be in the goal room, not the start room)
        goal_room = dungeon.get_room_id(goal_pos[0], goal_pos[1])
        assert goal_room != 0, "Goal should not be in the start room (room 0)"
