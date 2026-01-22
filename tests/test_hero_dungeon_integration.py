"""Integration tests for hero navigating through generated dungeons."""

import pytest
import random
import numpy as np
from dungeon.world import Hero, Dungeon, TILE_SIZE


def run_hero_to_goal(dungeon: Dungeon, max_steps: int = 10000, dt: float = 0.1) -> tuple[bool, int, str]:
    """
    Run the hero through a dungeon until it reaches the goal, gets stuck, or throws.

    Returns:
        (reached_goal, steps_taken, failure_reason)

    Raises:
        Any exception thrown by the hero's update method (test should catch these)
    """
    start_x, start_y = dungeon.start_pos
    hero = Hero(start_x, start_y)

    last_position = (hero.x, hero.y)
    stuck_counter = 0
    max_stuck_steps = 100  # Consider stuck if no movement for this many steps

    for step in range(max_steps):
        # Check if hero reached the goal
        if dungeon.is_on_goal(hero.x, hero.y):
            return (True, step, "")

        # Run one update cycle - let exceptions propagate
        hero.update(dt, dungeon)

        # Check if hero is stuck (not moving)
        current_position = (hero.x, hero.y)
        if current_position == last_position:
            stuck_counter += 1
            if stuck_counter >= max_stuck_steps:
                hero_col = int(hero.x / TILE_SIZE)
                hero_row = int(hero.y / TILE_SIZE)
                return (False, step, f"Hero stuck at tile ({hero_row}, {hero_col}), state={hero.state}")
        else:
            stuck_counter = 0
            last_position = current_position

    hero_col = int(hero.x / TILE_SIZE)
    hero_row = int(hero.y / TILE_SIZE)
    return (False, max_steps, f"Hero did not reach goal within {max_steps} steps, at tile ({hero_row}, {hero_col})")


class TestHeroDungeonIntegration:
    """Test that hero can navigate through procedurally generated dungeons."""

    @pytest.mark.parametrize("seed", range(20))
    def test_hero_reaches_goal_in_small_dungeon(self, seed: int):
        """Hero should reach the goal in a small dungeon (5 rooms)."""
        random.seed(seed)
        np.random.seed(seed)
        dungeon = Dungeon(num_rooms=5)

        reached_goal, steps, failure_reason = run_hero_to_goal(dungeon)

        assert reached_goal, f"Seed {seed}: {failure_reason}"

    @pytest.mark.parametrize("seed", range(20))
    def test_hero_reaches_goal_in_medium_dungeon(self, seed: int):
        """Hero should reach the goal in a medium dungeon (10 rooms)."""
        random.seed(seed)
        np.random.seed(seed)
        dungeon = Dungeon(num_rooms=10)

        reached_goal, steps, failure_reason = run_hero_to_goal(dungeon)

        assert reached_goal, f"Seed {seed}: {failure_reason}"

    @pytest.mark.parametrize("seed", range(10))
    def test_hero_reaches_goal_in_large_dungeon(self, seed: int):
        """Hero should reach the goal in a large dungeon (20 rooms)."""
        random.seed(seed)
        np.random.seed(seed)
        dungeon = Dungeon(num_rooms=20)

        reached_goal, steps, failure_reason = run_hero_to_goal(dungeon, max_steps=20000)

        assert reached_goal, f"Seed {seed}: {failure_reason}"
