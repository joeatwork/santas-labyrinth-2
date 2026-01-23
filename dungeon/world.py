import math
from .dungeon_gen import generate_dungeon, Tile, DungeonMap, RoomTemplate
from .strategy import Strategy, GoalSeekingStrategy, MoveCommand, InteractCommand
from .npc import NPC
from typing import Tuple, List, Optional, Callable, Dict

TILE_SIZE: int = 64

class Dungeon:
    def __init__(self, num_rooms: int) -> None:
        self.map: DungeonMap
        self.start_pos: Tuple[int, int]

        # Room layout information
        self.room_positions: Dict[int, Tuple[int, int]]
        self.room_templates: Dict[int, RoomTemplate]

        self.map, self.start_pos, self.room_positions, self.room_templates = generate_dungeon(num_rooms)

        self.rows: int
        self.cols: int
        self.rows, self.cols = self.map.shape

        self.width_pixels: int = self.cols * TILE_SIZE
        self.height_pixels: int = self.rows * TILE_SIZE

        # NPC registry
        self.npcs: List[NPC] = []

        # Hero (set via add_hero() for custom strategies)
        self.hero: Optional['Hero'] = None

    # Tiles that can be walked on
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
        """Returns room_id for a given pixel position."""
        tile_col = int(x / TILE_SIZE)
        tile_row = int(y / TILE_SIZE)

        # Search through rooms to find which one contains this tile
        for room_id, (pos_x, pos_y) in self.room_positions.items():
            template = self.room_templates[room_id]
            if (pos_x <= tile_col < pos_x + template.width and
                pos_y <= tile_row < pos_y + template.height):
                return room_id

        return 0

    # TODO: caller wants a tile position, not a pixel position!
    def find_goal_position(self) -> Optional[Tuple[int, int]]:
        """Returns pixel position (x, y) of the goal tile, or None if not found."""
        for row in range(self.rows):
            for col in range(self.cols):
                if self.map[row, col] == Tile.GOAL:
                    return (col * TILE_SIZE + TILE_SIZE / 2, row * TILE_SIZE + TILE_SIZE / 2)
        return None

    def is_on_goal(self, x: float, y: float) -> bool:
        """Returns True if the given pixel position is on the goal tile."""
        col = int(x / TILE_SIZE)
        row = int(y / TILE_SIZE)
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.map[row, col] == Tile.GOAL
        return False

    def distance_to_goal(self, x: float, y: float) -> float:
        """Returns Euclidean distance in pixels from position (x, y) to the goal."""
        goal_pos = self.find_goal_position()
        if goal_pos is None:
            return float('inf')
        goal_x, goal_y = goal_pos
        dx = goal_x - x
        dy = goal_y - y
        return math.sqrt(dx * dx + dy * dy)

    # TODO: use a data class for doors rather than tuples
    def find_doors_in_room(self, room_id: int) -> List[Tuple[int, float, float]]:
        """
        Returns list of (direction, pixel_x, pixel_y) for doors in the given room.
        Direction: 0=East, 1=South, 2=West, 3=North

        Scans the room tiles for door tile types and returns their center positions.
        """
        doors: List[Tuple[int, float, float]] = []
        found_doors: set[int] = set()  # Track which directions we've found

        # Determine room bounds
        if room_id not in self.room_positions:
            return doors
        pos_x, pos_y = self.room_positions[room_id]
        template = self.room_templates[room_id]
        base_col = pos_x
        base_row = pos_y
        room_width = template.width
        room_height = template.height

        # Map door tile types to directions (use first tile of each door pair)
        door_tile_to_direction = {
            Tile.NORTH_DOOR_WEST: 3,
            Tile.SOUTH_DOOR_WEST: 1,
            Tile.EAST_DOOR_NORTH: 0,
            Tile.WEST_DOOR_NORTH: 2,
        }

        # Scan all tiles in the room for door tiles
        for local_row in range(room_height):
            for local_col in range(room_width):
                map_row = base_row + local_row
                map_col = base_col + local_col
                if 0 <= map_row < self.rows and 0 <= map_col < self.cols:
                    tile = self.map[map_row, map_col]
                    if tile in door_tile_to_direction:
                        direction = door_tile_to_direction[tile]
                        # Only add each door direction once (doors span multiple tiles)
                        if direction not in found_doors:
                            found_doors.add(direction)
                            # Calculate door center position
                            door_x = (map_col + 0.5) * TILE_SIZE
                            door_y = (map_row + 0.5) * TILE_SIZE
                            doors.append((direction, door_x, door_y))

        return doors

    def add_npc(self, npc: NPC) -> None:
        """Add an NPC to the dungeon."""
        npc.room_id = self.get_room_id(npc.x, npc.y)
        self.npcs.append(npc)

    def find_npc_at_tile(self, row: int, col: int) -> Optional[NPC]:
        """Find NPC occupying this tile (for strategy queries)."""
        for npc in self.npcs:
            if npc.tile_row == row and npc.tile_col == col:
                return npc
        return None

    def get_npcs_in_room(self, room_id: int) -> List[NPC]:
        """Get all NPCs in a specific room."""
        return [npc for npc in self.npcs if npc.room_id == room_id]

    def add_hero(self, hero: 'Hero') -> None:
        """Add a hero to the dungeon."""
        self.hero = hero


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
        random_choice: Optional[Callable[[List], any]] = None,
    ) -> None:
        # Pixel coordinates
        self.x: float = float(x)
        self.y: float = float(y)
        self.speed: float = 150.0  # pixels/sec
        self.direction: int = 0  # 0=East, 1=South, 2=West, 3=North

        # Pixel target of next move
        self.target_x: float = x
        self.target_y: float = y

        self.state: str = 'idle'  # idle, walking, talking

        # Animation State
        self.walk_frame: int = 0  # 0 or 1
        self.dist_accumulator: float = 0.0  # Track distance for toggling

        # Navigation strategy
        if strategy is not None:
            self.strategy = strategy
        else:
            self.strategy = GoalSeekingStrategy(random_choice=random_choice)

    def update(self, dt: float, dungeon: 'Dungeon') -> Optional[InteractCommand]:
        """
        Update hero state.

        Returns:
            InteractCommand if strategy wants to interact with an NPC,
            None otherwise.
        """
        if self.state == 'idle':
            interact_cmd = self._decide_next_move(dungeon)
            self.walk_frame = 0  # Reset to standing frame when idle
            return interact_cmd

        elif self.state == 'walking':
            self._move(dt)
            return None

        elif self.state == 'talking':
            # Don't move or decide - DungeonWalk handles conversation
            return None

        return None

    def _decide_next_move(self, dungeon: 'Dungeon') -> Optional[InteractCommand]:
        """Ask the strategy for the next move and apply it."""
        command = self.strategy.decide_next_move(self.x, self.y, dungeon)

        if isinstance(command, MoveCommand):
            self.target_x = command.target_x
            self.target_y = command.target_y
            self.direction = command.direction
            self.state = 'walking'
            return None
        elif isinstance(command, InteractCommand):
            self.state = 'talking'
            return command
        else:
            # None - stay idle
            return None

    def end_conversation(self) -> None:
        """Called by DungeonWalk when conversation ends."""
        if self.state == 'talking':
            self.state = 'idle'

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
            self.state = 'idle'
        else:
            angle = math.atan2(diff_y, diff_x)
            self.x += math.cos(angle) * move_dist
            self.y += math.sin(angle) * move_dist
