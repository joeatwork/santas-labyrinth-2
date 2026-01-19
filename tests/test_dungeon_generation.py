"""Unit tests for verifying generated dungeons are fully connected."""

import pytest
import numpy as np
import random
from typing import Set, Tuple, List, Deque, Optional
from collections import deque

from dungeon_gen import generate_dungeon, Tile


def get_walkable_tiles(dungeon_map: np.ndarray) -> Set[Tuple[int, int]]:
    """Extract all walkable tile coordinates from the dungeon map."""
    walkable_tiles = set()
    rows, cols = dungeon_map.shape

    # All tiles that can be walked on
    walkable_tile_types = {
        Tile.FLOOR,
        Tile.GOAL,
        Tile.NORTH_DOOR_WEST,
        Tile.NORTH_DOOR_EAST,
        Tile.SOUTH_DOOR_WEST,
        Tile.SOUTH_DOOR_EAST,
        Tile.WEST_DOOR_NORTH,
        Tile.WEST_DOOR_SOUTH,
        Tile.EAST_DOOR_NORTH,
        Tile.EAST_DOOR_SOUTH,
    }

    for row in range(rows):
        for col in range(cols):
            if dungeon_map[row, col] in walkable_tile_types:
                walkable_tiles.add((row, col))

    return walkable_tiles


def flood_fill_from(start: Tuple[int, int], walkable_tiles: Set[Tuple[int, int]]) -> Set[Tuple[int, int]]:
    """
    Perform flood fill starting from a tile, returning all reachable tiles.
    Uses BFS to find all tiles connected to the start position.
    """
    visited: Set[Tuple[int, int]] = set()
    queue: Deque[Tuple[int, int]] = deque([start])
    visited.add(start)

    while queue:
        row, col = queue.popleft()

        # Check all four adjacent tiles (no diagonal movement)
        neighbors = [
            (row - 1, col),  # North
            (row + 1, col),  # South
            (row, col - 1),  # West
            (row, col + 1),  # East
        ]

        for neighbor in neighbors:
            if neighbor in walkable_tiles and neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return visited


def is_dungeon_connected(dungeon_map: np.ndarray) -> Tuple[bool, str]:
    """
    Check if all walkable tiles in the dungeon are connected.

    Returns:
        Tuple of (is_connected, message) where message explains any issues
    """
    walkable_tiles = get_walkable_tiles(dungeon_map)

    if not walkable_tiles:
        return False, "No walkable tiles found in dungeon"

    # Start flood fill from an arbitrary walkable tile
    start_tile = next(iter(walkable_tiles))
    reachable_tiles = flood_fill_from(start_tile, walkable_tiles)

    # Check if all walkable tiles are reachable
    unreachable = walkable_tiles - reachable_tiles

    if unreachable:
        return False, f"Found {len(unreachable)} unreachable tiles out of {len(walkable_tiles)} total walkable tiles"

    return True, f"All {len(walkable_tiles)} walkable tiles are connected"


class TestDungeonConnectivity:
    """Test that generated dungeons have all areas connected."""

    def test_single_room_dungeon_is_connected(self):
        """A 1x1 dungeon should be trivially connected."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(1, 1)

        is_connected, message = is_dungeon_connected(dungeon_map)
        assert is_connected, f"1x1 dungeon not connected: {message}"

    def test_2x2_dungeon_is_connected(self):
        """A 2x2 dungeon should have all rooms and corridors connected."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(2, 2)

        is_connected, message = is_dungeon_connected(dungeon_map)
        assert is_connected, f"2x2 dungeon not connected: {message}"

    def test_3x3_dungeon_is_connected(self):
        """A 3x3 dungeon should be fully connected."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(3, 3)

        is_connected, message = is_dungeon_connected(dungeon_map)
        assert is_connected, f"3x3 dungeon not connected: {message}"

    def test_5x5_dungeon_is_connected(self):
        """A larger 5x5 dungeon should be fully connected."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(5, 5)

        is_connected, message = is_dungeon_connected(dungeon_map)
        assert is_connected, f"5x5 dungeon not connected: {message}"

    def test_wide_dungeon_is_connected(self):
        """A 6x2 wide dungeon should be fully connected."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(6, 2)

        is_connected, message = is_dungeon_connected(dungeon_map)
        assert is_connected, f"6x2 dungeon not connected: {message}"

    def test_tall_dungeon_is_connected(self):
        """A 2x6 tall dungeon should be fully connected."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(2, 6)

        is_connected, message = is_dungeon_connected(dungeon_map)
        assert is_connected, f"2x6 dungeon not connected: {message}"

    def test_multiple_random_seeds_produce_connected_dungeons(self):
        """Test that different random seeds all produce connected dungeons."""
        seeds = [1, 42, 123, 456, 789, 999, 1234, 5678]

        for seed in seeds:
            random.seed(seed)
            dungeon_map, _, _, _ = generate_dungeon(4, 4)
            is_connected, message = is_dungeon_connected(dungeon_map)
            assert is_connected, f"4x4 dungeon with seed {seed} not connected: {message}"

    def test_goal_is_reachable_from_start(self):
        """Test that the goal tile is reachable from the start position."""
        random.seed(42)
        dungeon_map, start_pos, _, _ = generate_dungeon(4, 4)

        # Find goal tile
        goal_tiles = np.argwhere(dungeon_map == Tile.GOAL)
        assert len(goal_tiles) > 0, "No goal tile found"

        # Convert start position from pixels to tile coordinates
        start_tile_col = int(start_pos[0] / 64)
        start_tile_row = int(start_pos[1] / 64)
        start_tile = (start_tile_row, start_tile_col)

        # Get all walkable tiles
        walkable_tiles = get_walkable_tiles(dungeon_map)
        assert start_tile in walkable_tiles, f"Start position {start_tile} is not walkable"

        # Flood fill from start
        reachable_from_start = flood_fill_from(start_tile, walkable_tiles)

        # Check that goal is reachable
        goal_tile = tuple(goal_tiles[0])
        assert goal_tile in reachable_from_start, \
            f"Goal at {goal_tile} is not reachable from start at {start_tile}"


class TestConnectivityStressTest:
    """Stress test connectivity with many different dungeon configurations."""

    @pytest.mark.parametrize("width,height", [
        (1, 1), (2, 1), (1, 2),
        (2, 2), (3, 2), (2, 3),
        (3, 3), (4, 3), (3, 4),
        (4, 4), (5, 4), (4, 5),
        (5, 5), (6, 5), (5, 6),
    ])
    def test_various_dungeon_sizes_are_connected(self, width, height):
        """Test that dungeons of various sizes are all connected."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(width, height)

        is_connected, message = is_dungeon_connected(dungeon_map)
        assert is_connected, f"{width}x{height} dungeon not connected: {message}"

    @pytest.mark.parametrize("seed", range(0, 50))
    def test_fifty_random_dungeons_are_connected(self, seed):
        """Test 50 different random 4x4 dungeons for connectivity."""
        random.seed(seed)
        dungeon_map, _, _, _ = generate_dungeon(4, 4)

        is_connected, message = is_dungeon_connected(dungeon_map)
        assert is_connected, f"4x4 dungeon with seed {seed} not connected: {message}"


def get_door_tiles(dungeon_map: np.ndarray) -> Set[Tuple[int, int]]:
    """Extract all door tile coordinates from the dungeon map."""
    door_tiles = set()
    rows, cols = dungeon_map.shape

    door_tile_types = {
        Tile.NORTH_DOOR_WEST,
        Tile.NORTH_DOOR_EAST,
        Tile.SOUTH_DOOR_WEST,
        Tile.SOUTH_DOOR_EAST,
        Tile.WEST_DOOR_NORTH,
        Tile.WEST_DOOR_SOUTH,
        Tile.EAST_DOOR_NORTH,
        Tile.EAST_DOOR_SOUTH,
    }

    for row in range(rows):
        for col in range(cols):
            if dungeon_map[row, col] in door_tile_types:
                door_tiles.add((row, col))

    return door_tiles


def is_door_connected_to_corridor(dungeon_map: np.ndarray, door_row: int, door_col: int) -> bool:
    """
    Check if a door tile is connected to a corridor (has floor tiles or other doors adjacent to it).

    A door is considered connected if it has floor tiles or other door tiles on at least one side.
    Door-to-door adjacency is valid because corridors now have doors on both ends.
    """
    rows, cols = dungeon_map.shape

    # All door tile types
    door_tiles = {
        Tile.NORTH_DOOR_WEST, Tile.NORTH_DOOR_EAST,
        Tile.SOUTH_DOOR_WEST, Tile.SOUTH_DOOR_EAST,
        Tile.WEST_DOOR_NORTH, Tile.WEST_DOOR_SOUTH,
        Tile.EAST_DOOR_NORTH, Tile.EAST_DOOR_SOUTH,
    }

    # Check all four adjacent tiles
    adjacent_positions = [
        (door_row - 1, door_col),  # North
        (door_row + 1, door_col),  # South
        (door_row, door_col - 1),  # West
        (door_row, door_col + 1),  # East
    ]

    for adj_row, adj_col in adjacent_positions:
        if 0 <= adj_row < rows and 0 <= adj_col < cols:
            tile = dungeon_map[adj_row, adj_col]
            # Check if adjacent tile is a floor (corridor floor) or another door
            if tile == Tile.FLOOR or tile in door_tiles:
                return True

    return False


class TestNoBlindDoors:
    """Test that generated dungeons have no blind doors (unconnected doors)."""

    def test_single_room_has_no_doors(self):
        """A 1x1 dungeon (single room) should have no doors at all."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(1, 1)

        door_tiles = get_door_tiles(dungeon_map)
        assert len(door_tiles) == 0, \
            f"Single room dungeon should have no doors, but found {len(door_tiles)} door tiles"

    def test_2x2_dungeon_has_no_blind_doors(self):
        """A 2x2 dungeon should have no unconnected doors."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(2, 2)

        door_tiles = get_door_tiles(dungeon_map)

        blind_doors = []
        for door_row, door_col in door_tiles:
            if not is_door_connected_to_corridor(dungeon_map, door_row, door_col):
                blind_doors.append((door_row, door_col))

        assert len(blind_doors) == 0, \
            f"Found {len(blind_doors)} blind doors at positions: {blind_doors}"

    def test_3x3_dungeon_has_no_blind_doors(self):
        """A 3x3 dungeon should have no unconnected doors."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(3, 3)

        door_tiles = get_door_tiles(dungeon_map)

        blind_doors = []
        for door_row, door_col in door_tiles:
            if not is_door_connected_to_corridor(dungeon_map, door_row, door_col):
                blind_doors.append((door_row, door_col))

        assert len(blind_doors) == 0, \
            f"Found {len(blind_doors)} blind doors at positions: {blind_doors}"

    def test_5x5_dungeon_has_no_blind_doors(self):
        """A 5x5 dungeon should have no unconnected doors."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(5, 5)

        door_tiles = get_door_tiles(dungeon_map)

        blind_doors = []
        for door_row, door_col in door_tiles:
            if not is_door_connected_to_corridor(dungeon_map, door_row, door_col):
                blind_doors.append((door_row, door_col))

        assert len(blind_doors) == 0, \
            f"Found {len(blind_doors)} blind doors at positions: {blind_doors}"

    @pytest.mark.parametrize("width,height", [
        (2, 2), (3, 2), (2, 3),
        (3, 3), (4, 3), (3, 4),
        (4, 4), (5, 5),
    ])
    def test_various_dungeon_sizes_have_no_blind_doors(self, width, height):
        """Test that dungeons of various sizes have no blind doors."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(width, height)

        door_tiles = get_door_tiles(dungeon_map)

        blind_doors = []
        for door_row, door_col in door_tiles:
            if not is_door_connected_to_corridor(dungeon_map, door_row, door_col):
                blind_doors.append((door_row, door_col))

        assert len(blind_doors) == 0, \
            f"{width}x{height} dungeon: Found {len(blind_doors)} blind doors at positions: {blind_doors}"


class TestCorridorDoors:
    """Test that corridors have doors on both ends."""

    def count_tiles_in_corridor(self, corridor_tiles: List[Tuple[int, int, int]], tile_type: int) -> int:
        """Count how many tiles of a specific type exist in corridor tiles list."""
        return sum(1 for (row, col, tile) in corridor_tiles if tile == tile_type)

    def test_north_corridor_has_doors_on_both_ends(self):
        """Test that a north corridor has matching doors at both ends."""
        from dungeon_gen import _calculate_room_placement, RoomTemplate

        # Create a simple room template (doesn't matter what it is)
        template = RoomTemplate(name="test", ascii_art=["1-nN-2", "[....]", "[....]", "3_sS_4"])

        # Generate a north corridor from position (10, 5)
        direction = 'north'
        door_row = 10  # Source room's north door row
        door_col = 5   # Source room's north door col (left tile of the 2-tile door)

        new_room_x, new_room_y, corridor_tiles = _calculate_room_placement(
            direction, door_row, door_col, template
        )

        # Count door tiles in the corridor
        north_door_west = self.count_tiles_in_corridor(corridor_tiles, Tile.NORTH_DOOR_WEST)
        north_door_east = self.count_tiles_in_corridor(corridor_tiles, Tile.NORTH_DOOR_EAST)
        south_door_west = self.count_tiles_in_corridor(corridor_tiles, Tile.SOUTH_DOOR_WEST)
        south_door_east = self.count_tiles_in_corridor(corridor_tiles, Tile.SOUTH_DOOR_EAST)

        # A north corridor should have:
        # - 1 pair of NORTH doors at the entrance (near source room)
        # - 1 pair of SOUTH doors at the exit (near target room)
        assert north_door_west == 1, f"Expected 1 NORTH_DOOR_WEST, found {north_door_west}"
        assert north_door_east == 1, f"Expected 1 NORTH_DOOR_EAST, found {north_door_east}"
        assert south_door_west == 1, f"Expected 1 SOUTH_DOOR_WEST, found {south_door_west}"
        assert south_door_east == 1, f"Expected 1 SOUTH_DOOR_EAST, found {south_door_east}"

    def test_south_corridor_has_doors_on_both_ends(self):
        """Test that a south corridor has matching doors at both ends."""
        from dungeon_gen import _calculate_room_placement, RoomTemplate

        template = RoomTemplate(name="test", ascii_art=["1-nN-2", "[....]", "[....]", "3_sS_4"])

        direction = 'south'
        door_row = 10
        door_col = 5

        new_room_x, new_room_y, corridor_tiles = _calculate_room_placement(
            direction, door_row, door_col, template
        )

        north_door_west = self.count_tiles_in_corridor(corridor_tiles, Tile.NORTH_DOOR_WEST)
        north_door_east = self.count_tiles_in_corridor(corridor_tiles, Tile.NORTH_DOOR_EAST)
        south_door_west = self.count_tiles_in_corridor(corridor_tiles, Tile.SOUTH_DOOR_WEST)
        south_door_east = self.count_tiles_in_corridor(corridor_tiles, Tile.SOUTH_DOOR_EAST)

        assert north_door_west == 1, f"Expected 1 NORTH_DOOR_WEST, found {north_door_west}"
        assert north_door_east == 1, f"Expected 1 NORTH_DOOR_EAST, found {north_door_east}"
        assert south_door_west == 1, f"Expected 1 SOUTH_DOOR_WEST, found {south_door_west}"
        assert south_door_east == 1, f"Expected 1 SOUTH_DOOR_EAST, found {south_door_east}"

    def test_east_corridor_has_doors_on_both_ends(self):
        """Test that an east corridor has matching doors at both ends."""
        from dungeon_gen import _calculate_room_placement, RoomTemplate

        template = RoomTemplate(name="test", ascii_art=["1-nN-2", "w...e", "W...E", "3_sS_4"])

        direction = 'east'
        door_row = 10
        door_col = 5

        new_room_x, new_room_y, corridor_tiles = _calculate_room_placement(
            direction, door_row, door_col, template
        )

        east_door_north = self.count_tiles_in_corridor(corridor_tiles, Tile.EAST_DOOR_NORTH)
        east_door_south = self.count_tiles_in_corridor(corridor_tiles, Tile.EAST_DOOR_SOUTH)
        west_door_north = self.count_tiles_in_corridor(corridor_tiles, Tile.WEST_DOOR_NORTH)
        west_door_south = self.count_tiles_in_corridor(corridor_tiles, Tile.WEST_DOOR_SOUTH)

        assert east_door_north == 1, f"Expected 1 EAST_DOOR_NORTH, found {east_door_north}"
        assert east_door_south == 1, f"Expected 1 EAST_DOOR_SOUTH, found {east_door_south}"
        assert west_door_north == 1, f"Expected 1 WEST_DOOR_NORTH, found {west_door_north}"
        assert west_door_south == 1, f"Expected 1 WEST_DOOR_SOUTH, found {west_door_south}"

    def test_west_corridor_has_doors_on_both_ends(self):
        """Test that a west corridor has matching doors at both ends."""
        from dungeon_gen import _calculate_room_placement, RoomTemplate

        template = RoomTemplate(name="test", ascii_art=["1-nN-2", "w...e", "W...E", "3_sS_4"])

        direction = 'west'
        door_row = 10
        door_col = 5

        new_room_x, new_room_y, corridor_tiles = _calculate_room_placement(
            direction, door_row, door_col, template
        )

        east_door_north = self.count_tiles_in_corridor(corridor_tiles, Tile.EAST_DOOR_NORTH)
        east_door_south = self.count_tiles_in_corridor(corridor_tiles, Tile.EAST_DOOR_SOUTH)
        west_door_north = self.count_tiles_in_corridor(corridor_tiles, Tile.WEST_DOOR_NORTH)
        west_door_south = self.count_tiles_in_corridor(corridor_tiles, Tile.WEST_DOOR_SOUTH)

        assert east_door_north == 1, f"Expected 1 EAST_DOOR_NORTH, found {east_door_north}"
        assert east_door_south == 1, f"Expected 1 EAST_DOOR_SOUTH, found {east_door_south}"
        assert west_door_north == 1, f"Expected 1 WEST_DOOR_NORTH, found {west_door_north}"
        assert west_door_south == 1, f"Expected 1 WEST_DOOR_SOUTH, found {west_door_south}"
