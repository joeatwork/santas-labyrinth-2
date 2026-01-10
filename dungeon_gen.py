import random
import numpy as np

# Tile Constants (Matching animation.py expectations or defining new ones)
class Tile:
    NOTHING = 0
    FLOOR = 1
    NORTH_WALL = 10
    SOUTH_WALL = 11
    WEST_WALL = 12
    EAST_WALL = 13
    NW_CORNER = 14
    NE_CORNER = 15
    SW_CORNER = 16
    SE_CORNER = 17
    
    # Doors (simplified for now, treated as floor or specific sprites if we had them)
    # The original game has specific door tiles, but we might just use floor for openings
    # or specific door sprites if we map them.
    NORTH_DOOR = 20
    SOUTH_DOOR = 21
    WEST_DOOR = 22
    EAST_DOOR = 23

# Room size in tiles (from references)
ROOM_WIDTH = 12
ROOM_HEIGHT = 10

def generate_maze_graph(rows, cols):
    """
    Generates a grid of connected rooms using a simple DFS maze algorithm.
    Returns:
        connections: dict mapping (r,c) -> list of connected neighbors (r,c)
        start: (r,c)
        end: (r,c)
    """
    # Initialize grid
    grid_cells = [(r, c) for r in range(rows) for c in range(cols)]
    visited = set()
    stack = []
    connections = {cell: [] for cell in grid_cells}
    
    # Random start
    start = random.choice(grid_cells)
    stack.append(start)
    visited.add(start)
    
    while stack:
        current = stack[-1]
        r, c = current
        
        # Find unvisited neighbors
        neighbors = []
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
    end = start
    while end == start:
        end = random.choice(grid_cells)
        
    return connections, start, end

def get_room_template(n_door, e_door, s_door, w_door):
    """
    Returns a 2D array of Tiles for a single room based on door presence.
    Based on deathMountainRoom template.
    """
    # Abbreviations for brevity
    # Wall corners
    NWC, NEC, SWC, SEC = Tile.NW_CORNER, Tile.NE_CORNER, Tile.SW_CORNER, Tile.SE_CORNER
    # Walls
    NW, EW, SW, WW = Tile.NORTH_WALL, Tile.EAST_WALL, Tile.SOUTH_WALL, Tile.WEST_WALL
    # Floor
    F = Tile.FLOOR
    
    # Door placeholders (Use floor for walkability, or specialized tiles if we have them)
    # The original code has complex door frames. For this PoC, we'll keep it simple.
    # If a door exists, we put FLOOR. If not, we put WALL.
    
    # Top Row
    row0 = [NWC] + [NW]*10 + [NEC]
    
    # If North Door, open the middle
    if n_door:
        # Indices 5 and 6 are middle-ish (0-11 width)
        row0[5] = F
        row0[6] = F
        
    # Bottom Row
    row9 = [SWC] + [SW]*10 + [SEC]
    if s_door:
        row9[5] = F
        row9[6] = F
        
    # Middle Rows construction
    mid_rows = []
    for r in range(1, 9):
        # West boundary
        left = WW
        if w_door and r in [4, 5]: # Middle vertical
            left = F
            
        # East boundary
        right = EW
        if e_door and r in [4, 5]:
            right = F
            
        row = [left] + [F]*10 + [right]
        mid_rows.append(row)
        
    # Combine
    furniture = [row0] + mid_rows + [row9]
    return furniture

def generate_dungeon(map_width_rooms, map_height_rooms):
    """
    Generates a full tilemap for the dungeon.
    """
    connections, start_room, end_room = generate_maze_graph(map_height_rooms, map_width_rooms)
    
    # Calculate full map size
    full_width = map_width_rooms * ROOM_WIDTH
    full_height = map_height_rooms * ROOM_HEIGHT
    
    # 0 is NOTHING
    dungeon_map = np.zeros((full_height, full_width), dtype=int)
    
    for r in range(map_height_rooms):
        for c in range(map_width_rooms):
            cell = (r, c)
            conns = connections[cell]
            
            # Check directions of connections
            n = (r-1, c) in conns
            s = (r+1, c) in conns
            w = (r, c-1) in conns
            e = (r, c+1) in conns
            
            # Get template
            room_grid = get_room_template(n, e, s, w)
            
            # Place in full map
            y_offset = r * ROOM_HEIGHT
            x_offset = c * ROOM_WIDTH
            
            for local_y, row in enumerate(room_grid):
                for local_x, val in enumerate(row):
                    dungeon_map[y_offset + local_y, x_offset + local_x] = val
                    
    # Calculate start pixel position (approximate center of start room)
    start_pos_pixel = (
        (start_room[1] * ROOM_WIDTH + ROOM_WIDTH//2) * 64, # x
        (start_room[0] * ROOM_HEIGHT + ROOM_HEIGHT//2) * 64 # y
    )

    return dungeon_map, start_pos_pixel
