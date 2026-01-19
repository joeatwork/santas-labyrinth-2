import math
import numpy as np
from dungeon_gen import generate_dungeon, Tile, DungeonMap, RoomTemplate
from pathfinding import find_path_bfs
from typing import Tuple, List, Optional, Callable, Dict

TILE_SIZE: int = 64

class Dungeon:
    def __init__(self, width_rooms: int, height_rooms: int) -> None:
        self.map: DungeonMap
        self.start_pos: Tuple[int, int]

        # Room layout information
        self.room_positions: Dict[Tuple[int, int], Tuple[int, int]]
        self.room_templates: Dict[Tuple[int, int], RoomTemplate]

        self.map, self.start_pos, self.room_positions, self.room_templates = generate_dungeon(width_rooms, height_rooms)

        self.rows: int
        self.cols: int
        self.rows, self.cols = self.map.shape

        self.width_pixels: int = self.cols * TILE_SIZE
        self.height_pixels: int = self.rows * TILE_SIZE

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

    def get_room_coords(self, x: float, y: float) -> Tuple[int, int]:
        """Returns (room_row, room_col) for a given pixel position."""
        tile_col = int(x / TILE_SIZE)
        tile_row = int(y / TILE_SIZE)

        # Search through rooms to find which one contains this tile
        for (r, c), (pos_x, pos_y) in self.room_positions.items():
            template = self.room_templates[(r, c)]
            if (pos_x <= tile_col < pos_x + template.width and
                pos_y <= tile_row < pos_y + template.height):
                return (r, c)
        # Not in a room (probably in a corridor) - find nearest room
        # For now, return based on approximate position
        return (0, 0)

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

    # TODO: use a data class for doors rather than tuples
    def find_doors_in_room(self, room_row: int, room_col: int) -> List[Tuple[int, float, float]]:
        """
        Returns list of (direction, pixel_x, pixel_y) for doors in the given room.
        Direction: 0=East, 1=South, 2=West, 3=North

        Scans the room tiles for door tile types and returns their center positions.
        """
        doors: List[Tuple[int, float, float]] = []
        found_doors: set[int] = set()  # Track which directions we've found

        # Determine room bounds
        if (room_row, room_col) not in self.room_positions:
            return doors
        pos_x, pos_y = self.room_positions[(room_row, room_col)]
        template = self.room_templates[(room_row, room_col)]
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

class Hero:
    def __init__(self, x: float, y: float,
                 random_choice: Optional[Callable[[List], any]] = None) -> None:
        
        # Pixel coordinates
        self.x: float = float(x)
        self.y: float = float(y)
        self.speed: float = 150.0 # pixels/sec
        self.direction: int = 0 # 0=East, 1=South, 2=West, 3=North
        
        # Pixel target of next move
        self.target_x: float = x
        self.target_y: float = y

        # Ultimate goal target in row / col
        self.next_goal_row: Optional[int] = None
        self.next_goal_col: Optional[int] = None
        self.state: str = 'idle' # idle, walking

        # Animation State
        self.walk_frame: int = 0 # 0 or 1
        self.dist_accumulator: float = 0.0 # Track distance for toggling

        # Navigation state
        self.last_door_direction: Optional[int] = None  # Direction of last door passed through
        self.current_room: Optional[Tuple[int, int]] = None
        self.selected_door: Optional[Tuple[int, float, float]] = None  # (direction, x, y)
        self.entry_door_direction: Optional[int] = None  # Direction of door we entered through

        # BFS pathfinding state
        self.current_path: Optional[List[Tuple[int, int]]] = None  # List of (row, col) tiles
        self.path_index: int = 0  # Index of next tile to move to
        self._path_target: Optional[Tuple[int, int]] = None  # (row, col) of current path target

        # Dependency injection for random selection (for testing)
        self._random_choice: Callable[[List], any] = random_choice or (lambda lst: lst[np.random.randint(0, len(lst))])

    def update(self, dt: float, dungeon: Dungeon) -> None:
        if self.state == 'idle':
            self.decide_next_move(dungeon)
            self.walk_frame = 0 # Reset to standing frame when idle
            
        elif self.state == 'walking':
            self.move(dt)

    def decide_next_move(self, dungeon: Dungeon) -> None:
        """
        Hero uses the following algorithm to navigate the dungeon:
        
        If the hero has no selected target, select a target based on the following priority:
            - The goal if it is in the same room as the hero
            - A walkable space just beyond a door in the current room that the hero did not pass through most recently
            - A walkable space just beyond the door the hero did pass through most recently

        If the hero has a selected target, compute a path to that target using BFS and follow it.

        When the hero arrives at a target space, forget that target and select a new one.

        """
        hero_col = int(self.x / TILE_SIZE)
        hero_row = int(self.y / TILE_SIZE)

        current_tile = dungeon.map[hero_row, hero_col]
        
        if current_tile in (Tile.NORTH_DOOR_WEST, Tile.NORTH_DOOR_EAST):
            self.last_door_direction = 3            
        elif current_tile in (Tile.SOUTH_DOOR_WEST, Tile.SOUTH_DOOR_EAST):
            self.last_door_direction = 1            
        elif current_tile in (Tile.EAST_DOOR_NORTH, Tile.EAST_DOOR_SOUTH):
            self.last_door_direction = 0            
        elif current_tile in (Tile.WEST_DOOR_NORTH, Tile.WEST_DOOR_SOUTH):
            self.last_door_direction = 2

        current_room = dungeon.get_room_coords(self.x, self.y)

        if hero_row == self.next_goal_row and hero_col == self.next_goal_col:
            # Reached target
            self.next_goal_row = None
            self.next_goal_col = None
            self.current_path = None
            self.path_index = 0
            self._path_target = None

        if self.next_goal_row is None or self.next_goal_col is None:
            # Select new target
            goal_pos = dungeon.find_goal_position()
            if goal_pos:
                # TODO: call get_room_coords with tile positions, not pixel positions
                goal_room = dungeon.get_room_coords(
                    goal_pos[0], goal_pos[1]
                )
                
                if current_room == goal_room:
                    # Goal is in the same room - target it
                    self.next_goal_row = goal_pos[1] // TILE_SIZE
                    self.next_goal_col = goal_pos[0] // TILE_SIZE
        
        if self.next_goal_row is None or self.next_goal_col is None:
            doors = dungeon.find_doors_in_room(current_room[0], current_room[1])
            other_doors = [d for d in doors if d[0] != self.last_door_direction]
            chosen_door = None
            if other_doors:
                # Select a door we did not just come through
                chosen_door = self._random_choice(other_doors)
            elif doors:
                # No other doors, select the door we came through
                chosen_door = doors[0]
            
            if chosen_door:
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
                    raise ValueError("Invalid door direction {door_dir}")
            
        # Check if we need to (re)compute the path
        should_recompute_path = (
            self.current_path is None or
            self.path_index >= len(self.current_path) or
            self._path_target != (self.next_goal_row, self.next_goal_col)
        )

        if should_recompute_path:
            self.current_path = find_path_bfs(
                hero_row, hero_col,
                self.next_goal_row, self.next_goal_col,
                dungeon.is_tile_walkable,
                max_distance=150,
            )
            self.path_index = 0
            self._path_target = (self.next_goal_row, self.next_goal_col)

        # Follow the computed path
        if self.current_path and self.path_index < len(self.current_path):
            next_row, next_col = self.current_path[self.path_index]

            # Update direction based on next tile
            if next_col > hero_col:
                self.direction = 0  # East
            elif next_col < hero_col:
                self.direction = 2  # West
            elif next_row > hero_row:
                self.direction = 1  # South
            elif next_row < hero_row:
                self.direction = 3  # North

            # Set target to next tile center
            self.target_x = next_col * TILE_SIZE + TILE_SIZE / 2
            self.target_y = next_row * TILE_SIZE + TILE_SIZE / 2
            self.state = 'walking'
            self.path_index += 1

    def move(self, dt: float) -> None:
        move_dist = self.speed * dt
        
        diff_x = self.target_x - self.x
        diff_y = self.target_y - self.y
        dist_sq = diff_x*diff_x + diff_y*diff_y
        
        # Animate
        self.dist_accumulator += move_dist
        # Toggle every 32 pixels (half a tile)
        if self.dist_accumulator >= 32.0:
            self.walk_frame = (self.walk_frame + 1) % 2
            self.dist_accumulator = 0.0
        
        if dist_sq <= move_dist*move_dist:
            self.x = self.target_x
            self.y = self.target_y
            self.state = 'idle'
        else:
            angle = math.atan2(diff_y, diff_x)
            self.x += math.cos(angle) * move_dist
            self.y += math.sin(angle) * move_dist
