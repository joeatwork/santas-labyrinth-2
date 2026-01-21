"""
Pathfinding algorithms for dungeon navigation.
"""

from collections import deque
import random
import sys
from typing import Callable, List, Tuple, Optional, Dict

# A path is a list of tile coordinates (row, col), ordered from start to goal
Path = List[Tuple[int, int]]


def find_path_bfs(
    start_row: int,
    start_col: int,
    target_row: int,
    target_col: int,
    is_walkable_tile: Callable[[int, int], bool],
    max_distance: int,
) -> Optional[Path]:
    """
    Find a path from (start_row, start_col) to (target_row, target_col) using BFS.

    Args:
        start_row: Starting tile row
        start_col: Starting tile column
        target_row: Target tile row
        target_col: Target tile column
        is_walkable_tile: Callback that returns True if tile (row, col) is walkable
        max_distance: Maximum number of tiles to search (bounds the search)

    Returns:
        List of (row, col) tuples from start to target (excludes start, includes target),
        or None if no path found within max_distance.
        Returns empty list if already at target.
    """
    if start_row == target_row and start_col == target_col:
        return []  # Already at target

    # BFS queue: (row, col)
    queue: deque[Tuple[int, int]] = deque([(start_row, start_col)])

    # Track visited tiles and their parent for path reconstruction
    # parent[tile] = previous_tile
    parent: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {
        (start_row, start_col): None
    }

    # 4-directional neighbors: (delta_row, delta_col)
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # North, South, West, East

    tiles_searched = 0

    while queue:
        if tiles_searched >= max_distance:
            raise RuntimeError("Exceeded maximum search distance without finding path.")

        current_row, current_col = queue.popleft()
        tiles_searched += 1

        # Shuffle directions to avoid bias
        random.shuffle(directions)

        for dr, dc in directions:
            next_row = current_row + dr
            next_col = current_col + dc
            next_tile = (next_row, next_col)

            # Skip if already visited
            if next_tile in parent:
                continue

            # Skip if not walkable
            if not is_walkable_tile(next_row, next_col):
                continue

            # Mark as visited with parent
            parent[next_tile] = (current_row, current_col)

            # Check if we reached target
            if next_row == target_row and next_col == target_col:
                # Reconstruct path
                path: Path = []
                tile: Optional[Tuple[int, int]] = next_tile
                while tile is not None and tile != (start_row, start_col):
                    path.append(tile)
                    tile = parent[tile]
                path.reverse()
                return path

            queue.append(next_tile)

    print(f"No path found to ({target_row}, {target_col}): queue exhausted.", file=sys.stderr)

    return None  # No path found within max_distance
