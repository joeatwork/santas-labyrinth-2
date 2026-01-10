import cv2
import numpy as np
import os
import math
from dungeon_gen import Tile

# --- Constants & Sprite Config ---
TILE_SIZE = 64

# Sprite offsets from death_mountain_paradigm_room.png
# and spaceman_overworld_64x64.png
SPRITE_OFFSETS = {
    # Walls (death_mountain)
    'wall_nw_corner': {'x': 0, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/death_mountain_paradigm_room.png'},
    'wall_ne_corner': {'x': 576, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/death_mountain_paradigm_room.png'},
    'wall_sw_corner': {'x': 0, 'y': 576, 'w': 64, 'h': 64, 'file': 'sprites/death_mountain_paradigm_room.png'},
    'wall_se_corner': {'x': 576, 'y': 576, 'w': 64, 'h': 64, 'file': 'sprites/death_mountain_paradigm_room.png'},
    'wall_north': {'x': 64, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/death_mountain_paradigm_room.png'},
    'wall_south': {'x': 64, 'y': 576, 'w': 64, 'h': 64, 'file': 'sprites/death_mountain_paradigm_room.png'},
    'wall_west': {'x': 0, 'y': 64, 'w': 64, 'h': 64, 'file': 'sprites/death_mountain_paradigm_room.png'},
    'wall_east': {'x': 576, 'y': 64, 'w': 64, 'h': 64, 'file': 'sprites/death_mountain_paradigm_room.png'},
    
    # Floor (death_mountain)
    'floor': {'x': 64, 'y': 64, 'w': 64, 'h': 64, 'file': 'sprites/death_mountain_paradigm_room.png'},
    
    # Hero (spaceman)
    'hero_south': {'x': 0, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/spaceman_overworld_64x64.png'},
    'hero_north': {'x': 64, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/spaceman_overworld_64x64.png'},
    'hero_west': {'x': 128, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/spaceman_overworld_64x64.png'},
    'hero_east': {'x': 640, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/spaceman_overworld_64x64.png'},
}

TILE_MAP = {
    Tile.FLOOR: 'floor',
    Tile.NORTH_WALL: 'wall_north',
    Tile.SOUTH_WALL: 'wall_south',
    Tile.WEST_WALL: 'wall_west',
    Tile.EAST_WALL: 'wall_east',
    Tile.NW_CORNER: 'wall_nw_corner',
    Tile.NE_CORNER: 'wall_ne_corner',
    Tile.SW_CORNER: 'wall_sw_corner',
    Tile.SE_CORNER: 'wall_se_corner',
    # Treat unknown tiles as floor for now
    Tile.NOTHING: None
}

class AssetManager:
    def __init__(self):
        self.images = {}
        self.sprites = {}

    def load_images(self):
        unique_files = set(cfg['file'] for cfg in SPRITE_OFFSETS.values())
        for rel_path in unique_files:
            path = os.path.join('assets', rel_path)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Asset not found: {path}")
            
            img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise ValueError(f"Failed to load image: {path}")
            self.images[rel_path] = img

    def get_sprite(self, name):
        if name in self.sprites:
            return self.sprites[name]
        
        cfg = SPRITE_OFFSETS.get(name)
        if not cfg:
            return None
            
        src_img = self.images[cfg['file']]
        x, y, w, h = cfg['x'], cfg['y'], cfg['w'], cfg['h']
        sprite = src_img[y:y+h, x:x+w]
        self.sprites[name] = sprite
        return sprite

def overlay_image(background, foreground, x, y):
    """Overlays fg on bg at (x,y) handling alpha channel."""
    bh, bw = background.shape[:2]
    fh, fw = foreground.shape[:2]
    
    # Check bounds
    if x >= bw or y >= bh or x + fw <= 0 or y + fh <= 0:
        return

    # Clip coordinates
    x1, y1 = max(x, 0), max(y, 0)
    x2, y2 = min(x + fw, bw), min(y + fh, bh)
    
    # Dimensions of overlap
    w, h = x2 - x1, y2 - y1
    
    if w <= 0 or h <= 0:
        return

    # Foreground offsets
    fx1 = max(0, -x)
    fy1 = max(0, -y)
    fx2 = fx1 + w
    fy2 = fy1 + h
    
    fg_crop = foreground[fy1:fy2, fx1:fx2]
    bg_crop = background[y1:y2, x1:x2]
    
    if fg_crop.shape[2] == 4:
        alpha = fg_crop[:, :, 3] / 255.0
        alpha = np.dstack([alpha, alpha, alpha])
        fg_bgr = fg_crop[:, :, :3]
        bg_combined = (1.0 - alpha) * bg_crop + alpha * fg_bgr
        background[y1:y2, x1:x2] = bg_combined.astype(np.uint8)
    else:
        background[y1:y2, x1:x2] = fg_crop

def create_dungeon_background(dungeon_map, assets):
    """
    Creates the full static background image for the dungeon.
    Warning: This can be large.
    """
    rows, cols = dungeon_map.shape
    width = cols * TILE_SIZE
    height = rows * TILE_SIZE
    
    # Create black background
    bg = np.zeros((height, width, 3), np.uint8)
    
    print(f"Generating dungeon background: {width}x{height}...")
    
    for r in range(rows):
        for c in range(cols):
            tile_type = dungeon_map[r, c]
            sprite_name = TILE_MAP.get(tile_type)
            
            if sprite_name:
                sprite = assets.get_sprite(sprite_name)
                if sprite is not None:
                    overlay_image(bg, sprite, c * TILE_SIZE, r * TILE_SIZE)
            elif tile_type != Tile.NOTHING:
                 # Default to floor for unspecified valid tiles
                 sprite = assets.get_sprite('floor')
                 if sprite is not None:
                    overlay_image(bg, sprite, c * TILE_SIZE, r * TILE_SIZE)
                    
    return bg

class Hero:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.speed = 150.0 # pixels/sec
        self.direction = 0 # 0=East, 1=South, 2=West, 3=North
        self.target_x = x
        self.target_y = y
        self.state = 'idle' # idle, walking

    def update(self, dt, dungeon_map):
        # Very simple random walk AI for this PoC
        if self.state == 'idle':
            # Pick a random direction
            self.direction = np.random.randint(0, 4)
            dist = TILE_SIZE
            
            dx, dy = 0, 0
            if self.direction == 0: dx = dist  # East
            elif self.direction == 1: dy = dist # South
            elif self.direction == 2: dx = -dist # West
            elif self.direction == 3: dy = -dist # North
            
            target_col = int((self.x + dx + TILE_SIZE/2) / TILE_SIZE)
            target_row = int((self.y + dy + TILE_SIZE/2) / TILE_SIZE)
            
            # Check collision
            rows, cols = dungeon_map.shape
            if 0 <= target_row < rows and 0 <= target_col < cols:
                tile = dungeon_map[target_row, target_col]
                # Is walkable? (Floor or specific tiles)
                if tile == Tile.FLOOR or tile >= 20: # Floor or Doors
                     self.target_x = self.x + dx
                     self.target_y = self.y + dy
                     self.state = 'walking'
            
        elif self.state == 'walking':
            # Move towards target
            move_dist = self.speed * dt
            
            diff_x = self.target_x - self.x
            diff_y = self.target_y - self.y
            dist_sq = diff_x*diff_x + diff_y*diff_y
            
            if dist_sq <= move_dist*move_dist:
                self.x = self.target_x
                self.y = self.target_y
                self.state = 'idle'
            else:
                angle = math.atan2(diff_y, diff_x)
                self.x += math.cos(angle) * move_dist
                self.y += math.sin(angle) * move_dist

def render_frame_camera(bg_image, assets, hero, view_width, view_height):
    """
    Renders the frame centered on the hero.
    """
    # Create blank canvas
    frame = np.zeros((view_height, view_width, 3), np.uint8)
    
    # Calculate camera top-left
    cam_x = int(hero.x - view_width / 2)
    cam_y = int(hero.y - view_height / 2)
    
    # Clamp camera to map bounds
    map_h, map_w = bg_image.shape[:2]
    cam_x = max(0, min(cam_x, map_w - view_width))
    cam_y = max(0, min(cam_y, map_h - view_height))
    
    # Crop background
    # Handle case where map is smaller than view
    if map_w < view_width or map_h < view_height:
        # Just draw what we can, centered or top-left
        # For simplicity, top-left with black padding
        frame[:min(map_h, view_height), :min(map_w, view_width)] = \
            bg_image[:min(map_h, view_height), :min(map_w, view_width)]
    else:
        # Standard crop
        crop = bg_image[cam_y:cam_y+view_height, cam_x:cam_x+view_width]
        frame[:crop.shape[0], :crop.shape[1]] = crop

    # Draw Hero relative to camera
    hero_screen_x = int(hero.x - cam_x - TILE_SIZE/2) # Center sprite
    hero_screen_y = int(hero.y - cam_y - TILE_SIZE/2) # Center sprite
    
    # Determine sprite based on direction
    # 0=East, 1=South, 2=West, 3=North
    sprite_name = 'hero_south'
    if hero.direction == 0: sprite_name = 'hero_east'
    elif hero.direction == 1: sprite_name = 'hero_south'
    elif hero.direction == 2: sprite_name = 'hero_west'
    elif hero.direction == 3: sprite_name = 'hero_north'
    
    hero_sprite = assets.get_sprite(sprite_name)
    overlay_image(frame, hero_sprite, hero_screen_x, hero_screen_y)

    return frame
