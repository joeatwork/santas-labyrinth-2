"""Unit tests for Hero and GoalSeekingStrategy."""

import pytest
import numpy as np
from typing import List, Tuple, Optional, Dict

from dungeon.dungeon_gen import Tile, ROOM_WIDTH, ROOM_HEIGHT
from dungeon.world import Hero, Dungeon, TILE_SIZE
from dungeon.strategy import Strategy, GoalSeekingStrategy, MoveCommand


class MockStrategy(Strategy):
    """A mock strategy for testing Hero in isolation."""

    def __init__(self, commands: Optional[List[Optional[MoveCommand]]] = None):
        """
        Args:
            commands: List of MoveCommands to return on successive calls.
                      None in the list means return None for that call.
                      If exhausted, returns None.
        """
        self.commands = commands or []
        self.call_count = 0

    def decide_next_move(self, x: float, y: float, dungeon) -> Optional[MoveCommand]:
        if self.call_count < len(self.commands):
            command = self.commands[self.call_count]
            self.call_count += 1
            return command
        return None


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


class TestHero:
    """Test Hero behavior in isolation using MockStrategy."""

    def test_hero_stays_idle_when_strategy_returns_none(self):
        """Hero remains idle when strategy returns None."""
        strategy = MockStrategy(commands=[None])
        hero = Hero(100.0, 100.0, strategy=strategy)
        dungeon = MockDungeon()

        hero.update(0.0, dungeon)

        assert hero.state == 'idle'
        assert hero.target_x == 100.0
        assert hero.target_y == 100.0

    def test_hero_applies_move_command(self):
        """Hero applies target and direction from MoveCommand."""
        command = MoveCommand(target_x=200.0, target_y=150.0, direction=0)
        strategy = MockStrategy(commands=[command])
        hero = Hero(100.0, 100.0, strategy=strategy)
        dungeon = MockDungeon()

        hero.update(0.0, dungeon)

        assert hero.state == 'walking'
        assert hero.target_x == 200.0
        assert hero.target_y == 150.0
        assert hero.direction == 0  # East

    def test_hero_applies_direction_from_command(self):
        """Hero direction is set by the MoveCommand."""
        command = MoveCommand(target_x=100.0, target_y=200.0, direction=1)
        strategy = MockStrategy(commands=[command])
        hero = Hero(100.0, 100.0, strategy=strategy)
        hero.direction = 0  # Start facing East
        dungeon = MockDungeon()

        hero.update(0.0, dungeon)

        assert hero.direction == 1  # Now facing South

    def test_hero_moves_toward_target(self):
        """Hero._move() moves hero toward target."""
        hero = Hero(100.0, 100.0, strategy=MockStrategy())
        hero.target_x = 200.0
        hero.target_y = 100.0
        hero.state = 'walking'

        hero._move(0.1)  # Move for 0.1 seconds at 150 pixels/sec = 15 pixels

        assert hero.x > 100.0
        assert hero.state == 'walking'  # Not there yet

    def test_hero_reaches_target_and_becomes_idle(self):
        """Hero transitions to idle when reaching target."""
        hero = Hero(100.0, 100.0, strategy=MockStrategy())
        hero.target_x = 105.0  # Very close
        hero.target_y = 100.0
        hero.state = 'walking'

        hero._move(0.1)  # 15 pixels is enough to reach target 5 pixels away

        assert hero.x == 105.0
        assert hero.y == 100.0
        assert hero.state == 'idle'


class TestStrategyTargetStability:
    """Test that strategy targets remain stable while being pursued."""

    def test_target_persists_across_calls(self):
        """Strategy keeps the same goal target until reached."""
        dungeon = MockDungeon(2, 2)

        goal_row = ROOM_HEIGHT + 5
        goal_col = ROOM_WIDTH + 5
        dungeon.set_goal(goal_row, goal_col)

        dungeon.add_door(0, 0, 0)  # East
        dungeon.add_door(0, 0, 1)  # South

        x, y = room_center(0, 0)
        strategy = GoalSeekingStrategy(random_choice=lambda lst: lst[0])

        # First call should select a target
        strategy.decide_next_move(x, y, dungeon)
        first_goal_row = strategy.next_goal_row
        first_goal_col = strategy.next_goal_col
        assert first_goal_row is not None
        assert first_goal_col is not None

        # Second call from same position should keep the same target
        strategy.decide_next_move(x, y, dungeon)
        assert strategy.next_goal_row == first_goal_row
        assert strategy.next_goal_col == first_goal_col


class TestStrategyPathfinding:
    """Test GoalSeekingStrategy pathfinding."""

    def test_strategy_path_avoids_obstacle(self):
        """Verify the computed path does not include obstacle tiles."""
        dungeon = MockDungeon(1, 1)

        hero_row, hero_col = 5, 3
        goal_row, goal_col = 5, 8
        pillar_row, pillar_col = 5, 5

        dungeon.add_pillar(pillar_row, pillar_col)
        dungeon.set_goal(goal_row, goal_col)

        x, y = tile_center(hero_row, hero_col)
        strategy = GoalSeekingStrategy(random_choice=lambda lst: lst[0])

        # Trigger path computation
        strategy.decide_next_move(x, y, dungeon)

        # Check that the computed path does not include the pillar
        assert strategy.current_path is not None, "Strategy should have computed a path"
        assert (pillar_row, pillar_col) not in strategy.current_path, \
            "Path should not include the pillar tile"


class TestStrategyDeadEndTracking:
    """Test that GoalSeekingStrategy marks and avoids dead end doors."""

    def test_strategy_marks_door_as_dead_end_when_room_has_no_other_doors(self):
        """Strategy marks a door as dead end after entering a room with only one door."""
        dungeon = MockDungeon(2, 1)

        # Room 0 (left) has east door, Room 1 (right) has only west door (dead end)
        dungeon.add_door(0, 0, 0)  # East door in room 0
        dungeon.add_door(0, 1, 2)  # West door in room 1

        strategy = GoalSeekingStrategy(random_choice=lambda lst: lst[0])

        # Strategy should not have any dead ends marked yet
        assert len(strategy.dead_end_doors) == 0

        # Start in room 0
        x, y = room_center(0, 0)
        strategy.decide_next_move(x, y, dungeon)

        # Move to room 1 (past the door)
        x = ROOM_WIDTH * TILE_SIZE + TILE_SIZE * 5  # Center of room 1
        y = TILE_SIZE * 5
        strategy.last_door_direction = 0  # Came through east door
        strategy.last_room_id = 0  # Was in room 0

        # Now call decide_next_move - it should detect room change and mark dead end
        strategy.decide_next_move(x, y, dungeon)

        # The east door of room 0 should now be marked as a dead end
        assert strategy.is_dead_end(0, 0), "East door of room 0 should be marked as dead end"

    def test_strategy_prefers_non_dead_end_doors(self):
        """Strategy chooses non-dead-end doors over dead-end doors."""
        dungeon = MockDungeon(2, 2)

        # Room 0 has east and south doors
        dungeon.add_door(0, 0, 0)  # East door
        dungeon.add_door(0, 0, 1)  # South door

        x, y = room_center(0, 0)
        # Use random_choice that returns last item (to verify filtering works)
        strategy = GoalSeekingStrategy(random_choice=lambda lst: lst[-1])

        # Mark east door as dead end
        strategy.mark_dead_end(0, 0)

        # Strategy should choose south door (only non-dead-end option)
        strategy.decide_next_move(x, y, dungeon)

        # Target should be beyond south door (row + 2)
        expected_target_row = 9 + 2  # South door is at row 9, target is 2 tiles beyond
        assert strategy.next_goal_row == expected_target_row, \
            f"Strategy should target south door, got row {strategy.next_goal_row}"

    def test_strategy_uses_dead_end_door_when_no_other_options(self):
        """Strategy uses dead-end door when it's the only non-entry option."""
        dungeon = MockDungeon(2, 2)

        # Room 0 has east and south doors
        dungeon.add_door(0, 0, 0)  # East door
        dungeon.add_door(0, 0, 1)  # South door

        x, y = room_center(0, 0)
        strategy = GoalSeekingStrategy(random_choice=lambda lst: lst[0])

        # Mark both doors as dead ends
        strategy.mark_dead_end(0, 0)  # East
        strategy.mark_dead_end(0, 1)  # South

        # Strategy should still choose one of them
        strategy.decide_next_move(x, y, dungeon)

        # Should have selected a target (one of the dead end doors)
        assert strategy.next_goal_row is not None
        assert strategy.next_goal_col is not None

    def test_strategy_marks_door_as_dead_end_when_all_other_doors_are_dead_ends(self):
        """Strategy marks entry door as dead end if all other doors in room are dead ends."""
        dungeon = MockDungeon(3, 1)

        # Room layout: [0] -- [1] -- [2]
        # Room 0: east door
        # Room 1: west door (to room 0), east door (to room 2)
        # Room 2: west door only (dead end)
        dungeon.add_door(0, 0, 0)  # Room 0 east
        dungeon.add_door(0, 1, 2)  # Room 1 west
        dungeon.add_door(0, 1, 0)  # Room 1 east
        dungeon.add_door(0, 2, 2)  # Room 2 west

        # Start in room 1, having come from room 0
        x, y = room_center(0, 1)
        strategy = GoalSeekingStrategy(random_choice=lambda lst: lst[0])
        strategy.last_room_id = 0  # Came from room 0
        strategy.last_door_direction = 0  # Through east door of room 0

        # Mark the east door of room 1 as already a dead end
        # (simulating that we already explored room 2)
        strategy.mark_dead_end(1, 0)

        # Now when entering room 1, it should see:
        # - Entry door (west) - don't count this
        # - East door - marked as dead end
        # Since all non-entry doors are dead ends, entry door should be marked

        # Trigger the dead end check
        strategy._check_and_mark_dead_end(x, y, dungeon, 0, 0)

        # Room 0's east door should now be marked as dead end
        assert strategy.is_dead_end(0, 0), \
            "East door of room 0 should be marked as dead end (leads to room with only dead ends)"
