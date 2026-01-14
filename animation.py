import cv2
import os
import sys
import numpy as np
from dungeon_gen import Tile, DungeonMap
from world import Hero
from typing import Dict, Any, Optional, Tuple

# Type Definition
Image = np.ndarray

# --- Constants & Sprite Config ---
TILE_SIZE: int = 64

# Sprite offsets from death_mountain_paradigm_room.png
# and spaceman_overworld_64x64.png
SPRITE_OFFSETS: Dict[str, Dict[str, Any]] = {
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
    
    # Hero Walk Cycles (spaceman)
    # South
    'hero_south_0': {'x': 192, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/spaceman_overworld_64x64.png'},
    'hero_south_1': {'x': 256, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/spaceman_overworld_64x64.png'},
    # North
    'hero_north_0': {'x': 320, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/spaceman_overworld_64x64.png'},
    'hero_north_1': {'x': 384, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/spaceman_overworld_64x64.png'},
    # West
    'hero_west_0': {'x': 448, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/spaceman_overworld_64x64.png'},
    'hero_west_1': {'x': 512, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/spaceman_overworld_64x64.png'},
    # East
    'hero_east_0': {'x': 576, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/spaceman_overworld_64x64.png'},
    'hero_east_1': {'x': 640, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/spaceman_overworld_64x64.png'},
}

# Static lookup for hero sprites: [direction][frame]
# Directions: 0=East, 1=South, 2=West, 3=North
HERO_WALK_CYCLES: Tuple[Tuple[str, str], ...] = (
    ('hero_east_0', 'hero_east_1'),   # 0: East
    ('hero_south_0', 'hero_south_1'), # 1: South
    ('hero_west_0', 'hero_west_1'),   # 2: West
    ('hero_north_0', 'hero_north_1'), # 3: North
)

TILE_MAP: Dict[int, Optional[str]] = {
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
    def __init__(self) -> None:
        self.images: Dict[str, Image] = {}
        self.sprites: Dict[str, Image] = {}

    def load_images(self) -> None:
        unique_files = set(cfg['file'] for cfg in SPRITE_OFFSETS.values())
        for rel_path in unique_files:
            path = os.path.join('assets', rel_path)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Asset not found: {path}")
            
            img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise ValueError(f"Failed to load image: {path}")
            self.images[rel_path] = img

    def get_sprite(self, name: str) -> Image:
        if name in self.sprites:
            return self.sprites[name]
        
        cfg = SPRITE_OFFSETS[name] # Adjusted to match user's non-safe access edit expectation
            
        src_img = self.images[cfg['file']]
        x, y, w, h = int(cfg['x']), int(cfg['y']), int(cfg['w']), int(cfg['h'])
        sprite = src_img[y:y+h, x:x+w]
        self.sprites[name] = sprite
        return sprite

def overlay_image(background: Image, foreground: Image, x: int, y: int) -> None:
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

def create_dungeon_background(dungeon_map: DungeonMap, assets: AssetManager) -> Image:
    """
    Creates the full static background image for the dungeon.
    """
    rows, cols = dungeon_map.shape
    width = cols * TILE_SIZE
    height = rows * TILE_SIZE
    
    # Create black background
    bg: Image = np.zeros((height, width, 3), np.uint8)
    
    print(f"Generating dungeon background: {width}x{height}...", file=sys.stderr)
    
    for r in range(rows):
        for c in range(cols):
            tile_type = dungeon_map[r, c]
            sprite_name = TILE_MAP.get(tile_type)
            
            if sprite_name:
                sprite = assets.get_sprite(sprite_name)
                # sprite is guaranteed Image by type hint, but might fail logic if key missing
                # get_sprite raises keyerror if missing, so we are safe assuming returns Image
                overlay_image(bg, sprite, c * TILE_SIZE, r * TILE_SIZE)
            elif tile_type != Tile.NOTHING:
                 # Default to floor for specified tiles that are missing mappings
                 try:
                    sprite = assets.get_sprite('floor')
                    overlay_image(bg, sprite, c * TILE_SIZE, r * TILE_SIZE)
                 except Exception:
                     pass
                    
    return bg

def render_frame_camera(bg_image: Image, assets: AssetManager, hero: Hero, view_width: int, view_height: int) -> Image:
    """
    Renders the frame centered on the hero.
    """
    # Create blank canvas
    frame: Image = np.zeros((view_height, view_width, 3), np.uint8)
    
    # Calculate camera top-left
    cam_x = int(hero.x - view_width / 2)
    cam_y = int(hero.y - view_height / 2)
    
    # Clamp camera to map bounds
    map_h, map_w = bg_image.shape[:2]
    cam_x = max(0, min(cam_x, map_w - view_width))
    cam_y = max(0, min(cam_y, map_h - view_height))
    
    # Crop background
    if map_w < view_width or map_h < view_height:
        frame[:min(map_h, view_height), :min(map_w, view_width)] = \
            bg_image[:min(map_h, view_height), :min(map_w, view_width)]
    else:
        crop = bg_image[cam_y:cam_y+view_height, cam_x:cam_x+view_width]
        frame[:crop.shape[0], :crop.shape[1]] = crop

    # Draw Hero relative to camera
    hero_screen_x = int(hero.x - cam_x - TILE_SIZE/2) 
    hero_screen_y = int(hero.y - cam_y - TILE_SIZE/2) 
    
    # Determine sprite based on direction and animation frame
    # Lookup sprite name from static table
    try:
        sprite_name = HERO_WALK_CYCLES[hero.direction][hero.walk_frame]
    except IndexError:
        # Fallback
        sprite_name = HERO_WALK_CYCLES[hero.direction][0]
    
    try:
        hero_sprite = assets.get_sprite(sprite_name)
        overlay_image(frame, hero_sprite, hero_screen_x, hero_screen_y)
    except KeyError:
        pass # Should not happen with correct data

    return frame
