import math
import numpy as np
from dungeon_gen import generate_dungeon, Tile

TILE_SIZE = 64

class Dungeon:
    def __init__(self, width_rooms, height_rooms):
        self.map, self.start_pos = generate_dungeon(width_rooms, height_rooms)
        self.rows, self.cols = self.map.shape
        self.width_pixels = self.cols * TILE_SIZE
        self.height_pixels = self.rows * TILE_SIZE

    def is_walkable(self, x, y):
        col = int(x / TILE_SIZE)
        row = int(y / TILE_SIZE)
        
        if 0 <= row < self.rows and 0 <= col < self.cols:
            tile = self.map[row, col]
            # Walkable if Floor or door-like (>= 20)
            return tile == Tile.FLOOR or tile >= 20
        return False

class Hero:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.speed = 150.0 # pixels/sec
        self.direction = 0 # 0=East, 1=South, 2=West, 3=North
        self.target_x = x
        self.target_y = y
        self.state = 'idle' # idle, walking
        
        # Animation State
        self.walk_frame = 0 # 0 or 1
        self.dist_accumulator = 0.0 # Track distance for toggling

    def update(self, dt, dungeon):
        if self.state == 'idle':
            self.decide_next_move(dungeon)
            self.walk_frame = 0 # Reset to standing frame when idle
            
        elif self.state == 'walking':
            self.move(dt)

    def decide_next_move(self, dungeon):
        # Random Walk Logic
        # Try a random direction
        
        # Prefer continuing in same direction with some probability
        if np.random.random() < 0.7:
             pass
        else:
             self.direction = np.random.randint(0, 4)

        dist = TILE_SIZE
        dx, dy = 0, 0
        
        if self.direction == 0: dx = dist  # East
        elif self.direction == 1: dy = dist # South
        elif self.direction == 2: dx = -dist # West
        elif self.direction == 3: dy = -dist # North
        
        # Target center of tile
        curr_col = int(self.x / TILE_SIZE)
        curr_row = int(self.y / TILE_SIZE)
        
        # Target
        target_col = curr_col
        target_row = curr_row
        
        if self.direction == 0: target_col += 1
        elif self.direction == 1: target_row += 1
        elif self.direction == 2: target_col -= 1
        elif self.direction == 3: target_row -= 1
        
        target_x = target_col * TILE_SIZE + TILE_SIZE/2
        target_y = target_row * TILE_SIZE + TILE_SIZE/2

        if dungeon.is_walkable(target_x, target_y):
             self.target_x = target_x
             self.target_y = target_y
             self.state = 'walking'
        else:
             # Turn randomly if hit wall
             self.direction = np.random.randint(0, 4)

    def move(self, dt):
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
