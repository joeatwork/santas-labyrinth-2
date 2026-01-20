"""Unit tests for Hero.decide_next_move navigation logic."""

import pytest
import numpy as np
from typing import List, Tuple, Optional, Dict

from dungeon_gen import Tile, ROOM_WIDTH, ROOM_HEIGHT
from world import Hero, Dungeon, TILE_SIZE


class MockDungeon:
    """A mock dungeon for testing with controllable layout."""

    def __init__(self, rooms_wide: int = 2, rooms_tall: int = 2):
        self.rooms_wide = rooms_wide
        self.rooms_tall = rooms_tall
        self.cols = rooms_wide * ROOM_WIDTH
        self.rows = rooms_tall * ROOM_HEIGHT
        self.map = np.zeros((self.rows, self.cols), dtype=int)
        self._goal_position: Optional[Tuple[float, float]] = None

        # Track which tiles belong to which room (for corridor support)
        # Maps (tile_row, tile_col) -> room_id (int)
        # If not in map, assumed to be corridor/nothing
        self._tile_to_room: Dict[Tuple[int, int], int] = {}

        # Fill all rooms with floor by default
        for r in range(self.rows):
            for c in range(self.cols):
                self.map[r, c] = Tile.FLOOR
                # Map each tile to its room (room_id = room_row * rooms_wide + room_col)
                room_row = r // ROOM_HEIGHT
                room_col = c // ROOM_WIDTH
                room_id = room_row * rooms_wide + room_col
                self._tile_to_room[(r, c)] = room_id

    def set_goal(self, tile_row: int, tile_col: int) -> None:
        """Place goal at specific tile coordinates."""
        self.map[tile_row, tile_col] = Tile.GOAL
        self._goal_position = (
            tile_col * TILE_SIZE + TILE_SIZE / 2,
            tile_row * TILE_SIZE + TILE_SIZE / 2
        )

    def mark_corridor_tile(self, tile_row: int, tile_col: int, adjacent_room_id: int) -> None:
        """Mark a tile as part of a corridor (not belonging to any room)."""
        # Corridor tiles are mapped to an adjacent room for pathfinding purposes
        self._tile_to_room[(tile_row, tile_col)] = adjacent_room_id

    def add_pillar(self, tile_row: int, tile_col: int) -> None:
        """Place a single pillar obstacle at the given tile."""
        self.map[tile_row, tile_col] = Tile.PILLAR

    def add_big_pillar(self, tile_row: int, tile_col: int) -> None:
        """Place a 2x2 convex corner block (big pillar) with top-left at given tile."""
        self.map[tile_row, tile_col] = Tile.NW_CONVEX_CORNER
        self.map[tile_row, tile_col + 1] = Tile.NE_CONVEX_CORNER
        self.map[tile_row + 1, tile_col] = Tile.SW_CONVEX_CORNER
        self.map[tile_row + 1, tile_col + 1] = Tile.SE_CONVEX_CORNER

    def add_door(self, room_row: int, room_col: int, direction: int) -> None:
        """
        Add a door to a room by placing door tiles.
        Direction: 0=East, 1=South, 2=West, 3=North
        """
        base_row = room_row * ROOM_HEIGHT
        base_col = room_col * ROOM_WIDTH

        if direction == 3:  # North - place at row 0, cols 5-6
            self.map[base_row, base_col + 5] = Tile.NORTH_DOOR_WEST
            self.map[base_row, base_col + 6] = Tile.NORTH_DOOR_EAST
        elif direction == 1:  # South - place at row 9, cols 5-6
            self.map[base_row + 9, base_col + 5] = Tile.SOUTH_DOOR_WEST
            self.map[base_row + 9, base_col + 6] = Tile.SOUTH_DOOR_EAST
        elif direction == 2:  # West - place at col 0, rows 4-5
            self.map[base_row + 4, base_col] = Tile.WEST_DOOR_NORTH
            self.map[base_row + 5, base_col] = Tile.WEST_DOOR_SOUTH
        elif direction == 0:  # East - place at col 11, rows 4-5
            self.map[base_row + 4, base_col + 11] = Tile.EAST_DOOR_NORTH
            self.map[base_row + 5, base_col + 11] = Tile.EAST_DOOR_SOUTH
        else:
            raise ValueError(f"Invalid direction: {direction}")

    # Tiles that can be walked on (matches Dungeon.WALKABLE_TILES)
    WALKABLE_TILES = (
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
    )

    def is_walkable(self, x: float, y: float) -> bool:
        """Check if a pixel position is walkable."""
        col = int(x / TILE_SIZE)
        row = int(y / TILE_SIZE)
        return self.is_tile_walkable(row, col)

    def is_tile_walkable(self, row: int, col: int) -> bool:
        """Check if a tile at (row, col) is walkable."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            tile = self.map[row, col]
            return tile in self.WALKABLE_TILES
        return False

    def get_room_id(self, x: float, y: float) -> int:
        tile_col = int(x / TILE_SIZE)
        tile_row = int(y / TILE_SIZE)
        # Check if this tile is explicitly mapped to a room
        if (tile_row, tile_col) in self._tile_to_room:
            return self._tile_to_room[(tile_row, tile_col)]
        # Default fallback for unmapped tiles (corridors)
        room_row = tile_row // ROOM_HEIGHT
        room_col = tile_col // ROOM_WIDTH
        return room_row * self.rooms_wide + room_col

    def find_goal_position(self) -> Optional[Tuple[float, float]]:
        return self._goal_position

    def find_doors_in_room(self, room_id: int) -> List[Tuple[int, float, float]]:
        """Scan room tiles for door tiles and return their positions."""
        doors: List[Tuple[int, float, float]] = []
        found_doors: set[int] = set()

        door_tile_to_direction = {
            Tile.NORTH_DOOR_WEST: 3,
            Tile.SOUTH_DOOR_WEST: 1,
            Tile.EAST_DOOR_NORTH: 0,
            Tile.WEST_DOOR_NORTH: 2,
        }

        # Find all tiles that belong to this room
        room_tiles = [(r, c) for (r, c), rid in self._tile_to_room.items() if rid == room_id]

        for tile_row, tile_col in room_tiles:
            if 0 <= tile_row < self.rows and 0 <= tile_col < self.cols:
                tile = self.map[tile_row, tile_col]
                if tile in door_tile_to_direction:
                    direction = door_tile_to_direction[tile]
                    if direction not in found_doors:
                        found_doors.add(direction)
                        door_x = (tile_col + 0.5) * TILE_SIZE
                        door_y = (tile_row + 0.5) * TILE_SIZE
                        doors.append((direction, door_x, door_y))

        return doors


def tile_center(tile_row: int, tile_col: int) -> Tuple[float, float]:
    """Get pixel coordinates of tile center."""
    return (tile_col * TILE_SIZE + TILE_SIZE / 2, tile_row * TILE_SIZE + TILE_SIZE / 2)


def room_center(room_row: int, room_col: int) -> Tuple[float, float]:
    """Get pixel coordinates of room center."""
    tile_row = room_row * ROOM_HEIGHT + ROOM_HEIGHT // 2
    tile_col = room_col * ROOM_WIDTH + ROOM_WIDTH // 2
    return tile_center(tile_row, tile_col)


class TestHeroOnGoal:
    """Test that hero stops moving when on the goal."""

    def test_hero_does_not_move_when_on_goal(self):
        dungeon = MockDungeon(1, 1)
        goal_row, goal_col = 5, 6
        dungeon.set_goal(goal_row, goal_col)

        x, y = tile_center(goal_row, goal_col)
        hero = Hero(x, y)

        hero.decide_next_move(dungeon)

        assert hero.state == 'idle'
        assert hero.target_x == x
        assert hero.target_y == y


class TestHeroApproachesGoal:
    """Test that hero approaches goal when in the same room."""

    def test_hero_moves_toward_goal_in_same_room(self):
        dungeon = MockDungeon(1, 1)
        goal_row, goal_col = 5, 8
        dungeon.set_goal(goal_row, goal_col)

        # Hero starts west of goal
        hero_row, hero_col = 5, 3
        x, y = tile_center(hero_row, hero_col)
        hero = Hero(x, y)

        hero.decide_next_move(dungeon)

        # Hero should start walking east toward goal
        assert hero.state == 'walking'
        assert hero.direction == 0  # East

    def test_hero_moves_south_toward_goal(self):
        dungeon = MockDungeon(1, 1)
        goal_row, goal_col = 7, 5
        dungeon.set_goal(goal_row, goal_col)

        # Hero starts north of goal
        hero_row, hero_col = 3, 5
        x, y = tile_center(hero_row, hero_col)
        hero = Hero(x, y)

        hero.decide_next_move(dungeon)

        assert hero.state == 'walking'
        assert hero.direction == 1  # South

    def test_hero_moves_north_toward_goal(self):
        dungeon = MockDungeon(1, 1)
        goal_row, goal_col = 2, 5
        dungeon.set_goal(goal_row, goal_col)

        # Hero starts south of goal
        hero_row, hero_col = 7, 5
        x, y = tile_center(hero_row, hero_col)
        hero = Hero(x, y)

        hero.decide_next_move(dungeon)

        assert hero.state == 'walking'
        assert hero.direction == 3  # North

    def test_hero_moves_west_toward_goal(self):
        dungeon = MockDungeon(1, 1)
        goal_row, goal_col = 5, 2
        dungeon.set_goal(goal_row, goal_col)

        # Hero starts east of goal
        hero_row, hero_col = 5, 8
        x, y = tile_center(hero_row, hero_col)
        hero = Hero(x, y)

        hero.decide_next_move(dungeon)

        assert hero.state == 'walking'
        assert hero.direction == 2  # West


class TestHeroNavigatesToDoor:
    """Test that hero navigates toward doors when goal is in another room."""

    def test_hero_aligns_with_east_door(self):
        dungeon = MockDungeon(2, 1)

        goal_col = ROOM_WIDTH + 5
        dungeon.set_goal(5, goal_col)
        dungeon.add_door(0, 0, 0)  # East door at y = (4.5) * TILE_SIZE

        # Hero not aligned with door (different y)
        hero_row, hero_col = 2, 5  # Row 2, but door is at rows 4-5
        x, y = tile_center(hero_row, hero_col)
        hero = Hero(x, y, random_choice=lambda lst: lst[0])

        hero.decide_next_move(dungeon)

        # Hero should move to align with door (move south)
        assert hero.state == 'walking'
        assert hero.direction == 1  # South to align with door

    def test_hero_aligns_with_south_door(self):
        dungeon = MockDungeon(1, 2)

        goal_row = ROOM_HEIGHT + 5
        dungeon.set_goal(goal_row, 5)
        dungeon.add_door(0, 0, 1)  # South door at x = (5.5) * TILE_SIZE

        # Hero not aligned with door (different x)
        hero_row, hero_col = 5, 2  # Col 2, but door is at cols 5-6
        x, y = tile_center(hero_row, hero_col)
        hero = Hero(x, y, random_choice=lambda lst: lst[0])

        hero.decide_next_move(dungeon)

        # Hero should move to align with door (move east)
        assert hero.state == 'walking'
        assert hero.direction == 0  # East to align with door


class TestHeroApproachesFacingDoor:
    """Test that hero approaches a door they're already facing and aligned with."""

    def test_hero_approaches_east_door_when_facing_and_aligned(self):
        dungeon = MockDungeon(2, 1)

        goal_col = ROOM_WIDTH + 5
        dungeon.set_goal(5, goal_col)
        dungeon.add_door(0, 0, 0)  # East door

        # Hero aligned with east door and facing east
        # East door y is at (4.5) * TILE_SIZE
        door_y = 4.5 * TILE_SIZE
        x, y = tile_center(4, 5)  # Row 4 puts us near the door's y
        hero = Hero(x, y)
        hero.direction = 0  # Facing East

        hero.decide_next_move(dungeon)

        # Should approach the door directly
        assert hero.state == 'walking'
        assert hero.direction == 0  # Still facing East

    def test_hero_approaches_south_door_when_facing_and_aligned(self):
        dungeon = MockDungeon(1, 2)

        goal_row = ROOM_HEIGHT + 5
        dungeon.set_goal(goal_row, 5)
        dungeon.add_door(0, 0, 1)  # South door

        # Hero aligned with south door and facing south
        x, y = tile_center(5, 5)  # Col 5 aligns with door at cols 5-6
        hero = Hero(x, y)
        hero.direction = 1  # Facing South

        hero.decide_next_move(dungeon)

        assert hero.state == 'walking'
        assert hero.direction == 1  # Still facing South


class TestHeroNavigationTargetStability:
    """Test that navigation targets remain stable while being pursued."""

    def test_target_persists_across_moves(self):
        """Hero keeps the same goal target while moving toward it."""
        dungeon = MockDungeon(2, 2)

        goal_row = ROOM_HEIGHT + 5
        goal_col = ROOM_WIDTH + 5
        dungeon.set_goal(goal_row, goal_col)

        dungeon.add_door(0, 0, 0)  # East
        dungeon.add_door(0, 0, 1)  # South

        x, y = room_center(0, 0)
        hero = Hero(x, y, random_choice=lambda lst: lst[0])

        # First call should select a target
        hero.decide_next_move(dungeon)
        first_goal_row = hero.next_goal_row
        first_goal_col = hero.next_goal_col
        assert first_goal_row is not None
        assert first_goal_col is not None

        # Simulate completing a single step but not reaching the target
        hero.state = 'idle'

        # Second call should keep the same target
        hero.decide_next_move(dungeon)
        assert hero.next_goal_row == first_goal_row
        assert hero.next_goal_col == first_goal_col


class TestHeroLeavesRoom:
    """Integration-style tests that hero can navigate through rooms."""

    def test_hero_eventually_reaches_door_tile(self):
        dungeon = MockDungeon(2, 1)

        goal_col = ROOM_WIDTH + 5
        dungeon.set_goal(5, goal_col)
        dungeon.add_door(0, 0, 0)  # East door

        # Start hero west of room center
        start_x, start_y = tile_center(5, 3)
        hero = Hero(start_x, start_y, random_choice=lambda lst: lst[0])

        # Simulate several update cycles
        for _ in range(100):
            if hero.state == 'idle':
                hero.decide_next_move(dungeon)
            hero.move(0.1)

            # Check if we've reached the east edge of room 0
            if hero.x >= (ROOM_WIDTH - 1) * TILE_SIZE:
                break

        # Hero should have moved significantly eastward
        assert hero.x > start_x

    def test_hero_walks_through_door_without_stopping(self):
        """Test that hero continues through a door tile without getting stuck."""
        dungeon = MockDungeon(2, 1)

        goal_col = ROOM_WIDTH + 5
        dungeon.set_goal(5, goal_col)
        dungeon.add_door(0, 0, 0)  # East door at col 11, rows 4-5

        # Start hero on the east door tile, facing east
        # Door is at col 11, row 4
        start_x, start_y = tile_center(4, 11)
        hero = Hero(start_x, start_y, random_choice=lambda lst: lst[0])
        hero.direction = 0  # Facing East

        # Hero should continue through the door
        hero.decide_next_move(dungeon)

        assert hero.state == 'walking'
        assert hero.direction == 0  # Still facing East
        # Target should be one tile east (into the next room)
        assert hero.target_x > start_x


class TestHeroNavigatesAroundObstacles:
    """Test that hero uses BFS pathfinding to navigate around obstacles."""

    def test_hero_navigates_around_pillar(self):
        """Hero finds path around single pillar to reach goal."""
        dungeon = MockDungeon(1, 1)

        # Place pillar directly between hero start and goal
        # Hero at col 3, goal at col 8, pillar at col 5
        hero_row, hero_col = 5, 3
        goal_row, goal_col = 5, 8
        pillar_col = 5

        dungeon.add_pillar(hero_row, pillar_col)
        dungeon.set_goal(goal_row, goal_col)

        x, y = tile_center(hero_row, hero_col)
        hero = Hero(x, y, random_choice=lambda lst: lst[0])

        # Simulate movement until hero reaches goal or max iterations
        max_iterations = 100
        for _ in range(max_iterations):
            if hero.state == 'idle':
                hero.decide_next_move(dungeon)
            hero.move(0.1)

            # Check if reached goal
            if int(hero.x / TILE_SIZE) == goal_col and int(hero.y / TILE_SIZE) == goal_row:
                break

        # Verify hero reached the goal
        final_col = int(hero.x / TILE_SIZE)
        final_row = int(hero.y / TILE_SIZE)
        assert final_col == goal_col and final_row == goal_row, \
            f"Hero should reach goal at ({goal_row}, {goal_col}), but is at ({final_row}, {final_col})"

    def test_hero_navigates_around_big_pillar(self):
        """Hero finds path around 2x2 convex corner block."""
        dungeon = MockDungeon(1, 1)

        # Place big pillar (2x2) between hero and goal
        hero_row, hero_col = 5, 2
        goal_row, goal_col = 5, 9

        # Big pillar at rows 4-5, cols 5-6 (blocking direct east path)
        dungeon.add_big_pillar(4, 5)
        dungeon.set_goal(goal_row, goal_col)

        x, y = tile_center(hero_row, hero_col)
        hero = Hero(x, y, random_choice=lambda lst: lst[0])

        # Simulate movement
        max_iterations = 150
        for _ in range(max_iterations):
            if hero.state == 'idle':
                hero.decide_next_move(dungeon)
            hero.move(0.1)

            # Check if reached goal
            if int(hero.x / TILE_SIZE) == goal_col and int(hero.y / TILE_SIZE) == goal_row:
                break

        # Verify hero reached the goal
        final_col = int(hero.x / TILE_SIZE)
        final_row = int(hero.y / TILE_SIZE)
        assert final_col == goal_col and final_row == goal_row, \
            f"Hero should reach goal at ({goal_row}, {goal_col}), but is at ({final_row}, {final_col})"

    def test_hero_path_avoids_obstacle(self):
        """Verify the computed path does not include obstacle tiles."""
        dungeon = MockDungeon(1, 1)

        hero_row, hero_col = 5, 3
        goal_row, goal_col = 5, 8
        pillar_row, pillar_col = 5, 5

        dungeon.add_pillar(pillar_row, pillar_col)
        dungeon.set_goal(goal_row, goal_col)

        x, y = tile_center(hero_row, hero_col)
        hero = Hero(x, y, random_choice=lambda lst: lst[0])

        # Trigger path computation
        hero.decide_next_move(dungeon)

        # Check that the computed path does not include the pillar
        assert hero.current_path is not None, "Hero should have computed a path"
        assert (pillar_row, pillar_col) not in hero.current_path, \
            "Path should not include the pillar tile"
