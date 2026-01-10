import random
import numpy as np
from typing import Tuple, List, Dict, Set

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
    
    # Doors (simplified for now, treated as floor or specific sprites if we had them)
    NORTH_DOOR: int = 20
    SOUTH_DOOR: int = 21
    WEST_DOOR: int = 22
    EAST_DOOR: int = 23

# Room size in tiles (from references)
ROOM_WIDTH: int = 12
ROOM_HEIGHT: int = 10

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

def get_room_template(n_door: bool, e_door: bool, s_door: bool, w_door: bool) -> List[List[int]]:
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
    
    # Top Row
    row0: List[int] = [NWC] + [NW]*10 + [NEC]
    
    # If North Door, open the middle
    if n_door:
        # Indices 5 and 6 are middle-ish (0-11 width)
        row0[5] = F
        row0[6] = F
        
    # Bottom Row
    row9: List[int] = [SWC] + [SW]*10 + [SEC]
    if s_door:
        row9[5] = F
        row9[6] = F
        
    # Middle Rows construction
    mid_rows: List[List[int]] = []
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


# Type Definition
DungeonMap = np.ndarray

def generate_dungeon(map_width_rooms: int, map_height_rooms: int) -> Tuple[DungeonMap, Tuple[int, int]]:
    """
    Generates a full tilemap for the dungeon.
    """
    connections, start_room, end_room = generate_maze_graph(map_height_rooms, map_width_rooms)
    
    # Calculate full map size
    full_width = map_width_rooms * ROOM_WIDTH
    full_height = map_height_rooms * ROOM_HEIGHT
    
    # 0 is NOTHING
    dungeon_map: DungeonMap = np.zeros((full_height, full_width), dtype=int)
    
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
