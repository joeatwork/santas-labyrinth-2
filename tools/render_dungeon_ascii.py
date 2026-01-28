#!/usr/bin/env python3
"""
Render a generated dungeon as ASCII art for debugging.

Usage:
    uv run tools/render_dungeon_ascii.py [--num-rooms N] [--seed S]
"""

import argparse
import random
import sys
from pathlib import Path

# Add parent directory to path so we can import dungeon
sys.path.insert(0, str(Path(__file__).parent.parent))

from dungeon.dungeon_gen import create_dungeon_with_gated_goal
from dungeon.metal_labyrinth_sprites import render_dungeon_ascii


def main():
    parser = argparse.ArgumentParser(description="Render dungeon as ASCII art")
    parser.add_argument("--num-rooms", type=int, default=9, help="Number of rooms in dungeon")
    parser.add_argument("--seed", type=int, help="Random seed for reproducible generation")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    dungeon, gate_direction, gate_door_position = create_dungeon_with_gated_goal(
        args.num_rooms
    )

    ascii_art = render_dungeon_ascii(dungeon.map)
    print(ascii_art)

    # Print some debug info
    print(f"\n--- Debug Info ---")
    print(f"Map size: {dungeon.cols}x{dungeon.rows} tiles")
    print(f"Start position (pixels): {dungeon.start_pos}")
    print(f"Rooms generated: {len(dungeon.room_positions)}")
    print(f"Gate direction: {gate_direction.name}")
    print(f"Gate door position: ({gate_door_position.column}, {gate_door_position.row})")


if __name__ == "__main__":
    main()
