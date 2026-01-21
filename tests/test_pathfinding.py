"""Unit tests for BFS pathfinding algorithm."""

import pytest
from typing import Set, Tuple

from dungeon.pathfinding import find_path_bfs


def make_walkability_checker(blocked_tiles: Set[Tuple[int, int]], rows: int, cols: int):
    """Create a walkability checker function for testing."""
    def is_walkable(row: int, col: int) -> bool:
        if not (0 <= row < rows and 0 <= col < cols):
            return False
        return (row, col) not in blocked_tiles
    return is_walkable


class TestFindPathBfs:
    """Tests for the find_path_bfs function."""

    def test_finds_path_in_open_space(self):
        """BFS finds direct path when no obstacles."""
        is_walkable = make_walkability_checker(set(), rows=10, cols=10)

        path = find_path_bfs(
            start_row=5, start_col=2,
            target_row=5, target_col=7,
            is_walkable_tile=is_walkable,
            max_distance=100,
        )

        assert path is not None
        assert len(path) == 5  # 5 tiles to move east
        assert path[0] == (5, 3)  # First step
        assert path[-1] == (5, 7)  # Target

    def test_navigates_around_single_pillar(self):
        """BFS finds path around a single obstacle tile."""
        # Block one tile directly in the path
        blocked = {(5, 4)}
        is_walkable = make_walkability_checker(blocked, rows=10, cols=10)

        path = find_path_bfs(
            start_row=5, start_col=2,
            target_row=5, target_col=6,
            is_walkable_tile=is_walkable,
            max_distance=100,
        )

        assert path is not None
        # Path should go around the pillar
        assert (5, 4) not in path
        assert path[-1] == (5, 6)

    def test_navigates_around_2x2_pillar(self):
        """BFS finds path around big-pillar (2x2 block)."""
        # Block a 2x2 area like convex corners
        blocked = {(4, 5), (4, 6), (5, 5), (5, 6)}
        is_walkable = make_walkability_checker(blocked, rows=10, cols=10)

        path = find_path_bfs(
            start_row=5, start_col=2,
            target_row=5, target_col=9,
            is_walkable_tile=is_walkable,
            max_distance=100,
        )

        assert path is not None
        # Path should not go through blocked tiles
        for tile in blocked:
            assert tile not in path
        assert path[-1] == (5, 9)

    def test_returns_none_when_blocked(self):
        """BFS returns None when target is unreachable."""
        # Completely surround the target
        blocked = {(4, 4), (4, 5), (4, 6), (5, 4), (5, 6), (6, 4), (6, 5), (6, 6)}
        is_walkable = make_walkability_checker(blocked, rows=10, cols=10)

        path = find_path_bfs(
            start_row=2, start_col=2,
            target_row=5, target_col=5,  # Surrounded by walls
            is_walkable_tile=is_walkable,
            max_distance=100,
        )

        assert path is None

    def test_respects_max_distance(self):
        """BFS stops searching after max_distance tiles."""
        is_walkable = make_walkability_checker(set(), rows=100, cols=100)

        # Target is far away, but max_distance is small
        path = find_path_bfs(
            start_row=0, start_col=0,
            target_row=50, target_col=50,
            is_walkable_tile=is_walkable,
            max_distance=10,  # Very small limit
        )

        # Should not find path within the limit
        assert path is None

    def test_empty_path_when_already_at_target(self):
        """BFS returns empty list when start == target."""
        is_walkable = make_walkability_checker(set(), rows=10, cols=10)

        path = find_path_bfs(
            start_row=5, start_col=5,
            target_row=5, target_col=5,
            is_walkable_tile=is_walkable,
            max_distance=100,
        )

        assert path is not None
        assert path == []

    def test_finds_shortest_path(self):
        """BFS finds the shortest path (by tile count)."""
        is_walkable = make_walkability_checker(set(), rows=10, cols=10)

        path = find_path_bfs(
            start_row=0, start_col=0,
            target_row=3, target_col=4,
            is_walkable_tile=is_walkable,
            max_distance=100,
        )

        assert path is not None
        # Manhattan distance is 7 (3 down + 4 right)
        assert len(path) == 7

    def test_handles_l_shaped_obstacle(self):
        """BFS navigates around L-shaped obstacles."""
        # Create an L-shaped wall
        blocked = {(3, 3), (3, 4), (3, 5), (4, 5), (5, 5)}
        is_walkable = make_walkability_checker(blocked, rows=10, cols=10)

        path = find_path_bfs(
            start_row=4, start_col=2,
            target_row=4, target_col=7,
            is_walkable_tile=is_walkable,
            max_distance=100,
        )

        assert path is not None
        for tile in blocked:
            assert tile not in path
        assert path[-1] == (4, 7)

    def test_path_excludes_start_tile(self):
        """Path does not include the starting tile."""
        is_walkable = make_walkability_checker(set(), rows=10, cols=10)

        path = find_path_bfs(
            start_row=5, start_col=5,
            target_row=5, target_col=8,
            is_walkable_tile=is_walkable,
            max_distance=100,
        )

        assert path is not None
        assert (5, 5) not in path  # Start not in path
        assert (5, 8) in path  # Target is in path

    def test_respects_grid_boundaries(self):
        """BFS does not go outside grid boundaries."""
        is_walkable = make_walkability_checker(set(), rows=5, cols=5)

        # Start at edge, target also at edge
        path = find_path_bfs(
            start_row=0, start_col=0,
            target_row=4, target_col=4,
            is_walkable_tile=is_walkable,
            max_distance=100,
        )

        assert path is not None
        # All tiles should be within bounds
        for row, col in path:
            assert 0 <= row < 5
            assert 0 <= col < 5
