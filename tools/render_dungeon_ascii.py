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
from dungeon.metal_labyrinth_sprites import render_dungeon_ascii


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
