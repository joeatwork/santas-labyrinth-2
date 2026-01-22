"""
Navigation strategies for dungeon mobs.

Strategies handle pathfinding, decision-making, and remembering navigation state.
They are decoupled from the mob's movement and animation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple, List, Optional, Callable, Set, Union, TYPE_CHECKING
import numpy as np

from .dungeon_gen import Tile
from .pathfinding import find_path_bfs

if TYPE_CHECKING:
    from .npc import NPC

# Re-export TILE_SIZE for convenience
TILE_SIZE: int = 64


@dataclass
class MoveCommand:
    """A command from a strategy telling a mob where to move next."""
    target_x: float
    target_y: float
    direction: int  # 0=East, 1=South, 2=West, 3=North


@dataclass
class InteractCommand:
    """A command from a strategy to interact with an NPC."""
    npc: 'NPC'


# Union type for all strategy commands
StrategyCommand = Optional[Union[MoveCommand, InteractCommand]]


class Strategy(ABC):
    """
    Abstract base class for mob navigation strategies.

    A strategy decides where a mob should move next based on the dungeon layout
    and the mob's current position. Strategies maintain their own state for
    pathfinding and decision-making.
    """

    @abstractmethod
    def decide_next_move(
        self,
        x: float,
        y: float,
        dungeon: 'Dungeon',
    ) -> StrategyCommand:
        """
        Decide the next move for a mob at position (x, y).

        Args:
            x: Current x position in pixels
            y: Current y position in pixels
            dungeon: The dungeon being navigated

        Returns:
            A MoveCommand with the next target position and direction,
            an InteractCommand to interact with an NPC,
            or None if the mob should stay idle.
        """
        pass


class GoalSeekingStrategy(Strategy):
    """
    A strategy that navigates toward the dungeon goal.

    Uses the following algorithm:
    - If the goal is in the same room, move toward it
    - Otherwise, pick a door (preferring non-dead-ends, avoiding the entry door)
    - Track dead ends to avoid revisiting them
    - Use BFS pathfinding to navigate around obstacles
    """

    def __init__(
        self,
        random_choice: Optional[Callable[[List], any]] = None,
    ) -> None:
        # Navigation state
        self.last_door_direction: Optional[int] = None
        self.last_room_id: Optional[int] = None

        # Dead end tracking: set of (room_id, direction) tuples
        self.dead_end_doors: Set[Tuple[int, int]] = set()

        # Target tile (row, col)
        self.next_goal_row: Optional[int] = None
        self.next_goal_col: Optional[int] = None

        # BFS pathfinding state
        self.current_path: Optional[List[Tuple[int, int]]] = None
        self.path_index: int = 0
        self._path_target: Optional[Tuple[int, int]] = None

        # Dependency injection for random selection (for testing)
        self._random_choice: Callable[[List], any] = random_choice or (
            lambda lst: lst[np.random.randint(0, len(lst))]
        )

    def is_dead_end(self, room_id: int, direction: int) -> bool:
        """Check if a door is marked as a dead end."""
        return (room_id, direction) in self.dead_end_doors

    def mark_dead_end(self, room_id: int, direction: int) -> None:
        """Mark a door as a dead end."""
        self.dead_end_doors.add((room_id, direction))

    def _check_and_mark_dead_end(
        self,
        x: float,
        y: float,
        dungeon: 'Dungeon',
        previous_room_id: int,
        entry_direction: int,
    ) -> None:
        """
        Check if the door we just came through should be marked as a dead end.

        A door is a dead end if:
        - The room it leads to has no other doors, OR
        - All other doors in the room (except the entry door) are already marked as dead ends
        """
        # Get the opposite direction (the door we entered through in the current room)
        opposite_direction = (entry_direction + 2) % 4

        current_room_id = dungeon.get_room_id(x, y)
        doors_in_current_room = dungeon.find_doors_in_room(current_room_id)

        # Get all doors except the one we entered through
        other_doors = [d for d in doors_in_current_room if d[0] != opposite_direction]

        # Check if this is a dead end
        is_dead_end = False
        if not other_doors:
            is_dead_end = True
        else:
            all_dead_ends = all(
                self.is_dead_end(current_room_id, d[0]) for d in other_doors
            )
            if all_dead_ends:
                is_dead_end = True

        if is_dead_end:
            self.mark_dead_end(previous_room_id, entry_direction)

    def _update_door_tracking(self, x: float, y: float, dungeon: 'Dungeon') -> None:
        """Update which door we're currently on."""
        col = int(x / TILE_SIZE)
        row = int(y / TILE_SIZE)
        current_tile = dungeon.map[row, col]

        if current_tile in (Tile.NORTH_DOOR_WEST, Tile.NORTH_DOOR_EAST):
            self.last_door_direction = 3
        elif current_tile in (Tile.SOUTH_DOOR_WEST, Tile.SOUTH_DOOR_EAST):
            self.last_door_direction = 1
        elif current_tile in (Tile.EAST_DOOR_NORTH, Tile.EAST_DOOR_SOUTH):
            self.last_door_direction = 0
        elif current_tile in (Tile.WEST_DOOR_NORTH, Tile.WEST_DOOR_SOUTH):
            self.last_door_direction = 2

    def _select_target(self, x: float, y: float, dungeon: 'Dungeon') -> None:
        """Select a new target tile if we don't have one."""
        current_room = dungeon.get_room_id(x, y)

        # First, check if goal is in the same room
        goal_pos = dungeon.find_goal_position()
        if goal_pos:
            goal_room = dungeon.get_room_id(goal_pos[0], goal_pos[1])
            if current_room == goal_room:
                self.next_goal_row = int(goal_pos[1] // TILE_SIZE)
                self.next_goal_col = int(goal_pos[0] // TILE_SIZE)
                return

        # Otherwise, pick a door
        doors = dungeon.find_doors_in_room(current_room)
        other_doors = [d for d in doors if d[0] != self.last_door_direction]
        non_dead_end_doors = [
            d for d in other_doors if not self.is_dead_end(current_room, d[0])
        ]

        if non_dead_end_doors:
            chosen_door = self._random_choice(non_dead_end_doors)
        else:
            chosen_door = doors[0]

        door_dir, door_x, door_y = chosen_door

        # Set target to a tile just beyond the door
        if door_dir == 0:  # East
            self.next_goal_row = int(door_y / TILE_SIZE)
            self.next_goal_col = int(door_x / TILE_SIZE) + 2
        elif door_dir == 1:  # South
            self.next_goal_row = int(door_y / TILE_SIZE) + 2
            self.next_goal_col = int(door_x / TILE_SIZE)
        elif door_dir == 2:  # West
            self.next_goal_row = int(door_y / TILE_SIZE)
            self.next_goal_col = int(door_x / TILE_SIZE) - 2
        elif door_dir == 3:  # North
            self.next_goal_row = int(door_y / TILE_SIZE) - 2
            self.next_goal_col = int(door_x / TILE_SIZE)
        else:
            raise ValueError(f"Invalid door direction {door_dir}")

    def decide_next_move(
        self,
        x: float,
        y: float,
        dungeon: 'Dungeon',
    ) -> StrategyCommand:
        """Decide the next move for a mob at position (x, y)."""
        hero_col = int(x / TILE_SIZE)
        hero_row = int(y / TILE_SIZE)

        # Track door crossings
        self._update_door_tracking(x, y, dungeon)

        current_room = dungeon.get_room_id(x, y)

        # Detect room changes and check for dead ends
        if self.last_room_id is not None and current_room != self.last_room_id:
            if self.last_door_direction is not None:
                self._check_and_mark_dead_end(
                    x, y, dungeon, self.last_room_id, self.last_door_direction
                )
        self.last_room_id = current_room

        # Check if we reached our target
        if hero_row == self.next_goal_row and hero_col == self.next_goal_col:
            self.next_goal_row = None
            self.next_goal_col = None
            self.current_path = None
            self.path_index = 0
            self._path_target = None

        # Select a new target if needed
        if self.next_goal_row is None or self.next_goal_col is None:
            self._select_target(x, y, dungeon)

        # Compute path if needed
        should_recompute_path = (
            self.current_path is None
            or self.path_index >= len(self.current_path)
            or self._path_target != (self.next_goal_row, self.next_goal_col)
        )

        if should_recompute_path:
            new_path = find_path_bfs(
                hero_row,
                hero_col,
                self.next_goal_row,
                self.next_goal_col,
                dungeon.is_tile_walkable,
                max_distance=1000,
            )
            if new_path is None:
                raise ValueError(
                    f"Could not find path to target ({self.next_goal_row}, {self.next_goal_col}) "
                    f"from ({hero_row}, {hero_col})"
                )

            self.current_path = new_path
            self.path_index = 0
            self._path_target = (self.next_goal_row, self.next_goal_col)

        # Follow the computed path
        if self.current_path and self.path_index < len(self.current_path):
            next_row, next_col = self.current_path[self.path_index]

            # Determine direction based on next tile
            if next_col > hero_col:
                direction = 0  # East
            elif next_col < hero_col:
                direction = 2  # West
            elif next_row > hero_row:
                direction = 1  # South
            else:
                direction = 3  # North

            target_x = next_col * TILE_SIZE + TILE_SIZE / 2
            target_y = next_row * TILE_SIZE + TILE_SIZE / 2

            self.path_index += 1

            return MoveCommand(target_x=target_x, target_y=target_y, direction=direction)

        return None
