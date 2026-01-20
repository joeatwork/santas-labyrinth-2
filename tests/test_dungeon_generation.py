"""Unit tests for verifying generated dungeons are fully connected."""

import pytest
import numpy as np
import random
from typing import Set, Tuple, List, Deque, Optional
from collections import deque

from dungeon_gen import (
    generate_dungeon,
    Tile,
    find_floor_tile_in_room,
    Position,
    RoomTemplate,
)


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
        """A 1-room dungeon should be trivially connected."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(1)

        is_connected, message = is_dungeon_connected(dungeon_map)
        assert is_connected, f"1-room dungeon not connected: {message}"

    def test_4_room_dungeon_is_connected(self):
        """A 4-room dungeon should have all rooms and corridors connected."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(4)

        is_connected, message = is_dungeon_connected(dungeon_map)
        assert is_connected, f"4-room dungeon not connected: {message}"

    def test_9_room_dungeon_is_connected(self):
        """A 9-room dungeon should be fully connected."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(9)

        is_connected, message = is_dungeon_connected(dungeon_map)
        assert is_connected, f"9-room dungeon not connected: {message}"

    def test_25_room_dungeon_is_connected(self):
        """A larger 25-room dungeon should be fully connected."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(25)

        is_connected, message = is_dungeon_connected(dungeon_map)
        assert is_connected, f"25-room dungeon not connected: {message}"

    def test_12_room_dungeon_is_connected(self):
        """A 12-room dungeon should be fully connected."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(12)

        is_connected, message = is_dungeon_connected(dungeon_map)
        assert is_connected, f"12-room dungeon not connected: {message}"

    def test_multiple_random_seeds_produce_connected_dungeons(self):
        """Test that different random seeds all produce connected dungeons."""
        seeds = [1, 42, 123, 456, 789, 999, 1234, 5678]

        for seed in seeds:
            random.seed(seed)
            dungeon_map, _, _, _ = generate_dungeon(16)
            is_connected, message = is_dungeon_connected(dungeon_map)
            assert is_connected, f"16-room dungeon with seed {seed} not connected: {message}"

    def test_goal_is_reachable_from_start(self):
        """Test that the goal tile is reachable from the start position."""
        random.seed(42)
        dungeon_map, start_pos, _, _ = generate_dungeon(16)

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

    @pytest.mark.parametrize("num_rooms", [
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 16, 20, 25, 30,
    ])
    def test_various_dungeon_sizes_are_connected(self, num_rooms):
        """Test that dungeons of various sizes are all connected."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(num_rooms)

        is_connected, message = is_dungeon_connected(dungeon_map)
        assert is_connected, f"{num_rooms}-room dungeon not connected: {message}"

    @pytest.mark.parametrize("seed", range(0, 50))
    def test_fifty_random_dungeons_are_connected(self, seed):
        """Test 50 different random 16-room dungeons for connectivity."""
        random.seed(seed)
        dungeon_map, _, _, _ = generate_dungeon(16)

        is_connected, message = is_dungeon_connected(dungeon_map)
        assert is_connected, f"16-room dungeon with seed {seed} not connected: {message}"


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
        """A 1-room dungeon (single room) should have no doors at all."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(1)

        door_tiles = get_door_tiles(dungeon_map)
        assert len(door_tiles) == 0, \
            f"Single room dungeon should have no doors, but found {len(door_tiles)} door tiles"

    def test_4_room_dungeon_has_no_blind_doors(self):
        """A 4-room dungeon should have no unconnected doors."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(4)

        door_tiles = get_door_tiles(dungeon_map)

        blind_doors = []
        for door_row, door_col in door_tiles:
            if not is_door_connected_to_corridor(dungeon_map, door_row, door_col):
                blind_doors.append((door_row, door_col))

        assert len(blind_doors) == 0, \
            f"Found {len(blind_doors)} blind doors at positions: {blind_doors}"

    def test_9_room_dungeon_has_no_blind_doors(self):
        """A 9-room dungeon should have no unconnected doors."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(9)

        door_tiles = get_door_tiles(dungeon_map)

        blind_doors = []
        for door_row, door_col in door_tiles:
            if not is_door_connected_to_corridor(dungeon_map, door_row, door_col):
                blind_doors.append((door_row, door_col))

        assert len(blind_doors) == 0, \
            f"Found {len(blind_doors)} blind doors at positions: {blind_doors}"

    def test_25_room_dungeon_has_no_blind_doors(self):
        """A 25-room dungeon should have no unconnected doors."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(25)

        door_tiles = get_door_tiles(dungeon_map)

        blind_doors = []
        for door_row, door_col in door_tiles:
            if not is_door_connected_to_corridor(dungeon_map, door_row, door_col):
                blind_doors.append((door_row, door_col))

        assert len(blind_doors) == 0, \
            f"Found {len(blind_doors)} blind doors at positions: {blind_doors}"

    @pytest.mark.parametrize("num_rooms", [
        4, 6, 9, 12, 16, 25,
    ])
    def test_various_dungeon_sizes_have_no_blind_doors(self, num_rooms):
        """Test that dungeons of various sizes have no blind doors."""
        random.seed(42)
        dungeon_map, _, _, _ = generate_dungeon(num_rooms)

        door_tiles = get_door_tiles(dungeon_map)

        blind_doors = []
        for door_row, door_col in door_tiles:
            if not is_door_connected_to_corridor(dungeon_map, door_row, door_col):
                blind_doors.append((door_row, door_col))

        assert len(blind_doors) == 0, \
            f"{num_rooms}-room dungeon: Found {len(blind_doors)} blind doors at positions: {blind_doors}"


class TestFindFloorTileInRoom:
    """Test that find_floor_tile_in_room correctly finds floor tiles in rooms with obstructed centers."""

    def test_finds_floor_when_center_is_obstructed(self):
        """A room with a pillar at center should still find a nearby floor tile."""
        from dungeon_gen import ASCII_TO_TILE

        template = RoomTemplate(
            name="test-obstructed",
            ascii_art=[
                "1--2",
                "[P.]",
                "[..]",
                "3__4",
            ],
        )
        dungeon_map = np.zeros((10, 10), dtype=int)
        room_pos = Position(row=2, column=2)

        for local_row, line in enumerate(template.ascii_art):
            for local_col, char in enumerate(line):
                dungeon_map[room_pos.row + local_row, room_pos.column + local_col] = ASCII_TO_TILE[char]

        result = find_floor_tile_in_room(dungeon_map, room_pos, template)

        assert dungeon_map[result.row, result.column] == Tile.FLOOR, \
            f"Expected FLOOR tile at {result}, got {dungeon_map[result.row, result.column]}"

    def test_finds_floor_in_big_pillar_room(self):
        """The big-pillar room template has a 2x2 pillar at center; should find floor nearby."""
        from dungeon_gen import ASCII_TO_TILE

        template = RoomTemplate(
            name="big-pillar",
            ascii_art=[
                "1-----nN-----2",
                "[............]",
                "w.....^!.....e",
                "W.....~,.....E",
                "[............]",
                "3_____sS_____4",
            ],
        )
        dungeon_map = np.zeros((20, 30), dtype=int)
        room_pos = Position(row=5, column=5)

        for local_row, line in enumerate(template.ascii_art):
            for local_col, char in enumerate(line):
                dungeon_map[room_pos.row + local_row, room_pos.column + local_col] = ASCII_TO_TILE[char]

        result = find_floor_tile_in_room(dungeon_map, room_pos, template)

        assert dungeon_map[result.row, result.column] == Tile.FLOOR, \
            f"Expected FLOOR tile at {result}, got {dungeon_map[result.row, result.column]}"


