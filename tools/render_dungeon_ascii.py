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

# Add parent directory to path so we can import dungeon_gen
sys.path.insert(0, str(Path(__file__).parent.parent))

from dungeon_gen import generate_dungeon, Tile


# Mapping from tile IDs to ASCII characters
TILE_TO_ASCII = {
    Tile.NOTHING: " ",
    Tile.FLOOR: ".",
    Tile.NORTH_WALL: "-",
    Tile.SOUTH_WALL: "_",
    Tile.WEST_WALL: "[",
    Tile.EAST_WALL: "]",
    Tile.NW_CORNER: "1",
    Tile.NE_CORNER: "2",
    Tile.SW_CORNER: "3",
    Tile.SE_CORNER: "4",
    Tile.PILLAR: "P",
    Tile.NW_CONVEX_CORNER: "^",
    Tile.NE_CONVEX_CORNER: "!",
    Tile.SW_CONVEX_CORNER: "~",
    Tile.SE_CONVEX_CORNER: ",",
    Tile.DECORATIVE_NORTH_WALL_0: "=",
    Tile.NORTH_DOOR_WEST: "n",
    Tile.NORTH_DOOR_EAST: "N",
    Tile.SOUTH_DOOR_WEST: "s",
    Tile.SOUTH_DOOR_EAST: "S",
    Tile.WEST_DOOR_NORTH: "w",
    Tile.WEST_DOOR_SOUTH: "W",
    Tile.EAST_DOOR_NORTH: "e",
    Tile.EAST_DOOR_SOUTH: "E",
    Tile.GOAL: "G",
    # Doorframes (render same as doors for simplicity)
    Tile.NORTH_DOORFRAME_WEST: "n",
    Tile.NORTH_DOORFRAME_EAST: "N",
    Tile.SOUTH_DOORFRAME_WEST: "s",
    Tile.SOUTH_DOORFRAME_EAST: "S",
    Tile.WEST_DOORFRAME_NORTH: "w",
    Tile.WEST_DOORFRAME_SOUTH: "W",
    Tile.EAST_DOORFRAME_NORTH: "e",
    Tile.EAST_DOORFRAME_SOUTH: "E",
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

    dungeon_map, start_pos, room_positions, room_assignments = generate_dungeon(
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
