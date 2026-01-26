#!/usr/bin/env python3
"""
Render a generated dungeon as ASCII art for debugging.

Usage:
    uv run tools/render_dungeon_ascii.py [--width N] [--height N] [--seed S]
"""

import argparse
import random
import sys
from pathlib import Path

# Add parent directory to path so we can import dungeon
sys.path.insert(0, str(Path(__file__).parent.parent))

from dungeon.dungeon_gen import generate_dungeon
from dungeon.metal_labyrinth_sprites import MetalTile


# Mapping from MetalTile IDs to ASCII characters
# Uses the Metal Labyrinth ASCII art conventions from metal_labyrinth_sprites.py
# TODO: share this with the ascii parsing code, it'll tend to rot
# otherwise as we add new tiles.
TILE_TO_ASCII = {
    MetalTile.NOTHING: " ",
    # Corners
    MetalTile.NW_CORNER: "1",
    MetalTile.NE_CORNER: "2",
    MetalTile.SW_CORNER: "3",
    MetalTile.SE_CORNER: "4",
    # Walls
    MetalTile.NORTH_WALL: "-",
    MetalTile.SOUTH_WALL: "_",
    MetalTile.WEST_WALL: "[",
    MetalTile.EAST_WALL: "]",
    # Floor tiles
    MetalTile.FLOOR: ".",
    MetalTile.NORTH_WALL_BASE: ",",  # Shadow row below north walls
    MetalTile.PILLAR_BASE: ";",
    MetalTile.CONVEX_SW_BASE: "<",
    MetalTile.CONVEX_SE_BASE: ">",
    # Convex corners
    MetalTile.CONVEX_NW: "^",
    MetalTile.CONVEX_NE: "!",
    MetalTile.CONVEX_SW: "~",
    MetalTile.CONVEX_SE: "`",
    # Pillar
    MetalTile.PILLAR: "P",
    # Doors
    MetalTile.NORTH_DOOR_WEST: "n",
    MetalTile.NORTH_DOOR_EAST: "N",
    MetalTile.SOUTH_DOOR_WEST: "s",
    MetalTile.SOUTH_DOOR_EAST: "S",
    MetalTile.WEST_DOOR_NORTH: "w",
    MetalTile.WEST_DOOR_SOUTH: "W",
    MetalTile.EAST_DOOR_NORTH: "e",
    MetalTile.EAST_DOOR_SOUTH: "E",
}


def render_dungeon_ascii(dungeon_map):
    """Convert a dungeon map to ASCII string."""
    lines = []
    rows, cols = dungeon_map.shape
    for row in range(rows):
        line = ""
        for col in range(cols):
            tile = dungeon_map[row, col]
            char = TILE_TO_ASCII.get(tile, "?")
            line += char
        lines.append(line)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Render dungeon as ASCII art")
    parser.add_argument("--num-rooms", type=int, default=9, help="Number of rooms in dungeon")
    parser.add_argument("--seed", type=int, help="Random seed for reproducible generation")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    dungeon_map, start_pos, room_positions, room_assignments, goal_room_id = generate_dungeon(
        args.num_rooms
    )

    ascii_art = render_dungeon_ascii(dungeon_map)
    print(ascii_art)

    # Print some debug info
    print(f"\n--- Debug Info ---")
    print(f"Map size: {dungeon_map.shape[1]}x{dungeon_map.shape[0]} tiles")
    print(f"Start position (pixels): {start_pos}")
    print(f"Rooms generated: {len(room_assignments)}")


if __name__ == "__main__":
    main()
