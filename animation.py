import cv2
import numpy as np
import os

# --- Constants & Sprite Config ---
TILE_SIZE = 64

# Sprite offsets from costumes.ts
SPRITE_OFFSETS = {
    'floor': {'x': 64, 'y': 64, 'w': 64, 'h': 64, 'file': 'sprites/death_mountain_paradigm_room.png'},
    'north_wall': {'x': 64, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/death_mountain_paradigm_room.png'},
    'hero_south': {'x': 0, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/spaceman_overworld_64x64.png'},
    'hero_north': {'x': 64, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/spaceman_overworld_64x64.png'},
    'hero_west': {'x': 128, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/spaceman_overworld_64x64.png'},
    'hero_east': {'x': 640, 'y': 0, 'w': 64, 'h': 64, 'file': 'sprites/spaceman_overworld_64x64.png'},
    'empty': {'x': 0, 'y': 0, 'w': 64, 'h': 64, 'file': 'rltiles/nh-dngn_dark_part_of_a_room.png'}
}

class AssetManager:
    def __init__(self):
        self.images = {}
        self.sprites = {}

    def load_images(self):
        # Load all unique files referenced in SPRITE_OFFSETS
        unique_files = set(cfg['file'] for cfg in SPRITE_OFFSETS.values())
        for rel_path in unique_files:
            path = os.path.join('assets', rel_path)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Asset not found: {path}")
            
            # Load image (OpenCV loads in BGR by default)
            # We want to keep alpha channel if present
            img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise ValueError(f"Failed to load image: {path}")
            self.images[rel_path] = img
            print(f"Loaded {rel_path}: {img.shape}")

    def get_sprite(self, name):
        if name in self.sprites:
            return self.sprites[name]
        
        cfg = SPRITE_OFFSETS.get(name)
        if not cfg:
            return None
            
        src_img = self.images[cfg['file']]
        x, y, w, h = cfg['x'], cfg['y'], cfg['w'], cfg['h']
        
        # Extract sprite
        sprite = src_img[y:y+h, x:x+w]
        self.sprites[name] = sprite
        return sprite

def overlay_image(background, foreground, x, y):
    """Overlays fg on bg at (x,y) handling alpha channel."""
    bh, bw = background.shape[:2]
    fh, fw = foreground.shape[:2]
    
    # Clip coordinates to fit within background
    x1, y1 = max(x, 0), max(y, 0)
    x2, y2 = min(x + fw, bw), min(y + fh, bh)
    
    # Dimensions of the overlap area
    w, h = x2 - x1, y2 - y1
    
    if w <= 0 or h <= 0:
        return

    # Corresponding coordinates in foreground
    fx1 = max(0, -x)
    fy1 = max(0, -y)
    fx2 = fx1 + w
    fy2 = fy1 + h
    
    fg_crop = foreground[fy1:fy2, fx1:fx2]
    bg_crop = background[y1:y2, x1:x2]
    
    if fg_crop.shape[2] == 4:
        # Separate alpha channel and normalize to 0-1
        alpha = fg_crop[:, :, 3] / 255.0
        alpha = np.dstack([alpha, alpha, alpha]) # Repeat for BGR channels
        
        # Combine
        fg_bgr = fg_crop[:, :, :3]
        bg_combined = (1.0 - alpha) * bg_crop + alpha * fg_bgr
        background[y1:y2, x1:x2] = bg_combined.astype(np.uint8)
    else:
        # No alpha, just copy
        background[y1:y2, x1:x2] = fg_crop

def create_level_background(width, height, assets):
    """Creates a static background image."""
    bg = np.zeros((height, width, 3), np.uint8)
    
    cols = width // TILE_SIZE + 1
    rows = height // TILE_SIZE + 1
    
    floor_sprite = assets.get_sprite('floor')
    wall_sprite = assets.get_sprite('north_wall')
    
    for r in range(rows):
        for c in range(cols):
            x = c * TILE_SIZE
            y = r * TILE_SIZE
            
            # Simple level design: Walls on top/bottom, floor in middle
            if r == 0 or r == rows - 1:
                overlay_image(bg, wall_sprite, x, y)
            else:
                overlay_image(bg, floor_sprite, x, y)
                
    return bg

def render_frame(bg_image, assets, t):
    """Renders a single frame based on time t."""
    # Copy background to avoid modifying the static one
    frame = bg_image.copy()
    
    h, w = frame.shape[:2]
    
    # Hero movement
    # Move back and forth
    speed = 100 # pixels per second
    cycle_length = (w - TILE_SIZE) / speed * 2
    cycle_pos = t % cycle_length
    
    if cycle_pos < cycle_length / 2:
        # Moving right
        hero_x = int(cycle_pos * speed)
        facing = 'hero_east'
    else:
        # Moving left
        hero_x = int((cycle_length - cycle_pos) * speed)
        facing = 'hero_west'
        
    hero_y = int(h / 2) - int(TILE_SIZE / 2)
    
    # Get hero sprite
    hero_sprite = assets.get_sprite(facing)
    
    overlay_image(frame, hero_sprite, hero_x, hero_y)
    
    # Add text overlay
    cv2.putText(frame, f"Live Stream - Time: {t:.1f}", (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    return frame
