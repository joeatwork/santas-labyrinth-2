"""Unit tests for Hero.decide_next_move navigation logic."""

import pytest
import numpy as np
from typing import List, Tuple, Optional

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

        # Fill all rooms with floor by default
        for r in range(self.rows):
            for c in range(self.cols):
                self.map[r, c] = Tile.FLOOR

    def set_goal(self, tile_row: int, tile_col: int) -> None:
        """Place goal at specific tile coordinates."""
        self.map[tile_row, tile_col] = Tile.GOAL
        self._goal_position = (
            tile_col * TILE_SIZE + TILE_SIZE / 2,
            tile_row * TILE_SIZE + TILE_SIZE / 2
        )

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

    def is_walkable(self, x: float, y: float) -> bool:
        col = int(x / TILE_SIZE)
        row = int(y / TILE_SIZE)
        if 0 <= row < self.rows and 0 <= col < self.cols:
            tile = self.map[row, col]
            return tile in (
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
        return False

    def get_room_coords(self, x: float, y: float) -> Tuple[int, int]:
        tile_col = int(x / TILE_SIZE)
        tile_row = int(y / TILE_SIZE)
        return (tile_row // ROOM_HEIGHT, tile_col // ROOM_WIDTH)

    def find_goal_position(self) -> Optional[Tuple[float, float]]:
        return self._goal_position

    def find_doors_in_room(self, room_row: int, room_col: int) -> List[Tuple[int, float, float]]:
        """Scan room tiles for door tiles and return their positions."""
        doors: List[Tuple[int, float, float]] = []
        found_doors: set[int] = set()

        base_row = room_row * ROOM_HEIGHT
        base_col = room_col * ROOM_WIDTH

        door_tile_to_direction = {
            Tile.NORTH_DOOR_WEST: 3,
            Tile.SOUTH_DOOR_WEST: 1,
            Tile.EAST_DOOR_NORTH: 0,
            Tile.WEST_DOOR_NORTH: 2,
        }

        for local_row in range(ROOM_HEIGHT):
            for local_col in range(ROOM_WIDTH):
                tile = self.map[base_row + local_row, base_col + local_col]
                if tile in door_tile_to_direction:
                    direction = door_tile_to_direction[tile]
                    if direction not in found_doors:
                        found_doors.add(direction)
                        door_x = (base_col + local_col + 0.5) * TILE_SIZE
                        door_y = (base_row + local_row + 0.5) * TILE_SIZE
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

    def test_hero_selects_door_when_goal_in_other_room(self):
        dungeon = MockDungeon(2, 1)

        # Goal in room (0, 1)
        goal_row = 5
        goal_col = ROOM_WIDTH + 5
        dungeon.set_goal(goal_row, goal_col)

        # Add east door to room (0, 0)
        dungeon.add_door(0, 0, 0)  # East door

        # Hero in room (0, 0)
        x, y = room_center(0, 0)
        hero = Hero(x, y, random_choice=lambda lst: lst[0])

        hero.decide_next_move(dungeon)

        assert hero.state == 'walking'
        assert hero.selected_door is not None
        assert hero.selected_door[0] == 0  # East door selected

    def test_hero_uses_injected_random_choice(self):
        dungeon = MockDungeon(2, 2)

        # Goal in room (1, 1)
        goal_row = ROOM_HEIGHT + 5
        goal_col = ROOM_WIDTH + 5
        dungeon.set_goal(goal_row, goal_col)

        # Add multiple doors to room (0, 0)
        dungeon.add_door(0, 0, 0)  # East
        dungeon.add_door(0, 0, 1)  # South

        # Hero in room (0, 0)
        x, y = room_center(0, 0)

        # Inject choice that always picks the last door
        hero = Hero(x, y, random_choice=lambda lst: lst[-1])

        hero.decide_next_move(dungeon)

        # Should have picked South (last in list)
        assert hero.selected_door[0] == 1  # South

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


class TestHeroDoorSelection:
    """Test door selection logic including entry door avoidance."""

    def test_hero_avoids_entry_door_when_other_options_exist(self):
        dungeon = MockDungeon(2, 2)

        # Goal in room (1, 1)
        goal_row = ROOM_HEIGHT + 5
        goal_col = ROOM_WIDTH + 5
        dungeon.set_goal(goal_row, goal_col)

        # Room (0, 0) has east and south doors
        dungeon.add_door(0, 0, 0)  # East
        dungeon.add_door(0, 0, 1)  # South

        x, y = room_center(0, 0)
        hero = Hero(x, y, random_choice=lambda lst: lst[0])

        # Simulate entering from the west (so entry_door_direction = 2 = West)
        # But there's no west door, so this shouldn't affect anything
        hero.current_room = (0, 0)
        hero.entry_door_direction = 0  # Entered from East

        hero.decide_next_move(dungeon)

        # Should pick South since East is entry door
        assert hero.selected_door[0] == 1  # South

    def test_hero_uses_entry_door_if_only_option(self):
        dungeon = MockDungeon(2, 1)

        # Goal in room (0, 1)
        goal_col = ROOM_WIDTH + 5
        dungeon.set_goal(5, goal_col)

        # Room (0, 0) has only east door
        dungeon.add_door(0, 0, 0)  # East only

        x, y = room_center(0, 0)
        hero = Hero(x, y, random_choice=lambda lst: lst[0])

        # Simulate that we entered from East (only door)
        hero.current_room = (0, 0)
        hero.entry_door_direction = 0  # East

        hero.decide_next_move(dungeon)

        # Must use East door since it's the only one
        assert hero.selected_door[0] == 0  # East

    def test_hero_resets_door_selection_on_room_change(self):
        dungeon = MockDungeon(2, 1)

        goal_col = ROOM_WIDTH + 5
        dungeon.set_goal(5, goal_col)
        dungeon.add_door(0, 0, 0)  # East door in room (0,0)
        dungeon.add_door(0, 1, 2)  # West door in room (0,1)

        # Start in room (0, 0)
        x, y = room_center(0, 0)
        hero = Hero(x, y, random_choice=lambda lst: lst[0])

        hero.decide_next_move(dungeon)
        first_selected = hero.selected_door

        # Move to room (0, 1)
        hero.x = room_center(0, 1)[0]
        hero.y = room_center(0, 1)[1]
        hero.state = 'idle'
        hero.direction = 0  # Was facing east when entering

        hero.decide_next_move(dungeon)

        # selected_door should have been reset (we're now in goal room anyway)
        # Entry door should be West (opposite of East)
        assert hero.entry_door_direction == 2  # West


class TestHeroDoorSelectionStability:
    """Test that door selection remains stable within a room."""

    def test_selected_door_persists_across_moves(self):
        dungeon = MockDungeon(2, 2)

        goal_row = ROOM_HEIGHT + 5
        goal_col = ROOM_WIDTH + 5
        dungeon.set_goal(goal_row, goal_col)

        dungeon.add_door(0, 0, 0)  # East
        dungeon.add_door(0, 0, 1)  # South

        x, y = room_center(0, 0)
        call_count = [0]

        def counting_choice(lst):
            call_count[0] += 1
            return lst[0]

        hero = Hero(x, y, random_choice=counting_choice)

        # First call should select a door
        hero.decide_next_move(dungeon)
        first_door = hero.selected_door
        assert call_count[0] == 1

        # Simulate completing a move but staying in same room
        hero.state = 'idle'

        # Second call should reuse the same door
        hero.decide_next_move(dungeon)
        assert hero.selected_door == first_door
        assert call_count[0] == 1  # No additional random call


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
