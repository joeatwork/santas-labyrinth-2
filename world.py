import math
import numpy as np
from dungeon_gen import generate_dungeon, Tile, DungeonMap, ROOM_WIDTH, ROOM_HEIGHT
from typing import Tuple, List, Optional, Callable

TILE_SIZE: int = 64

class Dungeon:
    def __init__(self, width_rooms: int, height_rooms: int) -> None:
        self.map: DungeonMap
        self.start_pos: Tuple[int, int]
        self.map, self.start_pos = generate_dungeon(width_rooms, height_rooms)
        
        self.rows: int
        self.cols: int
        self.rows, self.cols = self.map.shape
        
        self.width_pixels: int = self.cols * TILE_SIZE
        self.height_pixels: int = self.rows * TILE_SIZE

    def is_walkable(self, x: float, y: float) -> bool:
        col = int(x / TILE_SIZE)
        row = int(y / TILE_SIZE)

        if 0 <= row < self.rows and 0 <= col < self.cols:
            tile = self.map[row, col]
            return tile in (
                Tile.FLOOR,
                Tile.GOAL,
                Tile.NORTH_DOOR,
                Tile.SOUTH_DOOR,
                Tile.EAST_DOOR,
                Tile.WEST_DOOR,
            )
        return False

    def get_room_coords(self, x: float, y: float) -> Tuple[int, int]:
        """Returns (room_row, room_col) for a given pixel position."""
        tile_col = int(x / TILE_SIZE)
        tile_row = int(y / TILE_SIZE)
        return (tile_row // ROOM_HEIGHT, tile_col // ROOM_WIDTH)

    def find_goal_position(self) -> Optional[Tuple[float, float]]:
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

    def find_doors_in_room(self, room_row: int, room_col: int) -> List[Tuple[int, float, float]]:
        """
        Returns list of (direction, pixel_x, pixel_y) for doors in the given room.
        Direction: 0=East, 1=South, 2=West, 3=North

        Scans the room tiles for door tile types and returns their center positions.
        """
        doors: List[Tuple[int, float, float]] = []
        found_doors: set[int] = set()  # Track which directions we've found

        base_row = room_row * ROOM_HEIGHT
        base_col = room_col * ROOM_WIDTH

        # Map door tile types to directions
        door_tile_to_direction = {
            Tile.NORTH_DOOR: 3,
            Tile.SOUTH_DOOR: 1,
            Tile.EAST_DOOR: 0,
            Tile.WEST_DOOR: 2,
        }

        # Scan all tiles in the room for door tiles
        for local_row in range(ROOM_HEIGHT):
            for local_col in range(ROOM_WIDTH):
                tile = self.map[base_row + local_row, base_col + local_col]
                if tile in door_tile_to_direction:
                    direction = door_tile_to_direction[tile]
                    # Only add each door direction once (doors span multiple tiles)
                    if direction not in found_doors:
                        found_doors.add(direction)
                        # Calculate door center position
                        door_x = (base_col + local_col + 0.5) * TILE_SIZE
                        door_y = (base_row + local_row + 0.5) * TILE_SIZE
                        doors.append((direction, door_x, door_y))

        return doors

class Hero:
    def __init__(self, x: float, y: float,
                 random_choice: Optional[Callable[[List], any]] = None) -> None:
        self.x: float = float(x)
        self.y: float = float(y)
        self.speed: float = 150.0 # pixels/sec
        self.direction: int = 0 # 0=East, 1=South, 2=West, 3=North
        self.target_x: float = x
        self.target_y: float = y
        self.state: str = 'idle' # idle, walking

        # Animation State
        self.walk_frame: int = 0 # 0 or 1
        self.dist_accumulator: float = 0.0 # Track distance for toggling

        # Navigation state
        self.current_room: Optional[Tuple[int, int]] = None
        self.selected_door: Optional[Tuple[int, float, float]] = None  # (direction, x, y)
        self.entry_door_direction: Optional[int] = None  # Direction of door we entered through

        # Dependency injection for random selection (for testing)
        self._random_choice: Callable[[List], any] = random_choice or (lambda lst: lst[np.random.randint(0, len(lst))])

    def update(self, dt: float, dungeon: Dungeon) -> None:
        if self.state == 'idle':
            self.decide_next_move(dungeon)
            self.walk_frame = 0 # Reset to standing frame when idle
            
        elif self.state == 'walking':
            self.move(dt)

    def decide_next_move(self, dungeon: Dungeon) -> None:
        hero_col = int(self.x / TILE_SIZE)
        hero_row = int(self.y / TILE_SIZE)

        # Check if hero is standing in a door - keep moving through it
        current_tile = dungeon.map[hero_row, hero_col]
        if current_tile in (Tile.NORTH_DOOR, Tile.SOUTH_DOOR, Tile.EAST_DOOR, Tile.WEST_DOOR):
            # Continue in current direction until through the door
            target_col = hero_col
            target_row = hero_row

            if self.direction == 0:  # East
                target_col += 1
            elif self.direction == 1:  # South
                target_row += 1
            elif self.direction == 2:  # West
                target_col -= 1
            elif self.direction == 3:  # North
                target_row -= 1

            target_x = target_col * TILE_SIZE + TILE_SIZE / 2
            target_y = target_row * TILE_SIZE + TILE_SIZE / 2

            if dungeon.is_walkable(target_x, target_y):
                self.target_x = target_x
                self.target_y = target_y
                self.state = 'walking'
            return

        # Find goal position
        goal_pos = dungeon.find_goal_position()
        if goal_pos is None:
            return

        goal_x, goal_y = goal_pos
        goal_col = int(goal_x / TILE_SIZE)
        goal_row = int(goal_y / TILE_SIZE)

        if hero_col == goal_col and hero_row == goal_row:
            # On the goal - don't move
            return

        # Get current room
        current_room = dungeon.get_room_coords(self.x, self.y)
        goal_room = dungeon.get_room_coords(goal_x, goal_y)

        # Reset selected door if we changed rooms
        if current_room != self.current_room:
            # Track which door we entered through (opposite of facing direction)
            # 0=East <-> 2=West, 1=South <-> 3=North
            if self.current_room is not None:
                self.entry_door_direction = (self.direction + 2) % 4
            else:
                self.entry_door_direction = None  # Starting room, no entry door
            self.current_room = current_room
            self.selected_door = None

        # Determine navigation target
        if current_room == goal_room:
            # Same room as goal - approach the goal
            nav_target_x, nav_target_y = goal_x, goal_y
        else:
            # Need to navigate through doors
            doors = dungeon.find_doors_in_room(current_room[0], current_room[1])

            if not doors:
                return  # No doors, can't move

            # Check if we're facing a door (aligned and facing correct direction)
            facing_door = None
            for door in doors:
                door_dir, door_x, door_y = door
                if door_dir == self.direction:
                    # Check if we're aligned with this door
                    if door_dir in (0, 2):  # East/West - check y alignment
                        if abs(self.y - door_y) < TILE_SIZE:
                            facing_door = door
                            break
                    else:  # North/South - check x alignment
                        if abs(self.x - door_x) < TILE_SIZE:
                            facing_door = door
                            break

            if facing_door:
                # Approach the door we're facing
                nav_target_x, nav_target_y = facing_door[1], facing_door[2]
            else:
                # Select a door randomly (but keep it stable)
                if self.selected_door is None or self.selected_door not in doors:
                    # Filter out the entry door if there are other options
                    available_doors = doors
                    if self.entry_door_direction is not None and len(doors) > 1:
                        available_doors = [d for d in doors if d[0] != self.entry_door_direction]
                        if not available_doors:
                            available_doors = doors  # Fallback if filtering removed all
                    self.selected_door = self._random_choice(available_doors)

                # Line up with the selected door, or approach if aligned
                door_dir, door_x, door_y = self.selected_door
                if door_dir in (0, 2):  # East/West door - need to align Y
                    if abs(self.y - door_y) < TILE_SIZE:
                        # Already aligned, approach the door
                        nav_target_x, nav_target_y = door_x, door_y
                    else:
                        nav_target_x, nav_target_y = self.x, door_y
                else:  # North/South door - need to align X
                    if abs(self.x - door_x) < TILE_SIZE:
                        # Already aligned, approach the door
                        nav_target_x, nav_target_y = door_x, door_y
                    else:
                        nav_target_x, nav_target_y = door_x, self.y

        # Calculate direction and target tile toward nav_target
        diff_x = nav_target_x - self.x
        diff_y = nav_target_y - self.y

        # Determine primary direction to move
        if abs(diff_x) > abs(diff_y):
            # Move horizontally
            if diff_x > 0:
                self.direction = 0  # East
            else:
                self.direction = 2  # West
        else:
            # Move vertically
            if diff_y > 0:
                self.direction = 1  # South
            else:
                self.direction = 3  # North

        # Calculate target tile
        target_col = hero_col
        target_row = hero_row

        if self.direction == 0:
            target_col += 1
        elif self.direction == 1:
            target_row += 1
        elif self.direction == 2:
            target_col -= 1
        elif self.direction == 3:
            target_row -= 1

        target_x = target_col * TILE_SIZE + TILE_SIZE / 2
        target_y = target_row * TILE_SIZE + TILE_SIZE / 2

        if dungeon.is_walkable(target_x, target_y):
            self.target_x = target_x
            self.target_y = target_y
            self.state = 'walking'

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
