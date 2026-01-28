"""Tests for Goal NPC interaction behavior."""

import pytest
from typing import Tuple, Optional

from dungeon.dungeon_gen import Tile
from dungeon.world import Hero, TILE_SIZE
from dungeon.strategy import GoalSeekingStrategy, MoveCommand, InteractCommand
from dungeon.npc import NPC
from dungeon.setup import create_goal_npc

from tests.test_hero_navigation import MockDungeon, tile_center


class TestGoalNPCCreation:
    """Tests for creating Goal NPCs."""

    def test_create_goal_npc_has_correct_sprite(self):
        """Goal NPC should use the 'goal' sprite."""
        goal = create_goal_npc(5, 5)
        assert goal.sprite_name == "goal"

    def test_create_goal_npc_has_goal_id(self):
        """Goal NPC should have npc_id='goal'."""
        goal = create_goal_npc(5, 5)
        assert goal.npc_id == "goal"

    def test_create_goal_npc_is_marked_as_goal(self):
        """Goal NPC should have is_goal=True."""
        goal = create_goal_npc(5, 5)
        assert goal.is_goal is True

    def test_create_goal_npc_has_correct_position(self):
        """Goal NPC should be centered on the specified tile."""
        goal = create_goal_npc(3, 7)
        assert goal.tile_col == 3
        assert goal.tile_row == 7

    def test_create_goal_npc_has_no_conversation(self):
        """Goal NPC should have no conversation engine."""
        goal = create_goal_npc(5, 5)
        assert goal.conversation_engine is None


class TestGoalNPCInteraction:
    """Tests for hero interaction with Goal NPC."""

    def test_strategy_returns_interact_when_adjacent_to_goal(self):
        """Strategy should return InteractCommand when hero is adjacent to Goal NPC."""
        dungeon = MockDungeon(1, 1)

        # Place goal at tile (5, 5)
        dungeon.set_goal(5, 5)

        strategy = GoalSeekingStrategy(random_choice=lambda lst: lst[0])

        # Place hero adjacent to goal (one tile south)
        hero_row, hero_col = 6, 5
        hero_x, hero_y = tile_center(hero_row, hero_col)

        command = strategy.decide_next_move(hero_x, hero_y, dungeon)

        assert isinstance(command, InteractCommand)
        assert command.npc.is_goal is True

    def test_strategy_approaches_goal_when_in_same_room(self):
        """Strategy should approach goal NPC when in the same room."""
        dungeon = MockDungeon(1, 1)

        # Place goal at tile (5, 5)
        dungeon.set_goal(5, 5)

        strategy = GoalSeekingStrategy(random_choice=lambda lst: lst[0])

        # Place hero far from goal
        hero_row, hero_col = 2, 2
        hero_x, hero_y = tile_center(hero_row, hero_col)

        command = strategy.decide_next_move(hero_x, hero_y, dungeon)

        # Should get MoveCommand toward goal
        assert isinstance(command, MoveCommand)
        # Target should be set to approach tile adjacent to goal
        assert strategy.next_goal_row is not None
        assert strategy.next_goal_col is not None

    def test_goal_interaction_priority_over_regular_npcs(self):
        """Goal NPC should be interacted with when adjacent, even if regular NPCs are nearby."""
        dungeon = MockDungeon(1, 1)

        # Place goal at tile (5, 5)
        dungeon.set_goal(5, 5)

        # Place a regular NPC at tile (5, 3)
        regular_npc = NPC(
            x=3 * TILE_SIZE + TILE_SIZE / 2,
            y=5 * TILE_SIZE + TILE_SIZE / 2,
            sprite_name="npc_default",
            npc_id="regular_npc",
        )
        regular_npc.room_id = 0
        dungeon.npcs.append(regular_npc)

        strategy = GoalSeekingStrategy(random_choice=lambda lst: lst[0])

        # Place hero adjacent to both goal and regular NPC (between them)
        hero_row, hero_col = 5, 4
        hero_x, hero_y = tile_center(hero_row, hero_col)

        command = strategy.decide_next_move(hero_x, hero_y, dungeon)

        # Should interact with goal (higher priority)
        assert isinstance(command, InteractCommand)
        assert command.npc.is_goal is True


class TestGoalNPCBlocksMovement:
    """Tests that Goal NPC blocks hero movement like other NPCs."""

    def test_goal_npc_tile_not_walkable(self):
        """The tile occupied by Goal NPC should not be walkable."""
        dungeon = MockDungeon(1, 1)

        # Place goal at tile (5, 5)
        dungeon.set_goal(5, 5)

        # The goal tile should not be walkable (NPC occupies it)
        assert not dungeon.is_tile_walkable(5, 5)

    def test_adjacent_tiles_are_walkable(self):
        """Tiles adjacent to Goal NPC should be walkable (for hero approach)."""
        dungeon = MockDungeon(1, 1)

        # Place goal at tile (5, 5)
        dungeon.set_goal(5, 5)

        # Adjacent tiles should be walkable
        assert dungeon.is_tile_walkable(4, 5)  # North
        assert dungeon.is_tile_walkable(6, 5)  # South
        assert dungeon.is_tile_walkable(5, 4)  # West
        assert dungeon.is_tile_walkable(5, 6)  # East


class TestGoalOnInteractCallback:
    """Tests for Goal NPC on_interact callback."""

    def test_goal_can_have_on_interact_callback(self):
        """Goal NPC should support on_interact callback."""
        goal = create_goal_npc(5, 5)

        callback_called = [False]

        def on_interact():
            callback_called[0] = True

        goal.on_interact = on_interact

        # Simulate interaction
        if goal.on_interact:
            goal.on_interact()

        assert callback_called[0] is True
