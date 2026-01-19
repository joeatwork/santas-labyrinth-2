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
        # Maps (tile_row, tile_col) -> (room_row, room_col)
        # If not in map, assumed to be corridor/nothing
        self._tile_to_room: Dict[Tuple[int, int], Tuple[int, int]] = {}

        # Fill all rooms with floor by default
        for r in range(self.rows):
            for c in range(self.cols):
                self.map[r, c] = Tile.FLOOR
                # Map each tile to its room
                room_row = r // ROOM_HEIGHT
                room_col = c // ROOM_WIDTH
                self._tile_to_room[(r, c)] = (room_row, room_col)

    def set_goal(self, tile_row: int, tile_col: int) -> None:
        """Place goal at specific tile coordinates."""
        self.map[tile_row, tile_col] = Tile.GOAL
        self._goal_position = (
            tile_col * TILE_SIZE + TILE_SIZE / 2,
            tile_row * TILE_SIZE + TILE_SIZE / 2
        )

    def mark_corridor_tile(self, tile_row: int, tile_col: int, adjacent_room: Tuple[int, int]) -> None:
        """Mark a tile as part of a corridor (not belonging to any room)."""
        # Corridor tiles are mapped to an adjacent room for pathfinding purposes
        self._tile_to_room[(tile_row, tile_col)] = adjacent_room

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

    def get_room_coords(self, x: float, y: float) -> Tuple[int, int]:
        tile_col = int(x / TILE_SIZE)
        tile_row = int(y / TILE_SIZE)
        # Check if this tile is explicitly mapped to a room
        if (tile_row, tile_col) in self._tile_to_room:
            return self._tile_to_room[(tile_row, tile_col)]
        # Default fallback for unmapped tiles (corridors)
        return (tile_row // ROOM_HEIGHT, tile_col // ROOM_WIDTH)

    def find_goal_position(self) -> Optional[Tuple[float, float]]:
        return self._goal_position

    def find_doors_in_room(self, room_row: int, room_col: int) -> List[Tuple[int, float, float]]:
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
        room_tiles = [(r, c) for (r, c), room in self._tile_to_room.items() if room == (room_row, room_col)]

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
        assert hero.next_goal_col == 12
        assert hero.next_goal_row == 4

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


class TestHeroCorridorNavigation:
    """Test that hero navigates through corridors without turning around."""

    def test_hero_exits_north_south_corridor_to_south(self):
        """
        Test that a hero entering a north-south corridor from the north
        will always exit to the south without turning around.
        """
        # Create a dungeon with two rooms and a corridor between them
        # Room 0: rows 0-9
        # Corridor: rows 10-17 (8 tiles)
        # Room 1: rows 18-27

        # Calculate dimensions
        corridor_length = 8
        total_rows = 2 * ROOM_HEIGHT + corridor_length
        dungeon = MockDungeon(1, 1)

        # Manually resize the map to accommodate two rooms + corridor
        dungeon.rows = total_rows
        dungeon.map = np.zeros((total_rows, ROOM_WIDTH), dtype=int)

        # Fill rooms with floor and mark tiles
        for row in range(ROOM_HEIGHT):
            for col in range(ROOM_WIDTH):
                dungeon.map[row, col] = Tile.FLOOR  # Room 0
                dungeon._tile_to_room[(row, col)] = (0, 0)
        for row in range(ROOM_HEIGHT + corridor_length, total_rows):
            for col in range(ROOM_WIDTH):
                dungeon.map[row, col] = Tile.FLOOR  # Room 1
                dungeon._tile_to_room[(row, col)] = (1, 0)

        # Set goal in the southern room
        goal_row = ROOM_HEIGHT + corridor_length + 5
        goal_col = 5
        dungeon.set_goal(goal_row, goal_col)

        # Add south door to room 0 (at row 9, cols 5-6)
        dungeon.map[ROOM_HEIGHT - 1, 5] = Tile.SOUTH_DOOR_WEST
        dungeon.map[ROOM_HEIGHT - 1, 6] = Tile.SOUTH_DOOR_EAST

        # Create corridor tiles (rows 10-17)
        corridor_start_row = ROOM_HEIGHT
        corridor_end_row = ROOM_HEIGHT + corridor_length - 1
        corridor_col = 5  # Align with door positions

        # Fill corridor with floor and walls
        # Mark corridor tiles as a special "corridor room" (0, 1) - not a real room
        # This prevents the hero from thinking it's in either end room
        for row in range(corridor_start_row, corridor_end_row + 1):
            dungeon.map[row, corridor_col - 1] = Tile.WEST_WALL
            dungeon.map[row, corridor_col] = Tile.FLOOR
            dungeon.map[row, corridor_col + 1] = Tile.FLOOR
            dungeon.map[row, corridor_col + 2] = Tile.EAST_WALL
            # Mark corridor tiles as a different "room" to isolate navigation
            for col in [corridor_col - 1, corridor_col, corridor_col + 1, corridor_col + 2]:
                dungeon._tile_to_room[(row, col)] = (0, 1)  # Corridor "room"

        # Add door tiles at the corridor entrance (north door of corridor)
        dungeon.map[corridor_start_row, corridor_col] = Tile.NORTH_DOOR_WEST
        dungeon.map[corridor_start_row, corridor_col + 1] = Tile.NORTH_DOOR_EAST

        # Add door tiles at the corridor exit (south door of corridor)
        dungeon.map[corridor_end_row, corridor_col] = Tile.SOUTH_DOOR_WEST
        dungeon.map[corridor_end_row, corridor_col + 1] = Tile.SOUTH_DOOR_EAST

        # Add north door to room 1 (at row 18, cols 5-6)
        room1_start_row = ROOM_HEIGHT + corridor_length
        dungeon.map[room1_start_row, 5] = Tile.NORTH_DOOR_WEST
        dungeon.map[room1_start_row, 6] = Tile.NORTH_DOOR_EAST

        # Start hero in the middle of the corridor, having just entered from the north
        corridor_middle_row = (corridor_start_row + corridor_end_row) // 2
        start_x, start_y = tile_center(corridor_middle_row, corridor_col)
        hero = Hero(start_x, start_y, random_choice=lambda lst: lst[0])
        hero.direction = 1  # Facing South (came from north)

        # Simulate that the hero just entered the corridor from room 0
        # This sets up the entry_door_direction to prevent backtracking
        hero.current_room = (0, 1)  # Corridor "room"
        hero.entry_door_direction = 3  # Entered from north, so north door is the entry

        # Track hero's direction through the corridor
        directions_taken = []
        positions = []
        max_iterations = 200

        for i in range(max_iterations):
            if hero.state == 'idle':
                hero.decide_next_move(dungeon)

            if hero.state == 'walking':
                directions_taken.append(hero.direction)
                positions.append((int(hero.y / TILE_SIZE), hero.entry_door_direction, hero.current_room))

            hero.move(0.1)

            # Check if hero has exited the corridor to the south (reached room 1)
            hero_row = int(hero.y / TILE_SIZE)
            if hero_row >= room1_start_row + 2:  # Deep into room 1
                break

        # Debug output if test fails
        if 3 in directions_taken:
            print(f"\nHero turned north at iteration {directions_taken.index(3)}")
            print(f"Positions when north was chosen: {positions[directions_taken.index(3)]}")
            print(f"Direction history around that point: {directions_taken[max(0, directions_taken.index(3)-5):directions_taken.index(3)+5]}")
            print(f"Hero start position: row={corridor_middle_row}, col={corridor_col}")
            print(f"Doors found in room (0, 0): {dungeon.find_doors_in_room(0, 0)}")
            print(f"Goal position: {dungeon.find_goal_position()}")

        # Verify hero never turned north (direction 3)
        assert 3 not in directions_taken, "Hero should never turn north in a north-south corridor"

        # Verify hero reached the southern room
        final_hero_row = int(hero.y / TILE_SIZE)
        assert final_hero_row >= room1_start_row, f"Hero should have reached the southern room (row {final_hero_row} >= {room1_start_row})"


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
