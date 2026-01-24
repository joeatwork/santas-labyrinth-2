#!/usr/bin/env python3
"""
Demo: NPC Conversation

Demonstrates the NPC conversation system with a simple 2-room dungeon.
The hero approaches an NPC, has a conversation, then proceeds to the goal.

Usage:
    uv run demo/conversation.py --output demo_conversation.flv
"""

import argparse
import sys
import os
from typing import List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dungeon.animation import AssetManager
from dungeon.world import Dungeon, Hero, TILE_SIZE
from dungeon.npc import NPC
from dungeon.conversation import ConversationPage, ScriptedConversation
from dungeon.strategy import (
    Strategy,
    StrategyCommand,
    MoveCommand,
    InteractCommand,
    GoalSeekingStrategy,
    TILE_SIZE,
)
from dungeon.pathfinding import find_path_bfs
from streaming import FFmpegStreamer
from content import DungeonWalk


class NPCThenGoalStrategy(Strategy):
    """
    Strategy that first approaches an NPC to interact, then seeks the goal.

    This strategy is specific to the demo and defined here rather than in
    the main strategy module.

    The hero navigates to a tile adjacent to the NPC and triggers the
    interaction when standing next to the NPC.
    """

    def __init__(self, npc: NPC):
        self.npc = npc
        self.has_interacted = False
        self.goal_strategy = GoalSeekingStrategy()

        # Pathfinding state for approaching NPC
        self.current_path: Optional[List[Tuple[int, int]]] = None
        self.path_index: int = 0
        self._path_target: Optional[Tuple[int, int]] = None

    def decide_next_move(
        self,
        x: float,
        y: float,
        dungeon: 'Dungeon',
    ) -> StrategyCommand:
        hero_col = int(x / TILE_SIZE)
        hero_row = int(y / TILE_SIZE)

        if not self.has_interacted:
            # Check if we're adjacent to the NPC
            if dungeon.is_adjacent_to_tile(hero_row, hero_col, self.npc.tile_row, self.npc.tile_col):
                self.has_interacted = True
                return InteractCommand(npc=self.npc)

            # Navigate toward an adjacent tile to the NPC
            return self._navigate_to_npc(hero_row, hero_col, dungeon)
        else:
            # After interaction, seek the goal
            return self.goal_strategy.decide_next_move(x, y, dungeon)

    def _navigate_to_npc(
        self,
        hero_row: int,
        hero_col: int,
        dungeon: 'Dungeon',
    ) -> Optional[MoveCommand]:
        # Find an adjacent walkable tile to the NPC
        adjacent = dungeon.find_adjacent_walkable_tile(self.npc.tile_row, self.npc.tile_col)
        if adjacent is None:
            return None

        target_row, target_col = adjacent

        # Recompute path if needed
        if (
            self.current_path is None
            or self.path_index >= len(self.current_path)
            or self._path_target != (target_row, target_col)
        ):
            new_path = find_path_bfs(
                hero_row,
                hero_col,
                target_row,
                target_col,
                dungeon.is_tile_walkable,
                max_distance=1000,
            )
            if new_path is None:
                return None

            self.current_path = new_path
            self.path_index = 0
            self._path_target = (target_row, target_col)

        # Follow path
        if self.current_path and self.path_index < len(self.current_path):
            next_row, next_col = self.current_path[self.path_index]

            # Determine direction
            if next_col > hero_col:
                direction = 0  # East
            elif next_col < hero_col:
                direction = 2  # West
            elif next_row > hero_row:
                direction = 1  # South
            else:
                direction = 3  # North

            target_x = next_col * TILE_SIZE + TILE_SIZE / 2
            target_y = next_row * TILE_SIZE + TILE_SIZE / 2

            self.path_index += 1
            return MoveCommand(target_x=target_x, target_y=target_y, direction=direction)

        return None


def create_demo_conversation() -> ScriptedConversation:
    """Create a simple conversation for the demo."""
    return ScriptedConversation([
        ConversationPage(text="Hello, traveler!", speaker="NPC", duration=2.5),
        ConversationPage(text="The goal lies ahead. Good luck!", speaker="NPC", duration=2.5),
        ConversationPage(text="Thanks!", speaker="HERO", duration=1.5),
    ])


def setup_dungeon(dungeon: Dungeon) -> None:
    """
    Set up NPCs and hero in the dungeon.

    This function:
    1. Finds a suitable floor tile for the NPC
    2. Creates and adds the NPC to the dungeon
    3. Creates a hero with NPCThenGoalStrategy and adds it to the dungeon
    """
    start_x, start_y = dungeon.start_pos

    # Find a floor tile a few tiles away from start for NPC placement
    # Try tiles in the starting room
    start_row = int(start_y / TILE_SIZE)
    start_col = int(start_x / TILE_SIZE)

    # Look for a walkable tile 2-3 tiles away
    npc_row, npc_col = start_row, start_col + 3
    if not dungeon.is_tile_walkable(npc_row, npc_col):
        # Try other directions
        for dr, dc in [(0, 2), (2, 0), (0, -2), (-2, 0), (1, 1), (1, 2), (2, 1)]:
            test_row, test_col = start_row + dr, start_col + dc
            if dungeon.is_tile_walkable(test_row, test_col):
                npc_row, npc_col = test_row, test_col
                break

    npc_x = npc_col * TILE_SIZE + TILE_SIZE / 2
    npc_y = npc_row * TILE_SIZE + TILE_SIZE / 2

    npc = NPC(
        x=npc_x,
        y=npc_y,
        sprite_name='npc_default',
        conversation_engine=create_demo_conversation(),
    )
    dungeon.add_npc(npc)
    print(f"Placed NPC at tile ({npc_row}, {npc_col})", file=sys.stderr)

    # Create hero with strategy that targets the NPC first
    strategy = GoalSeekingStrategy()
    hero = Hero(start_x, start_y, strategy=strategy)
    dungeon.add_hero(hero)
    print(f"Placed hero at ({start_x}, {start_y})", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="NPC Conversation Demo")
    parser.add_argument("--output", default="demo_conversation.flv", help="Output file")
    parser.add_argument("--width", type=int, default=1280, help="Video width")
    parser.add_argument("--height", type=int, default=720, help="Video height")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second")
    parser.add_argument("--duration", type=float, default=60.0, help="Max duration in seconds")
    parser.add_argument("--num-rooms", type=int, default=2, help="Number of rooms")
    args = parser.parse_args()

    print("Loading assets...", file=sys.stderr)
    assets = AssetManager()
    assets.load_images()
    assets.load_fonts()

    # Create DungeonWalk without goal_movie or ambient_audio
    dungeon_walk = DungeonWalk(
        num_rooms=args.num_rooms,
        assets=assets,
    )

    # Generate the dungeon first, then set up NPCs and hero
    print("Generating dungeon...", file=sys.stderr)
    dungeon_walk.dungeon = Dungeon(args.num_rooms)
    setup_dungeon(dungeon_walk.dungeon)

    # Now call enter() which will use the hero we added
    dungeon_walk.enter()

    print(f"Starting stream to {args.output}...", file=sys.stderr)
    streamer = FFmpegStreamer(
        args.width,
        args.height,
        args.fps,
        args.output,
        audio_sample_rate=44100,
        audio_channels=2,
    )
    streamer.start()

    dt = 1.0 / args.fps
    max_frames = int(args.duration * args.fps)
    frame_count = 0

    print("Rendering frames...", file=sys.stderr)
    for _ in range(max_frames):
        dungeon_walk.update(dt)
        frame = dungeon_walk.render(args.width, args.height)

        if not streamer.write_frame(frame):
            print("Streamer closed", file=sys.stderr)
            break

        # Write silence since we have no audio
        streamer.write_silence(1)

        frame_count += 1

        if dungeon_walk.is_complete():
            print("DungeonWalk complete", file=sys.stderr)
            break

    streamer.close()
    print(f"Demo saved to {args.output} ({frame_count} frames)", file=sys.stderr)


if __name__ == "__main__":
    main()
