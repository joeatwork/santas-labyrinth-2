import random
import numpy as np
from dataclasses import dataclass
from typing import Tuple, List, Dict, Set, Optional

# TODO: eliminate optional arguments from functions where possible, prefer explicit parameters.
# Do this throughout the codebase.

# Tile Constants (Matching animation.py expectations or defining new ones)
class Tile:
    NOTHING: int = 0
    FLOOR: int = 1
    NORTH_WALL: int = 10
    SOUTH_WALL: int = 11
    WEST_WALL: int = 12
    EAST_WALL: int = 13
    NW_CORNER: int = 14
    NE_CORNER: int = 15
    SW_CORNER: int = 16
    SE_CORNER: int = 17
    
    # Doors (each direction has two tiles - west/east or north/south halves)
    NORTH_DOOR_WEST: int = 20
    NORTH_DOOR_EAST: int = 21
    SOUTH_DOOR_WEST: int = 22
    SOUTH_DOOR_EAST: int = 23
    WEST_DOOR_NORTH: int = 24
    WEST_DOOR_SOUTH: int = 25
    EAST_DOOR_NORTH: int = 26
    EAST_DOOR_SOUTH: int = 27

    # Goal
    GOAL: int = 30

    # Doorframes (foreground tiles)
    NORTH_DOORFRAME_WEST: int = 40
    NORTH_DOORFRAME_EAST: int = 41
    SOUTH_DOORFRAME_WEST: int = 42
    SOUTH_DOORFRAME_EAST: int = 43
    WEST_DOORFRAME_NORTH: int = 44
    WEST_DOORFRAME_SOUTH: int = 45
    EAST_DOORFRAME_NORTH: int = 46
    EAST_DOORFRAME_SOUTH: int = 47

# Room size in tiles (from references)
ROOM_WIDTH: int = 12
ROOM_HEIGHT: int = 10

# Corridor gap between rooms (for variable-size rooms)
CORRIDOR_GAP: int = 4

# ASCII character to tile mapping
ASCII_TO_TILE: Dict[str, int] = {
    ' ': Tile.NOTHING,
    '.': Tile.FLOOR,
    '-': Tile.NORTH_WALL,
    '_': Tile.SOUTH_WALL,
    '[': Tile.WEST_WALL,
    ']': Tile.EAST_WALL,
    '1': Tile.NW_CORNER,
    '2': Tile.NE_CORNER,
    '3': Tile.SW_CORNER,
    '4': Tile.SE_CORNER,
}

# Door slot characters (converted to door tiles or walls based on required connections)
DOOR_SLOT_CHARS = {'n', 'N', 's', 'S', 'w', 'W', 'e', 'E'}


@dataclass
class RoomTemplate:
    """Defines a room shape using ASCII art."""
    name: str
    ascii_art: List[str]

    @property
    def width(self) -> int:
        return max(len(line) for line in self.ascii_art) if self.ascii_art else 0

    @property
    def height(self) -> int:
        return len(self.ascii_art)

    @property
    def has_north_door(self) -> bool:
        return any('n' in line or 'N' in line for line in self.ascii_art)

    @property
    def has_south_door(self) -> bool:
        return any('s' in line or 'S' in line for line in self.ascii_art)

    @property
    def has_east_door(self) -> bool:
        return any('e' in line or 'E' in line for line in self.ascii_art)

    @property
    def has_west_door(self) -> bool:
        return any('w' in line or 'W' in line for line in self.ascii_art)


# Pre-defined room templates
ROOM_TEMPLATES: List[RoomTemplate] = [
    RoomTemplate(
        name="large",
        ascii_art=[
            "1----nN----2",
            "[..........]",
            "[..........]",
            "[..........]",
            "w..........e",
            "W..........E",
            "[..........]",
            "[..........]",
            "[..........]",
            "3____sS____4",
        ]
    ),
    RoomTemplate(
        name="medium",
        ascii_art=[
            "1--nN--2",
            "[......]",
            "[......]",
            "w......e",
            "W......E",
            "[......]",
            "[......]",
            "3__sS__4",
        ]
    ),
    RoomTemplate(
        name="small",
        ascii_art=[
            "1-nN-2",
            "[....]",
            "w....e",
            "W....E",
            "[....]",
            "3_sS_4",
        ]
    ),
]


def parse_ascii_room(template: RoomTemplate,
                     north_door: bool = False,
                     south_door: bool = False,
                     east_door: bool = False,
                     west_door: bool = False) -> List[List[int]]:
    """
    Parse an ASCII room template into a 2D tile array.

    Door slot characters are converted to door tiles if the corresponding
    door is needed, otherwise to wall tiles.
    """
    tiles: List[List[int]] = []

    for row_idx, line in enumerate(template.ascii_art):
        row: List[int] = []
        for col_idx, char in enumerate(line):
            if char in ASCII_TO_TILE:
                row.append(ASCII_TO_TILE[char])
            elif char == 'n':
                row.append(Tile.NORTH_DOOR_WEST if north_door else Tile.NORTH_WALL)
            elif char == 'N':
                row.append(Tile.NORTH_DOOR_EAST if north_door else Tile.NORTH_WALL)
            elif char == 's':
                row.append(Tile.SOUTH_DOOR_WEST if south_door else Tile.SOUTH_WALL)
            elif char == 'S':
                row.append(Tile.SOUTH_DOOR_EAST if south_door else Tile.SOUTH_WALL)
            elif char == 'w':
                row.append(Tile.WEST_DOOR_NORTH if west_door else Tile.WEST_WALL)
            elif char == 'W':
                row.append(Tile.WEST_DOOR_SOUTH if west_door else Tile.WEST_WALL)
            elif char == 'e':
                row.append(Tile.EAST_DOOR_NORTH if east_door else Tile.EAST_WALL)
            elif char == 'E':
                row.append(Tile.EAST_DOOR_SOUTH if east_door else Tile.EAST_WALL)
            else:
                row.append(Tile.NOTHING)

        # Pad row to template width if needed
        while len(row) < template.width:
            row.append(Tile.NOTHING)

        tiles.append(row)

    return tiles


def get_door_position(template: RoomTemplate, direction: str) -> Optional[Tuple[int, int]]:
    """
    Get the tile position of a door slot in the template.

    Returns (row, col) of the first door tile, or None if no door slot exists.
    Direction: 'north', 'south', 'east', 'west'
    """
    char_map = {
        'north': 'n',
        'south': 's',
        'east': 'e',
        'west': 'w',
    }
    target_char = char_map.get(direction)
    if not target_char:
        return None

    for row_idx, line in enumerate(template.ascii_art):
        for col_idx, char in enumerate(line):
            if char.lower() == target_char:
                return (row_idx, col_idx)

    return None

def generate_maze_graph(rows: int, cols: int) -> Tuple[Dict[Tuple[int, int], List[Tuple[int, int]]], Tuple[int, int], Tuple[int, int]]:
    """
    Generates a grid of connected rooms using a simple DFS maze algorithm.
    Returns:
        connections: dict mapping (r,c) -> list of connected neighbors (r,c)
        start: (r,c)
        end: (r,c)
    """
    # Initialize grid
    grid_cells: List[Tuple[int, int]] = [(r, c) for r in range(rows) for c in range(cols)]
    visited: Set[Tuple[int, int]] = set()
    stack: List[Tuple[int, int]] = []
    connections: Dict[Tuple[int, int], List[Tuple[int, int]]] = {cell: [] for cell in grid_cells}
    
    # Random start
    start: Tuple[int, int] = random.choice(grid_cells)
    stack.append(start)
    visited.add(start)
    
    while stack:
        current = stack[-1]
        r, c = current
        
        # Find unvisited neighbors
        neighbors: List[Tuple[int, int]] = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in visited:
                neighbors.append((nr, nc))
        
        if neighbors:
            next_cell = random.choice(neighbors)
            # Add connection (undirected)
            connections[current].append(next_cell)
            connections[next_cell].append(current)
            
            visited.add(next_cell)
            stack.append(next_cell)
        else:
            stack.pop()
            
    # Pick a random end point that is not start
    end: Tuple[int, int] = start
    while end == start:
        end = random.choice(grid_cells)
        
    return connections, start, end

# Type Definition
DungeonMap = np.ndarray

def generate_foreground_from_dungeon(dungeon_map: DungeonMap) -> DungeonMap:
    """
    Generates a foreground map from an existing dungeon map by detecting door tiles
    and placing corresponding doorframe arch tiles above them.
    """
    rows, cols = dungeon_map.shape
    foreground: DungeonMap = np.zeros((rows, cols), dtype=int)

    # Direct mapping from door tile to doorframe tile
    door_to_doorframe = {
        Tile.NORTH_DOOR_WEST: Tile.NORTH_DOORFRAME_WEST,
        Tile.NORTH_DOOR_EAST: Tile.NORTH_DOORFRAME_EAST,
        Tile.SOUTH_DOOR_WEST: Tile.SOUTH_DOORFRAME_WEST,
        Tile.SOUTH_DOOR_EAST: Tile.SOUTH_DOORFRAME_EAST,
        Tile.WEST_DOOR_NORTH: Tile.WEST_DOORFRAME_NORTH,
        Tile.WEST_DOOR_SOUTH: Tile.WEST_DOORFRAME_SOUTH,
        Tile.EAST_DOOR_NORTH: Tile.EAST_DOORFRAME_NORTH,
        Tile.EAST_DOOR_SOUTH: Tile.EAST_DOORFRAME_SOUTH,
    }

    for r in range(rows):
        for c in range(cols):
            tile = dungeon_map[r, c]
            if tile in door_to_doorframe:
                foreground[r, c] = door_to_doorframe[tile]

    return foreground


def calculate_room_positions(
    room_assignments: Dict[Tuple[int, int], RoomTemplate],
    map_height_rooms: int,
    map_width_rooms: int
) -> Tuple[Dict[Tuple[int, int], Tuple[int, int]], Dict[int, int], Dict[int, int]]:
    """
    Calculate tile positions for each room accounting for variable sizes.

    Returns:
        room_positions: Dict mapping (row, col) to (tile_x, tile_y) top-left position
        col_widths: Dict mapping column index to max room width in that column
        row_heights: Dict mapping row index to max room height in that row
    """
    # Calculate column widths (max room width per column)
    col_widths: Dict[int, int] = {}
    for c in range(map_width_rooms):
        max_width = 0
        for r in range(map_height_rooms):
            if (r, c) in room_assignments:
                max_width = max(max_width, room_assignments[(r, c)].width)
        col_widths[c] = max_width

    # Calculate row heights (max room height per row)
    row_heights: Dict[int, int] = {}
    for r in range(map_height_rooms):
        max_height = 0
        for c in range(map_width_rooms):
            if (r, c) in room_assignments:
                max_height = max(max_height, room_assignments[(r, c)].height)
        row_heights[r] = max_height

    # Calculate positions
    positions: Dict[Tuple[int, int], Tuple[int, int]] = {}
    for (r, c), template in room_assignments.items():
        x = sum(col_widths[i] + CORRIDOR_GAP for i in range(c))
        y = sum(row_heights[i] + CORRIDOR_GAP for i in range(r))
        positions[(r, c)] = (x, y)

    return positions, col_widths, row_heights


def generate_horizontal_corridor(
    door_a_row: int,  # Absolute row of room A's east door (top tile)
    door_a_col: int,  # Absolute col where corridor starts (right of room A)
    door_b_row: int,  # Absolute row of room B's west door (top tile)
    door_b_col: int,  # Absolute col where corridor ends (left of room B)
) -> List[Tuple[int, int, int]]:
    """
    Generate tiles for a horizontal corridor connecting two rooms.

    Returns list of (row, col, tile_type) tuples.
    """
    tiles: List[Tuple[int, int, int]] = []

    # Corridor spans from door_a_col to door_b_col - 1
    corridor_width = door_b_col - door_a_col

    if door_a_row == door_b_row:
        # Straight corridor - doors are aligned
        for col in range(door_a_col, door_b_col):
            # Top wall
            tiles.append((door_a_row - 1, col, Tile.NORTH_WALL))
            # Floor tiles (2 tiles tall for door)
            tiles.append((door_a_row, col, Tile.FLOOR))
            tiles.append((door_a_row + 1, col, Tile.FLOOR))
            # Bottom wall
            tiles.append((door_a_row + 2, col, Tile.SOUTH_WALL))
    else:
        # L-shaped corridor - doors are offset
        # Go straight for half, then turn, then straight again
        mid_col = door_a_col + corridor_width // 2

        # First horizontal segment (from room A door to mid point)
        for col in range(door_a_col, mid_col):
            tiles.append((door_a_row - 1, col, Tile.NORTH_WALL))
            tiles.append((door_a_row, col, Tile.FLOOR))
            tiles.append((door_a_row + 1, col, Tile.FLOOR))
            tiles.append((door_a_row + 2, col, Tile.SOUTH_WALL))

        # Vertical segment
        if door_b_row > door_a_row:
            # Going down
            # Corner at top
            tiles.append((door_a_row - 1, mid_col, Tile.NORTH_WALL))
            tiles.append((door_a_row - 1, mid_col + 1, Tile.NE_CORNER))

            for row in range(door_a_row, door_b_row + 2):
                tiles.append((row, mid_col, Tile.FLOOR))
                tiles.append((row, mid_col + 1, Tile.EAST_WALL))

            # Corner at bottom
            tiles.append((door_b_row + 2, mid_col, Tile.SOUTH_WALL))
            tiles.append((door_b_row + 2, mid_col + 1, Tile.SE_CORNER))
        else:
            # Going up
            # Corner at bottom
            tiles.append((door_a_row + 2, mid_col, Tile.SOUTH_WALL))
            tiles.append((door_a_row + 2, mid_col + 1, Tile.SE_CORNER))

            for row in range(door_b_row, door_a_row + 2):
                tiles.append((row, mid_col, Tile.FLOOR))
                tiles.append((row, mid_col + 1, Tile.EAST_WALL))

            # Corner at top
            tiles.append((door_b_row - 1, mid_col, Tile.NORTH_WALL))
            tiles.append((door_b_row - 1, mid_col + 1, Tile.NE_CORNER))

        # Second horizontal segment (from mid point to room B door)
        for col in range(mid_col, door_b_col):
            tiles.append((door_b_row - 1, col, Tile.NORTH_WALL))
            tiles.append((door_b_row, col, Tile.FLOOR))
            tiles.append((door_b_row + 1, col, Tile.FLOOR))
            tiles.append((door_b_row + 2, col, Tile.SOUTH_WALL))

    return tiles


def generate_vertical_corridor(
    door_a_col: int,  # Absolute col of room A's south door (left tile)
    door_a_row: int,  # Absolute row where corridor starts (below room A)
    door_b_col: int,  # Absolute col of room B's north door (left tile)
    door_b_row: int,  # Absolute row where corridor ends (above room B)
) -> List[Tuple[int, int, int]]:
    """
    Generate tiles for a vertical corridor connecting two rooms.

    Returns list of (row, col, tile_type) tuples.
    """
    
    # TODO: corridors need convex corners to look right.
    tiles: List[Tuple[int, int, int]] = []

    # Corridor spans from door_a_row to door_b_row - 1
    corridor_height = door_b_row - door_a_row

    if door_a_col == door_b_col:
        # Straight corridor - doors are aligned
        for row in range(door_a_row, door_b_row):
            # Left wall
            tiles.append((row, door_a_col - 1, Tile.WEST_WALL))
            # Floor tiles (2 tiles wide for door)
            tiles.append((row, door_a_col, Tile.FLOOR))
            tiles.append((row, door_a_col + 1, Tile.FLOOR))
            # Right wall
            tiles.append((row, door_a_col + 2, Tile.EAST_WALL))
    else:
        # L-shaped corridor - doors are offset
        mid_row = door_a_row + corridor_height // 2

        # First vertical segment
        for row in range(door_a_row, mid_row):
            tiles.append((row, door_a_col - 1, Tile.WEST_WALL))
            tiles.append((row, door_a_col, Tile.FLOOR))
            tiles.append((row, door_a_col + 1, Tile.FLOOR))
            tiles.append((row, door_a_col + 2, Tile.EAST_WALL))

        # Horizontal segment
        if door_b_col > door_a_col:
            # Going right
            tiles.append((mid_row, door_a_col - 1, Tile.WEST_WALL))
            tiles.append((mid_row + 1, door_a_col - 1, Tile.SW_CORNER))

            for col in range(door_a_col, door_b_col + 2):
                tiles.append((mid_row, col, Tile.FLOOR))
                tiles.append((mid_row + 1, col, Tile.SOUTH_WALL))

            tiles.append((mid_row, door_b_col + 2, Tile.EAST_WALL))
            tiles.append((mid_row + 1, door_b_col + 2, Tile.SE_CORNER))
        else:
            # Going left
            tiles.append((mid_row, door_a_col + 2, Tile.EAST_WALL))
            tiles.append((mid_row + 1, door_a_col + 2, Tile.SE_CORNER))

            for col in range(door_b_col - 1, door_a_col + 2):
                tiles.append((mid_row, col, Tile.FLOOR))
                tiles.append((mid_row + 1, col, Tile.SOUTH_WALL))

            tiles.append((mid_row, door_b_col - 1, Tile.WEST_WALL))
            tiles.append((mid_row + 1, door_b_col - 1, Tile.SW_CORNER))

        # Second vertical segment
        for row in range(mid_row, door_b_row):
            tiles.append((row, door_b_col - 1, Tile.WEST_WALL))
            tiles.append((row, door_b_col, Tile.FLOOR))
            tiles.append((row, door_b_col + 1, Tile.FLOOR))
            tiles.append((row, door_b_col + 2, Tile.EAST_WALL))

    return tiles


def generate_dungeon(map_width_rooms: int, map_height_rooms: int) -> Tuple[DungeonMap, Tuple[int, int], Dict[Tuple[int, int], Tuple[int, int]], Dict[Tuple[int, int], RoomTemplate]]:
    """
    Generates a dungeon with variable-size rooms and corridors.

    Returns:
        dungeon_map: The tile map
        start_pos_pixel: Starting position in pixels
        room_positions: Dict mapping (row, col) to (tile_x, tile_y) position
        room_templates: Dict mapping (row, col) to RoomTemplate used
    """
    connections, start_room, end_room = generate_maze_graph(map_height_rooms, map_width_rooms)

    # TODO: corridors must be long enough to allow for L-shapes and doorways, which
    # means at least three tiles of gap between rooms with doors that are not aligned.
    # (one tile each for doorways and one tile for a walkway)

    # Assign random templates to each room
    room_assignments: Dict[Tuple[int, int], RoomTemplate] = {}
    for r in range(map_height_rooms):
        for c in range(map_width_rooms):
            room_assignments[(r, c)] = random.choice(ROOM_TEMPLATES)

    # Calculate room positions
    room_positions, col_widths, row_heights = calculate_room_positions(
        room_assignments, map_height_rooms, map_width_rooms
    )

    # Calculate total map size
    total_width = sum(col_widths.values()) + CORRIDOR_GAP * (map_width_rooms - 1)
    total_height = sum(row_heights.values()) + CORRIDOR_GAP * (map_height_rooms - 1)

    # Create empty map
    dungeon_map: DungeonMap = np.zeros((total_height, total_width), dtype=int)

    # Place rooms
    for (r, c), template in room_assignments.items():
        pos_x, pos_y = room_positions[(r, c)]
        conns = connections[(r, c)]

        # Determine required doors
        north_door = (r - 1, c) in conns
        south_door = (r + 1, c) in conns
        west_door = (r, c - 1) in conns
        east_door = (r, c + 1) in conns

        # Parse and place room tiles
        room_tiles = parse_ascii_room(template, north_door, south_door, east_door, west_door)

        for local_y, row in enumerate(room_tiles):
            for local_x, tile in enumerate(row):
                map_y = pos_y + local_y
                map_x = pos_x + local_x
                if 0 <= map_y < total_height and 0 <= map_x < total_width:
                    dungeon_map[map_y, map_x] = tile

    # Generate corridors for each connection
    processed_connections: Set[Tuple[Tuple[int, int], Tuple[int, int]]] = set()

    for cell_a, neighbors in connections.items():
        for cell_b in neighbors:
            # Avoid processing same connection twice
            conn_key = (min(cell_a, cell_b), max(cell_a, cell_b))
            if conn_key in processed_connections:
                continue
            processed_connections.add(conn_key)

            r_a, c_a = cell_a
            r_b, c_b = cell_b
            template_a = room_assignments[cell_a]
            template_b = room_assignments[cell_b]
            pos_a = room_positions[cell_a]
            pos_b = room_positions[cell_b]

            corridor_tiles: List[Tuple[int, int, int]] = []

            if c_b == c_a + 1:
                # Horizontal connection (A is west of B)
                door_a_pos = get_door_position(template_a, 'east')
                door_b_pos = get_door_position(template_b, 'west')

                if door_a_pos and door_b_pos:
                    # Absolute positions
                    door_a_row = pos_a[1] + door_a_pos[0]
                    door_a_col = pos_a[0] + template_a.width  # Right edge of room A
                    door_b_row = pos_b[1] + door_b_pos[0]
                    door_b_col = pos_b[0]  # Left edge of room B

                    corridor_tiles = generate_horizontal_corridor(
                        door_a_row, door_a_col, door_b_row, door_b_col
                    )

            elif r_b == r_a + 1:
                # Vertical connection (A is north of B)
                door_a_pos = get_door_position(template_a, 'south')
                door_b_pos = get_door_position(template_b, 'north')

                if door_a_pos and door_b_pos:
                    # Absolute positions
                    door_a_col = pos_a[0] + door_a_pos[1]
                    door_a_row = pos_a[1] + template_a.height  # Bottom edge of room A
                    door_b_col = pos_b[0] + door_b_pos[1]
                    door_b_row = pos_b[1]  # Top edge of room B

                    corridor_tiles = generate_vertical_corridor(
                        door_a_col, door_a_row, door_b_col, door_b_row
                    )

            # Place corridor tiles
            for row, col, tile in corridor_tiles:
                if 0 <= row < total_height and 0 <= col < total_width:
                    # Only place if empty (don't overwrite room tiles)
                    if dungeon_map[row, col] == Tile.NOTHING:
                        dungeon_map[row, col] = tile

    # Place goal in center of end room
    end_pos = room_positions[end_room]
    end_template = room_assignments[end_room]
    goal_tile_y = end_pos[1] + end_template.height // 2
    goal_tile_x = end_pos[0] + end_template.width // 2
    dungeon_map[goal_tile_y, goal_tile_x] = Tile.GOAL

    # Calculate start position in pixels
    start_pos = room_positions[start_room]
    start_template = room_assignments[start_room]
    start_pos_pixel = (
        (start_pos[0] + start_template.width // 2) * 64,
        (start_pos[1] + start_template.height // 2) * 64
    )

    return dungeon_map, start_pos_pixel, room_positions, room_assignments


