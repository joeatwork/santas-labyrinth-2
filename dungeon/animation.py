import cv2
import os
import sys
import numpy as np
from PIL import ImageFont
from dataclasses import dataclass
from dungeon.dungeon_gen import Tile, DungeonMap, generate_foreground_from_dungeon
from dungeon.sprite import Sprite
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
    Protocol,
    TYPE_CHECKING,
    Union,
    cast,
)

if TYPE_CHECKING:
    from dungeon.npc import NPC


@dataclass
class RenderableEntity:
    """An entity that can be rendered, with a sort key for y-ordering."""

    entity: Union["NPC", "HeroLike"]
    sort_y: float  # Bottom of the base (maximum y dimension)
    is_hero: bool


# TODO: this module should probably be named something like dungeon_renderer rather
# than "animation"


class HeroLike(Protocol):
    """Protocol for hero-like objects that can be rendered."""

    x: float
    y: float
    direction: int
    walk_frame: int


# Type Definition
Image = np.ndarray

# --- Constants & Sprite Config ---
TILE_SIZE: int = 64

# Sprite offsets from death_mountain_paradigm_room.png
# and spaceman_overworld_64x64.png
SPRITE_OFFSETS: Dict[str, Sprite] = {
    # Walls (death_mountain)
    "wall_nw_corner": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=0, y=0
    ),
    "wall_ne_corner": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=576, y=0
    ),
    "wall_sw_corner": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=0, y=576
    ),
    "wall_se_corner": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=576, y=576
    ),
    "wall_north": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=64, y=0
    ),
    "wall_south": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=64, y=576
    ),
    "wall_west": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=0, y=64
    ),
    "wall_east": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=576, y=64
    ),
    # Floor (death_mountain)
    "floor": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=64, y=64
    ),
    # Door flooring
    "north_door_floor": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=192, y=640
    ),
    "south_door_floor": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=128, y=640
    ),
    "west_door_floor": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=640, y=128
    ),
    "east_door_floor": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=640, y=192
    ),
    # Pillar
    "pillar": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=0, y=704
    ),
    # Convex corners (inner corners for room intersections)
    "convex_nw": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=128, y=128
    ),
    "convex_ne": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=256, y=128
    ),
    "convex_sw": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=128, y=256
    ),
    "convex_se": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=256, y=256
    ),
    # Decorative north walls (variety of north wall styles)
    "decorative_north_wall_0": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=64, y=768
    ),
    "decorative_north_wall_1": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=128, y=768
    ),
    "decorative_north_wall_2": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=192, y=768
    ),
    "decorative_north_wall_3": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=256, y=768
    ),
    "decorative_north_wall_4": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=64, y=832
    ),
    # Goal
    "goal": Sprite(file="sprites/red_heart.png", x=0, y=0),
    # Doorframes (foreground arches - death_mountain)
    # North doorframes (drawn over north doors)
    "doorframe_north_west": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=256, y=640
    ),
    "doorframe_north_east": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=320, y=640
    ),
    # South doorframes (drawn over south doors)
    "doorframe_south_west": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=0, y=640
    ),
    "doorframe_south_east": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=64, y=640
    ),
    # West doorframes (drawn over west doors)
    "doorframe_west_north": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=640, y=256
    ),
    "doorframe_west_south": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=640, y=320
    ),
    # East doorframes (drawn over east doors)
    "doorframe_east_north": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=640, y=0
    ),
    "doorframe_east_south": Sprite(
        file="sprites/death_mountain_paradigm_room.png", x=640, y=64
    ),
    # Hero Walk Cycles (spaceman)
    # South
    "hero_south_0": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=192, y=0
    ),
    "hero_south_1": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=256, y=0
    ),
    # North
    "hero_north_0": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=320, y=0
    ),
    "hero_north_1": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=384, y=0
    ),
    # West
    "hero_west_0": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=448, y=0
    ),
    "hero_west_1": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=512, y=0
    ),
    # East
    "hero_east_0": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=576, y=0
    ),
    "hero_east_1": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=640, y=0
    ),
    # NPC sprites and walk cycles
    "npc_default": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=0, y=128
    ),
    # South
    "npc_south_0": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=192, y=128
    ),
    "npc_south_1": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=256, y=128
    ),
    # North
    "npc_north_0": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=320, y=128
    ),
    "npc_north_1": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=384, y=128
    ),
    # West
    "npc_west_0": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=448, y=128
    ),
    "npc_west_1": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=512, y=128
    ),
    # East
    "npc_east_0": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=576, y=128
    ),
    "npc_east_1": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=640, y=128
    ),
    # OLD Robot priest (large NPC: 128x192, logical base is bottom 128x64 = 2 tiles)
    "robot_priest": Sprite(
        file="sprites/npcs_01.png",
        x=0,
        y=0,
        width=128,
        height=192,
        base_width=128,
    ),
    # NEW Robot priest (large NPC with weird dimensions, with a weird negative offset)
    "indora_god": Sprite(
        file="sprites/npcs_01.png",
        x=128,
        y=0,
        width=154,
        height=282,
        base_width=128,
        offset_x=-10,
        offset_y=-32,
    ),
    # Portraits for conversation overlay
    "robot_priest_portrait": Sprite(
        file="portraits/npc_portraits_01.png",
        x=0,
        y=0,
        width=256,
        height=256,
    ),
}

# Static lookup for hero sprites: [direction][frame]
# Directions: 0=East, 1=South, 2=West, 3=North
HERO_WALK_CYCLES: Tuple[Tuple[str, str], ...] = (
    ("hero_east_0", "hero_east_1"),  # 0: East
    ("hero_south_0", "hero_south_1"),  # 1: South
    ("hero_west_0", "hero_west_1"),  # 2: West
    ("hero_north_0", "hero_north_1"),  # 3: North
)

TILE_MAP: Dict[int, Optional[str]] = {
    Tile.FLOOR: "floor",
    Tile.NORTH_WALL: "wall_north",
    Tile.SOUTH_WALL: "wall_south",
    Tile.WEST_WALL: "wall_west",
    Tile.EAST_WALL: "wall_east",
    Tile.NW_CORNER: "wall_nw_corner",
    Tile.NE_CORNER: "wall_ne_corner",
    Tile.SW_CORNER: "wall_sw_corner",
    Tile.SE_CORNER: "wall_se_corner",
    Tile.PILLAR: "pillar",
    Tile.NW_CONVEX_CORNER: "convex_nw",
    Tile.NE_CONVEX_CORNER: "convex_ne",
    Tile.SW_CONVEX_CORNER: "convex_sw",
    Tile.SE_CONVEX_CORNER: "convex_se",
    Tile.DECORATIVE_NORTH_WALL_0: "decorative_north_wall_0",
    Tile.DECORATIVE_NORTH_WALL_1: "decorative_north_wall_1",
    Tile.DECORATIVE_NORTH_WALL_2: "decorative_north_wall_2",
    Tile.DECORATIVE_NORTH_WALL_3: "decorative_north_wall_3",
    Tile.NORTH_DOOR_WEST: "north_door_floor",
    Tile.NORTH_DOOR_EAST: "north_door_floor",
    Tile.SOUTH_DOOR_WEST: "south_door_floor",
    Tile.SOUTH_DOOR_EAST: "south_door_floor",
    Tile.WEST_DOOR_NORTH: "west_door_floor",
    Tile.WEST_DOOR_SOUTH: "west_door_floor",
    Tile.EAST_DOOR_NORTH: "east_door_floor",
    Tile.EAST_DOOR_SOUTH: "east_door_floor",
    Tile.NOTHING: None,
}

# Foreground tile mapping (for doorframe arches drawn over hero)
FOREGROUND_TILE_MAP: Dict[int, Optional[str]] = {
    Tile.NORTH_DOORFRAME_WEST: "doorframe_north_west",
    Tile.NORTH_DOORFRAME_EAST: "doorframe_north_east",
    Tile.SOUTH_DOORFRAME_WEST: "doorframe_south_west",
    Tile.SOUTH_DOORFRAME_EAST: "doorframe_south_east",
    Tile.WEST_DOORFRAME_NORTH: "doorframe_west_north",
    Tile.WEST_DOORFRAME_SOUTH: "doorframe_west_south",
    Tile.EAST_DOORFRAME_NORTH: "doorframe_east_north",
    Tile.EAST_DOORFRAME_SOUTH: "doorframe_east_south",
    Tile.NOTHING: None,
}


# TODO: move AssetManager into it's own module, since it's used by non-dungeon code
# (move other non-dungeon code out of animation.py as well)
class AssetManager:
    def __init__(self) -> None:
        self.images: Dict[str, Image] = {}
        self.sprites: Dict[str, Image] = {}
        self.font_sizes: Dict[str, int] = {}
        self.fonts: Dict[str, ImageFont.FreeTypeFont] = {}

    def load_fonts(self) -> None:
        path = os.path.join("assets", "fonts", "ChicagoFLF.ttf")
        self.font_sizes = {
            "regular": 32,
            "small": 16
        }
        self.fonts["regular"] = ImageFont.truetype(path, self.font_sizes["regular"])
        self.fonts["small"] = ImageFont.truetype(path, self.font_sizes["small"])

    def load_images(self) -> None:
        unique_files = set(sprite.file for sprite in SPRITE_OFFSETS.values())
        for rel_path in unique_files:
            path = os.path.join("assets", rel_path)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Asset not found: {path}")

            img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise ValueError(f"Failed to load image: {path}")
            self.images[rel_path] = img

    def get_sprite(self, name: str) -> Image:
        if name in self.sprites:
            return self.sprites[name]

        cfg = SPRITE_OFFSETS[name]

        src_img = self.images[cfg.file]
        sprite = src_img[cfg.y : cfg.y + cfg.height, cfg.x : cfg.x + cfg.width]
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
        fg_bgr = fg_crop[:, :, :3]
        bg_channels = bg_crop.shape[2] if len(bg_crop.shape) > 2 else 3
        # Handle both RGB and RGBA backgrounds
        bg_rgb = bg_crop[:, :, :3] if bg_channels >= 3 else bg_crop
        alpha_3ch = np.dstack([alpha, alpha, alpha])
        blended = (1.0 - alpha_3ch) * bg_rgb + alpha_3ch * fg_bgr
        background[y1:y2, x1:x2, :3] = blended.astype(np.uint8)
        # If background has alpha channel, update it too
        if bg_channels == 4:
            bg_alpha = bg_crop[:, :, 3] / 255.0
            new_alpha = alpha + bg_alpha * (1.0 - alpha)
            background[y1:y2, x1:x2, 3] = (new_alpha * 255).astype(np.uint8)
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
                    sprite = assets.get_sprite("floor")
                    overlay_image(bg, sprite, c * TILE_SIZE, r * TILE_SIZE)
                except Exception:
                    pass

    return bg


def create_dungeon_foreground(dungeon_map: DungeonMap, assets: AssetManager) -> Image:
    """
    Creates the foreground image for the dungeon (doorframe arches).
    This layer is drawn on top of the hero.
    Uses RGBA to support transparency.
    """
    foreground_map = generate_foreground_from_dungeon(dungeon_map)
    rows, cols = foreground_map.shape
    width = cols * TILE_SIZE
    height = rows * TILE_SIZE

    # Create transparent background (RGBA)
    fg: Image = np.zeros((height, width, 4), np.uint8)

    for r in range(rows):
        for c in range(cols):
            tile_type = foreground_map[r, c]
            sprite_name = FOREGROUND_TILE_MAP.get(tile_type)

            if sprite_name:
                sprite = assets.get_sprite(sprite_name)
                overlay_image(fg, sprite, c * TILE_SIZE, r * TILE_SIZE)

    return fg


def render_frame_camera(
    bg_image: Image,
    assets: AssetManager,
    hero: HeroLike,
    npcs: List["NPC"],
    view_width: int,
    view_height: int,
    fg_image: Optional[Image] = None,
) -> Image:
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
        frame[: min(map_h, view_height), : min(map_w, view_width)] = bg_image[
            : min(map_h, view_height), : min(map_w, view_width)
        ]
    else:
        crop = bg_image[cam_y : cam_y + view_height, cam_x : cam_x + view_width]
        frame[: crop.shape[0], : crop.shape[1]] = crop

    # Build list of renderable entities (hero + NPCs) sorted by base bottom y
    # Entities with lower y (higher on screen) render first
    entities: List[RenderableEntity] = []

    # Add hero - base bottom is y + TILE_SIZE/2
    hero_base_bottom = hero.y + TILE_SIZE / 2
    entities.append(
        RenderableEntity(entity=hero, sort_y=hero_base_bottom, is_hero=True)
    )

    # Add NPCs - base bottom is y + base_height/2
    for npc in npcs:
        npc_base_bottom = npc.y + npc.base_height / 2
        entities.append(
            RenderableEntity(entity=npc, sort_y=npc_base_bottom, is_hero=False)
        )

    # Sort by sort_y (lowest y first = higher on screen renders first)
    entities.sort(key=lambda e: e.sort_y)

    # Render entities in sorted order
    for renderable in entities:
        if renderable.is_hero:
            # Draw Hero relative to camera
            hero_screen_x = int(hero.x - cam_x - TILE_SIZE / 2)
            hero_screen_y = int(hero.y - cam_y - TILE_SIZE / 2)

            # Determine sprite based on direction and animation frame
            sprite_name = HERO_WALK_CYCLES[hero.direction][hero.walk_frame]
            hero_sprite = assets.get_sprite(sprite_name)
            overlay_image(frame, hero_sprite, hero_screen_x, hero_screen_y)
        else:
            # Type is guaranteed to be NPC when is_hero=False
            render_npc(frame, cast("NPC", renderable.entity), assets, cam_x, cam_y)

    # Draw foreground layer (doorframe arches) on top of hero
    if fg_image is not None:
        fg_h, fg_w = fg_image.shape[:2]
        if fg_w >= view_width and fg_h >= view_height:
            fg_crop = fg_image[cam_y : cam_y + view_height, cam_x : cam_x + view_width]
            overlay_image(frame, fg_crop, 0, 0)

    return frame


# TODO: inline this into render_frame_camera
def render_npc(
    frame: Image,
    npc: "NPC",
    assets: AssetManager,
    cam_x: int,
    cam_y: int,
) -> None:
    """
    Render an NPC on the frame.

    Supports variable sprite sizes via npc.sprite_width and npc.sprite_height.
    For large NPCs where sprite extends above the base, the sprite is aligned
    so its bottom edge matches the bottom of the logical base.

    NPC position (x, y) is the center of the logical base (base_width x base_height).
    The sprite is centered horizontally on the base but aligned to the bottom.
    Sprite offsets (sprite_offset_x, sprite_offset_y) are applied to adjust positioning.
    """
    # Center sprite horizontally on base center
    npc_screen_x = int(npc.x - cam_x - npc.sprite_width / 2)

    # Align sprite bottom with base bottom
    # base bottom = y + base_height/2
    # sprite bottom should be at that point
    # sprite top = sprite bottom - sprite_height
    base_bottom = npc.y + npc.base_height / 2
    npc_screen_y = int(base_bottom - cam_y - npc.sprite_height)

    # Apply sprite offsets
    npc_screen_x += npc.sprite_offset_x
    npc_screen_y += npc.sprite_offset_y

    try:
        sprite = assets.get_sprite(npc.sprite_name)
        overlay_image(frame, sprite, npc_screen_x, npc_screen_y)
    except KeyError:
        pass  # Sprite not found
