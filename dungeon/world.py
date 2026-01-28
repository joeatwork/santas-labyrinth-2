import math
from .dungeon_gen import Tile, DungeonMap, RoomTemplate
from .metal_labyrinth_sprites import WALKABLE_TILES as METAL_WALKABLE_TILES
from .strategy import Strategy, GoalSeekingStrategy, MoveCommand, InteractCommand
from .npc import NPC
from .event_system import EventBus, Event
from typing import Tuple, List, Optional, Callable, Dict, Any, TYPE_CHECKING

# TODO: This import seems incorrect. Why if TYPE_CHECKING?
# and we shouldn't import anything from setup.
if TYPE_CHECKING:
    from .setup import create_goal_npc

TILE_SIZE: int = 64


class Dungeon:
    def __init__(
        self,
        dungeon_map: DungeonMap,
        start_pos: Tuple[int, int],
        room_positions: Dict[int, Tuple[int, int]],
        room_templates: Dict[int, RoomTemplate],
    ) -> None:
        self.map: DungeonMap = dungeon_map
        self.start_pos: Tuple[int, int] = start_pos

        # Room layout information
        self.room_positions: Dict[int, Tuple[int, int]] = room_positions
        self.room_templates: Dict[int, RoomTemplate] = room_templates

        self.rows: int
        self.cols: int
        self.rows, self.cols = self.map.shape

        self.width_pixels: int = self.cols * TILE_SIZE
        self.height_pixels: int = self.rows * TILE_SIZE

        # NPC registry
        self.npcs: List[NPC] = []

        # Hero (set via add_hero() for custom strategies)
        self.hero: Optional["Hero"] = None

        # Event system (optional)
        self.event_bus: Optional[EventBus] = None

    # Tiles that can be walked on (use metal labyrinth walkable tiles)
    WALKABLE_TILES = METAL_WALKABLE_TILES

    def set_event_bus(self, bus: EventBus) -> None:
        """Set the event bus for this dungeon."""
        self.event_bus = bus

    def _emit(self, event: Event, **kwargs: Any) -> None:
        """Emit an event if an event bus is configured."""
        if self.event_bus:
            self.event_bus.emit(event, **kwargs)

    def is_walkable(self, x: float, y: float) -> bool:
        """Check if a pixel position is walkable."""
        col = int(x / TILE_SIZE)
        row = int(y / TILE_SIZE)
        return self.is_tile_walkable(row, col)

    def is_tile_walkable(self, row: int, col: int) -> bool:
        """Check if a tile at (row, col) is walkable."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            tile = self.map[row, col]
            if tile not in self.WALKABLE_TILES:
                return False
            # Check if an NPC occupies this tile
            if self.find_npc_at_tile(row, col) is not None:
                return False
            return True
        return False

    def get_room_id(self, x: float, y: float) -> int:
        """Returns room_id for a given pixel position."""
        col = int(x / TILE_SIZE)
        row = int(y / TILE_SIZE)
        return self.get_room_id_for_tile(row, col)


    def get_room_id_for_tile(self, row: int, col: int) -> int:
        """Return room id for row, column tile"""
        # Search through rooms to find which one contains this tile
        for room_id, (pos_x, pos_y) in self.room_positions.items():
            template = self.room_templates[room_id]
            if (
                pos_x <= col < pos_x + template.width
                and pos_y <= row < pos_y + template.height
            ):
                return room_id

        return 0
        

    def find_goal_npc(self) -> Optional[NPC]:
        """Returns the Goal NPC if present, or None."""
        for npc in self.npcs:
            if npc.is_goal:
                return npc
        return None

    # TODO: caller wants a tile position, not a pixel position!
    def find_goal_position(self) -> Optional[Tuple[int, int]]:
        """Returns pixel position (x, y) of the goal, or None if not found."""
        goal_npc = self.find_goal_npc()
        if goal_npc is not None:
            return (int(goal_npc.x), int(goal_npc.y))
        return None

    def place_goal(self, room_id: int) -> Tuple[int, int]:
        """
        Place the goal NPC in the specified room.

        If a goal already exists, it is removed first.

        Args:
            room_id: The room to place the goal in.

        Returns:
            (col, row) tile coordinates where the goal was placed.

        Raises:
            RuntimeError: If the room doesn't exist or no suitable floor tile can be found.
        """
        from .dungeon_gen import find_floor_tile_in_room, Position
        from .setup import create_goal_npc

        # Remove existing goal NPC if present
        self.remove_goal()

        if room_id not in self.room_positions:
            raise RuntimeError(f"Room {room_id} does not exist")

        # Get room position and template
        pos_col, pos_row = self.room_positions[room_id]
        template = self.room_templates[room_id]
        room_pos = Position(row=pos_row, column=pos_col)

        # Find a floor tile in the room
        goal_pos = find_floor_tile_in_room(self.map, room_pos, template)

        # Create and add the goal NPC
        goal_npc = create_goal_npc(goal_pos.column, goal_pos.row)
        self.add_npc(goal_npc)

        self._emit(Event.GOAL_PLACED, room_id=room_id)

        return (goal_pos.column, goal_pos.row)

    def remove_goal(self) -> None:
        """Remove the goal NPC from the dungeon if present."""
        had_goal = any(npc.is_goal for npc in self.npcs)
        self.npcs = [npc for npc in self.npcs if not npc.is_goal]
        if had_goal:
            self._emit(Event.GOAL_REMOVED)

    def distance_to_goal(self, x: float, y: float) -> float:
        """Returns Euclidean distance in pixels from position (x, y) to the goal NPC."""
        goal_npc = self.find_goal_npc()
        if goal_npc is None:
            return float("inf")
        dx = goal_npc.x - x
        dy = goal_npc.y - y
        return math.sqrt(dx * dx + dy * dy)

    def find_doors_in_room(self, room_id: int) -> List[Tuple[int, int]]:
        """
        Scans the room tiles for door tile types and returns a door tile
        for each door in the room. Returns the door tile as (row, col).
        Which door tile is implementation dependent but it will return 
        only one tile for each door.
        """
        doors: List[Tuple[int, int]] = []

        # Determine room bounds
        if room_id not in self.room_positions:
            raise RuntimeError(f"no such room {room_id}")

        # room_positions to tile offsets
        base_col, base_row = self.room_positions[room_id]
        template = self.room_templates[room_id]
        room_width = template.width
        room_height = template.height

        # Scan all tiles in the room for door tiles
        for local_row in range(room_height):
            for local_col in range(room_width):
                map_row = base_row + local_row
                map_col = base_col + local_col
                if 0 <= map_row < self.rows and 0 <= map_col < self.cols:
                    tile = self.map[map_row, map_col]
                    if tile in (
                        Tile.NORTH_DOOR_WEST,
                        Tile.SOUTH_DOOR_WEST,
                        Tile.EAST_DOOR_NORTH,
                        Tile.WEST_DOOR_NORTH,
                    ):
                        doors.append((map_row, map_col))

        return doors

    def add_npc(self, npc: NPC) -> None:
        """Add an NPC to the dungeon."""
        npc.room_id = self.get_room_id(npc.x, npc.y)
        self.npcs.append(npc)
        self._emit(Event.NPC_ADDED, npc_id=npc.npc_id)

    def remove_npc(self, npc_id: str) -> bool:
        """
        Remove an NPC from the dungeon by its ID.

        Returns True if an NPC was removed, False if no NPC with that ID was found.
        """
        for i, npc in enumerate(self.npcs):
            if npc.npc_id == npc_id:
                self.npcs.pop(i)
                self._emit(Event.NPC_REMOVED, npc_id=npc_id)
                return True
        return False

    def find_npc_at_tile(self, row: int, col: int) -> Optional[NPC]:
        """Find NPC occupying this tile (for strategy queries)."""
        for npc in self.npcs:
            if npc.occupies_tile(row, col):
                return npc
        return None

    def get_npcs_in_room(self, room_id: int) -> List[NPC]:
        """Get all NPCs in a specific room."""
        return [npc for npc in self.npcs if npc.room_id == room_id]

    def add_hero(self, hero: "Hero") -> None:
        """Add a hero to the dungeon."""
        self.hero = hero

    def find_adjacent_walkable_tile(
        self, row: int, col: int
    ) -> Optional[Tuple[int, int]]:
        """
        Find a walkable tile adjacent to the given position.
        Returns (row, col) of a walkable neighbor, or None if none found.
        Prefers South, then East, West, North.
        """
        # Direction order: South, East, West, North
        for dr, dc in [(1, 0), (0, 1), (0, -1), (-1, 0)]:
            adj_row, adj_col = row + dr, col + dc
            if self.is_tile_walkable(adj_row, adj_col):
                return (adj_row, adj_col)
        return None

    def is_adjacent_to_tile(
        self, row: int, col: int, target_row: int, target_col: int
    ) -> bool:
        """Check if (row, col) is adjacent to (target_row, target_col)."""
        dr = abs(row - target_row)
        dc = abs(col - target_col)
        # Adjacent means one step in cardinal direction (not diagonal)
        return (dr == 1 and dc == 0) or (dr == 0 and dc == 1)

    def is_adjacent_to_npc(self, row: int, col: int, npc: NPC) -> bool:
        """
        Check if (row, col) is adjacent to any tile occupied by the NPC.

        For multi-tile NPCs, this checks adjacency to any of the base tiles.
        """
        # Check all tiles occupied by the NPC
        for npc_row in range(npc.tile_row, npc.tile_row + npc.base_tile_height):
            for npc_col in range(npc.tile_col, npc.tile_col + npc.base_tile_width):
                if self.is_adjacent_to_tile(row, col, npc_row, npc_col):
                    return True
        return False


class Hero:
    """
    A hero character that navigates the dungeon.

    The hero's navigation decisions are delegated to a Strategy object,
    while the Hero handles position, movement, and animation state.

    States:
        - idle: Waiting for strategy to decide next move
        - walking: Moving toward target position
        - talking: In conversation with an NPC (managed by DungeonWalk)
    """

    def __init__(
        self,
        x: float,
        y: float,
        strategy: Optional[Strategy] = None,
        random_choice: Optional[Callable[[List], Any]] = None,
    ) -> None:
        # Pixel coordinates
        self.x: float = float(x)
        self.y: float = float(y)
        self.speed: float = 150.0  # pixels/sec
        self.direction: int = 0  # 0=East, 1=South, 2=West, 3=North

        # Pixel target of next move
        self.target_x: float = x
        self.target_y: float = y

        self.state: str = "idle"  # idle, walking, talking

        # Animation State
        self.walk_frame: int = 0  # 0 or 1
        self.dist_accumulator: float = 0.0  # Track distance for toggling

        # Navigation strategy
        if strategy is not None:
            self.strategy = strategy
        else:
            self.strategy = GoalSeekingStrategy(random_choice=random_choice)

    def update(self, dt: float, dungeon: "Dungeon") -> Optional[InteractCommand]:
        """
        Update hero state.

        Returns:
            InteractCommand if strategy wants to interact with an NPC,
            None otherwise.
        """
        if self.state == "idle":
            interact_cmd = self._decide_next_move(dungeon)
            self.walk_frame = 0  # Reset to standing frame when idle
            return interact_cmd

        elif self.state == "walking":
            self._move(dt)
            return None

        elif self.state == "talking":
            # Don't move or decide - DungeonWalk handles conversation
            return None

        return None

    def _decide_next_move(self, dungeon: "Dungeon") -> Optional[InteractCommand]:
        """Ask the strategy for the next move and apply it."""
        command = self.strategy.decide_next_move(self.x, self.y, dungeon)

        if isinstance(command, MoveCommand):
            self.target_x = command.target_x
            self.target_y = command.target_y
            self.direction = command.direction
            self.state = "walking"
            return None
        elif isinstance(command, InteractCommand):
            self.state = "talking"
            return command
        else:
            # None - stay idle
            return None

    def end_conversation(self) -> None:
        """Called by DungeonWalk when conversation ends."""
        if self.state == "talking":
            self.state = "idle"

    def _move(self, dt: float) -> None:
        move_dist = self.speed * dt

        diff_x = self.target_x - self.x
        diff_y = self.target_y - self.y
        dist_sq = diff_x * diff_x + diff_y * diff_y

        # Animate
        self.dist_accumulator += move_dist
        # Toggle every 32 pixels (half a tile)
        if self.dist_accumulator >= 32.0:
            self.walk_frame = (self.walk_frame + 1) % 2
            self.dist_accumulator = 0.0

        if dist_sq <= move_dist * move_dist:
            self.x = self.target_x
            self.y = self.target_y
            self.state = "idle"
        else:
            angle = math.atan2(diff_y, diff_x)
            self.x += math.cos(angle) * move_dist
            self.y += math.sin(angle) * move_dist
