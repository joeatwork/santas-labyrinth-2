"""
Navigation strategies for dungeon mobs.

Strategies handle pathfinding, decision-making, and remembering navigation state.
They are decoupled from the mob's movement and animation.
"""

from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
import sys
from typing import Tuple, List, Optional, Callable, Set, Union, TYPE_CHECKING, Any
import numpy as np

from .dungeon_gen import Tile
from .pathfinding import find_path_bfs

if TYPE_CHECKING:
    from .npc import NPC
    from .world import Dungeon

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

    npc: "NPC"


# Union type for all strategy commands
StrategyCommand = Optional[Union[MoveCommand, InteractCommand]]

# TODO: hero will walk up to north_gate NPC and freeze. We need some
# interaction by the gate so that the gate ends up in npcs_met and
# the hero and move on with their life.
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
        dungeon: "Dungeon",
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
        random_choice: Optional[
            Callable[[List[Tuple[int, int]]], Tuple[int, int]]
        ] = None,
    ) -> None:
        # Keep track of the doors we've traversed, most recent last
        self.lru_doors: OrderedDict[Tuple[int, int], None] = OrderedDict()

        # Keep track of everyone we've talked to
        # by npc_id
        self.npcs_met: Set[str] = set()

        # Target tile (row, col)
        self.next_goal_row: Optional[int] = None
        self.next_goal_col: Optional[int] = None

        # BFS pathfinding state
        self.current_path: Optional[List[Tuple[int, int]]] = None
        self.path_index: int = 0
        self._path_target: Optional[Tuple[int, int]] = None

        # Dependency injection for random selection (for testing)
        self._random_choice: Callable[[List], Any] = random_choice or (
            lambda lst: lst[np.random.randint(0, len(lst))]
        )

    def reset_search_state(self) -> None:
        """
        Reset the strategy's search state.

        Clears the LRU door tracking and path state. Call this when the dungeon
        changes (e.g., when a goal is placed) to allow re-exploration.
        """
        self.lru_doors.clear()
        self.next_goal_row = None
        self.next_goal_col = None
        self.current_path = None
        self.path_index = 0
        self._path_target = None

    def _find_door_northwest_corner(
        self, row: int, col: int, dungeon: "Dungeon"
    ) -> Optional[Tuple[int, int]]:
        """
        returns the (row, col) of the northwest corner of a door if the
        given row, column is any part of a door. Returns None if the
        given row, column isn't part of a door
        """
        current_tile = dungeon.map[row, col]
        if current_tile == Tile.NORTH_DOOR_WEST:
            return (row, col)
        elif current_tile == Tile.NORTH_DOOR_EAST:
            return (row, col - 1)
        elif current_tile == Tile.SOUTH_DOOR_WEST:
            return (row - 1, col)
        elif current_tile == Tile.SOUTH_DOOR_EAST:
            return (row - 1, col - 1)
        elif current_tile == Tile.WEST_DOOR_NORTH:
            return (row, col)
        elif current_tile == Tile.WEST_DOOR_SOUTH:
            return (row - 1, col)
        elif current_tile == Tile.EAST_DOOR_NORTH:
            return (row, col - 1)
        elif current_tile == Tile.EAST_DOOR_SOUTH:
            return (row - 1, col - 1)

        return None

    def _update_door_tracking(self, row, col, dungeon: "Dungeon") -> None:
        """
        Record the door we're currently on, and the door we most recently passed through
        """
        current_door = self._find_door_northwest_corner(row, col, dungeon)
        if current_door is not None:
            if current_door in self.lru_doors:
                self.lru_doors.move_to_end(current_door)
            else:
                self.lru_doors[current_door] = None

    def _select_target(self, x: float, y: float, dungeon: "Dungeon") -> None:
        """Select a new target tile if we don't have one. x and y are pixel positions."""
        self.next_goal_row = None
        self.next_goal_col = None

        current_room = dungeon.get_room_id(x, y)

        # Check if there are NPCs to talk to
        npcs_around = dungeon.get_npcs_in_room(current_room)
        new_npcs = [npc for npc in npcs_around if npc.npc_id not in self.npcs_met]
        for friend in new_npcs:
            approach = self._find_npc_approach_tile(friend, dungeon)
            if approach is not None:
                self.next_goal_row, self.next_goal_col = approach
                return

        # Check if the Goal NPC is in the same room (always approach, even if "met")
        goal_npc = dungeon.find_goal_npc()
        if goal_npc is not None and goal_npc.room_id == current_room:
            approach = self._find_npc_approach_tile(goal_npc, dungeon)
            if approach is not None:
                self.next_goal_row, self.next_goal_col = approach
                return

        # Otherwise, pick a door
        chosen_door: Optional[Tuple[int, int]] = None

        doors = dungeon.find_doors_in_room(current_room)
        keys_and_doors = [
            (self._find_door_northwest_corner(row, col, dungeon), (row, col))
            for (row, col) in doors
        ]
        new_doors: List[Tuple[int, int]] = [
            door for (key, door) in keys_and_doors if key not in self.lru_doors
        ]

        if new_doors:
            chosen_door = self._random_choice(new_doors)
        else:
            doors_by_id = dict(keys_and_doors)
            for id in self.lru_doors.keys():
                if id in doors_by_id:
                    chosen_door = doors_by_id[id]
                    break

        if not chosen_door:
            print(
                "no goal or doors in room {x}, {y}: {current_room}! hero is dead in the water!",
                file=sys.stderr,
            )
            return  # we have nothing to do!

        door_row, door_col = chosen_door
        door_tile = dungeon.map[chosen_door]  # TODO: is this transposed?

        # Set target to a tile just beyond the door
        if door_tile in (Tile.NORTH_DOOR_EAST, Tile.NORTH_DOOR_WEST):
            self.next_goal_row = door_row - 2
            self.next_goal_col = door_col
        elif door_tile in (Tile.SOUTH_DOOR_EAST, Tile.SOUTH_DOOR_WEST):
            self.next_goal_row = door_row + 2
            self.next_goal_col = door_col
        elif door_tile in (Tile.EAST_DOOR_NORTH, Tile.EAST_DOOR_SOUTH):
            self.next_goal_row = door_row
            self.next_goal_col = door_col + 2
        elif door_tile in (Tile.WEST_DOOR_NORTH, Tile.WEST_DOOR_SOUTH):
            self.next_goal_row = door_row
            self.next_goal_col = door_col - 2
        else:
            raise RuntimeError(f"bug identifying door, {chosen_door} is {door_tile}")

    def _find_npc_approach_tile(self, npc, dungeon: "Dungeon") -> Optional[Tuple[int, int]]:
        """
        Find a walkable tile adjacent to the NPC that the hero can stand on.

        Prefers tiles south of the NPC (so hero faces north toward NPC).
        Returns (row, col)
        """
        # Check all tiles adjacent to the NPC's base
        # Prefer south tiles first (so hero faces north)
        candidates: List[Tuple[int, int]] = []

        for npc_col in range(npc.tile_col, npc.tile_col + npc.base_tile_width):
            # South of NPC (below)
            south_row = npc.tile_row + npc.base_tile_height
            if dungeon.is_tile_walkable(south_row, npc_col):
                candidates.append((south_row, npc_col))

        # If no south tiles, try other directions
        if not candidates:
            for npc_row in range(npc.tile_row, npc.tile_row + npc.base_tile_height):
                # East
                east_col = npc.tile_col + npc.base_tile_width
                if dungeon.is_tile_walkable(npc_row, east_col):
                    candidates.append((npc_row, east_col))
                # West
                west_col = npc.tile_col - 1
                if dungeon.is_tile_walkable(npc_row, west_col):
                    candidates.append((npc_row, west_col))

            for npc_col in range(npc.tile_col, npc.tile_col + npc.base_tile_width):
                # North
                north_row = npc.tile_row - 1
                if dungeon.is_tile_walkable(north_row, npc_col):
                    candidates.append((north_row, npc_col))

        return candidates[0] if candidates else None


    def decide_next_move(
        self,
        x: float,
        y: float,
        dungeon: "Dungeon",
    ) -> StrategyCommand:
        """Decide the next move for a mob at position (x, y)."""
        hero_col = int(x / TILE_SIZE)
        hero_row = int(y / TILE_SIZE)

        # Track door crossings
        self._update_door_tracking(hero_row, hero_col, dungeon)

        # Check if we reached our target
        if hero_row == self.next_goal_row and hero_col == self.next_goal_col:
            self.next_goal_row = None
            self.next_goal_col = None
            self.current_path = None
            self.path_index = 0
            self._path_target = None

        # Check if adjacent to the Goal NPC first (highest priority interaction)
        goal_npc = dungeon.find_goal_npc()
        if goal_npc is not None and dungeon.is_adjacent_to_npc(hero_row, hero_col, goal_npc):
            return InteractCommand(goal_npc)

        # Check if we have an available conversation with regular NPCs
        room_id = dungeon.get_room_id_for_tile(hero_row, hero_col)
        npcs_around = dungeon.get_npcs_in_room(room_id)
        new_npcs = [npc for npc in npcs_around if npc.npc_id not in self.npcs_met and not npc.is_goal]
        for friend in new_npcs:
            if dungeon.is_adjacent_to_npc(hero_row, hero_col, friend):
                self.npcs_met.add(friend.npc_id)
                return InteractCommand(friend)             

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
            # Type narrowing: ensure goal is set
            if self.next_goal_row is None or self.next_goal_col is None:
                # No valid target, stay idle
                return MoveCommand(target_x=x, target_y=y, direction=0)

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

            return MoveCommand(
                target_x=target_x, target_y=target_y, direction=direction
            )

        return None
