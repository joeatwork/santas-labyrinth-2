#!/usr/bin/env python3
"""
Render a dungeon to an image file for visual inspection.

Useful for:
- Designing new room templates
- Verifying tile rendering
- Debugging dungeon generation

Usage:
    uv run tools/render_dungeon_image.py                    # Default: 5 rooms, random seed
    uv run tools/render_dungeon_image.py --rooms 10         # 10 rooms
    uv run tools/render_dungeon_image.py --seed 42          # Reproducible dungeon
    uv run tools/render_dungeon_image.py --output my.png    # Custom output path
"""

import argparse
import cv2
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dungeon.setup import create_dungeon_with_priest
from dungeon.animation import AssetManager, create_dungeon_background, overlay_image, TILE_SIZE


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a dungeon to an image file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--rooms", "-r",
        type=int,
        default=5,
        help="Number of rooms to generate (default: 5)",
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=None,
        help="Random seed for reproducible dungeons",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="dungeon_render.png",
        help="Output image path (default: dungeon_render.png)",
    )
    parser.add_argument(
        "--show-grid",
        action="store_true",
        help="Overlay a tile grid on the image",
    )

    args = parser.parse_args()

    # Set random seed if provided
    if args.seed is not None:
        import random
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")

    # Create dungeon with priest, gate, and goal (matches main system)
    print(f"Generating dungeon with {args.rooms} rooms...")
    dungeon, _priest, hero = create_dungeon_with_priest(args.rooms)
    print(f"Dungeon size: {dungeon.cols}x{dungeon.rows} tiles ({dungeon.width_pixels}x{dungeon.height_pixels} pixels)")

    # Load assets and render
    print("Loading assets...")
    assets = AssetManager()
    assets.load_images()

    print("Rendering dungeon background...")
    image = create_dungeon_background(dungeon.map, assets)

    # Draw NPCs
    print(f"Drawing {len(dungeon.npcs)} NPCs...")
    for npc in dungeon.npcs:
        sprite = assets.get_sprite(npc.sprite_name)
        # Calculate top-left corner for sprite placement
        # npc.x, npc.y is center of base; sprite may extend above/left due to offsets
        sprite_x = int(npc.x - npc.sprite_width / 2 + npc.sprite_offset_x)
        sprite_y = int(npc.y - npc.sprite_height / 2 + npc.sprite_offset_y)
        overlay_image(image, sprite, sprite_x, sprite_y)
        print(f"  {npc.npc_id or npc.sprite_name}: pixel ({int(npc.x)}, {int(npc.y)})")

    # Draw hero
    hero_sprite = assets.get_sprite("hero_south_0")
    hero_x = int(hero.x - 32)
    hero_y = int(hero.y - 32)
    overlay_image(image, hero_sprite, hero_x, hero_y)
    print(f"  hero: pixel ({int(hero.x)}, {int(hero.y)})")

    # Optionally overlay a grid
    if args.show_grid:
        print("Adding tile grid overlay...")
        # Draw vertical lines
        for col in range(dungeon.cols + 1):
            x = col * TILE_SIZE
            cv2.line(image, (x, 0), (x, dungeon.height_pixels), (64, 64, 64), 1)
        # Draw horizontal lines
        for row in range(dungeon.rows + 1):
            y = row * TILE_SIZE
            cv2.line(image, (0, y), (dungeon.width_pixels, y), (64, 64, 64), 1)

    # Mark start position
    start_x, start_y = dungeon.start_pos
    start_col, start_row = start_x // TILE_SIZE, start_y // TILE_SIZE
    cv2.circle(image, (start_x, start_y), 8, (0, 255, 0), -1)  # Green dot at start
    print(f"Start position: tile ({start_col}, {start_row}), pixel ({start_x}, {start_y})")

    # Mark goal position if present
    goal_pos = dungeon.find_goal_position()
    if goal_pos:
        goal_x, goal_y = goal_pos
        goal_col, goal_row = goal_x // TILE_SIZE, goal_y // TILE_SIZE
        cv2.circle(image, (goal_x, goal_y), 8, (0, 0, 255), -1)  # Red dot at goal
        print(f"Goal position: tile ({goal_col}, {goal_row}), pixel ({goal_x}, {goal_y})")

    # Save image
    output_path = Path(args.output)
    cv2.imwrite(str(output_path), image)
    print(f"Saved to: {output_path.absolute()}")

    # Print room info
    print(f"\nRooms ({len(dungeon.room_positions)}):")
    for room_id, (col, row) in sorted(dungeon.room_positions.items()):
        template = dungeon.room_templates[room_id]
        print(f"  Room {room_id}: '{template.name}' at tile ({col}, {row}), size {template.width}x{template.height}")


if __name__ == "__main__":
    main()
