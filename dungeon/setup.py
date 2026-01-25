"""
Dungeon setup utilities for creating pre-configured dungeons with NPCs.
"""

import random
from typing import Optional, Callable

from .conversation import ConversationPage, ScriptedConversation
from .npc import NPC, TILE_SIZE
from .strategy import GoalSeekingStrategy
from .dungeon_gen import create_random_dungeon
from .world import Dungeon, Hero


def create_robot_priest(
    tile_col: int,
    tile_row: int,
) -> NPC:
    """
    Create a robot priest NPC at the given tile position.

    The robot priest has a 128x192 sprite with a 128x64 (2-tile wide) base.
    Position is specified as the top-left tile of the 2-tile base.

    Args:
        tile_col: Column of the left tile of the base
        tile_row: Row of the base tiles
    """
    # Calculate pixel position (center of 2-tile-wide, 1-tile-tall base)
    x = tile_col * TILE_SIZE + TILE_SIZE  # Center of 2 tiles = left_edge + 64
    y = tile_row * TILE_SIZE + TILE_SIZE / 2  # Center of 1 tile

    conversation = ScriptedConversation(
        [
            ConversationPage(
                text=" ".join(
                    [
                        "Greetings, traveler! I bless you on your quest!",
                        "I will cause the sacred crystal to appear somewhere in this place.",
                        "look for it and recieve your prize!",
                    ]
                ),
                speaker="Placeholder Robot Priest",
                duration=3.0,
            ),
            ConversationPage(
                text=" ".join(
                    [
                        "The prize is a lil' cut scene. We're still working on it,",
                        "it might not have as much context as we'd like right now.",
                    ]
                ),
                speaker="Placeholder Robot Priest",
                duration=3.0,
            ),
            ConversationPage(
                text=" ".join(
                    [
                        "We're still in an alpha release, so we'd appreciate it",
                        "if you'd report any bugs you find.",
                    ]
                ),
                speaker="Placeholder Robot Priest",
                duration=3.0,
            ),
        ]
    )

    return NPC(
        x=x,
        y=y,
        sprite_name="indora_god",
        conversation_engine=conversation,
        npc_id="robot_priest",
    )


def find_floor_tile_in_room(
    dungeon: Dungeon,
    room_id: int,
    min_distance_from_door: int = 2,
) -> Optional[tuple[int, int]]:
    """
    Find a floor tile in the given room suitable for placing an NPC.

    Returns (col, row) in tile coordinates, or None if no suitable tile found.
    Tries to find a tile away from doors for better placement.
    """
    from .dungeon_gen import Tile

    if room_id not in dungeon.room_positions:
        return None

    base_col, base_row = dungeon.room_positions[room_id]
    template = dungeon.room_templates[room_id]

    # Find all floor tiles in the room
    floor_tiles: list[tuple[int, int]] = []
    for local_row in range(template.height):
        for local_col in range(template.width):
            map_row = base_row + local_row
            map_col = base_col + local_col
            if 0 <= map_row < dungeon.rows and 0 <= map_col < dungeon.cols:
                if dungeon.map[map_row, map_col] == Tile.FLOOR:
                    floor_tiles.append((map_col, map_row))

    if not floor_tiles:
        return None

    # Find doors in the room to avoid placing too close
    doors = dungeon.find_doors_in_room(room_id)
    door_tiles = set((col, row) for row, col in doors)

    # Score tiles by distance from doors
    def score_tile(tile: tuple[int, int]) -> int:
        col, row = tile
        min_dist = float("inf")
        for door_row, door_col in doors:
            dist = abs(col - door_col) + abs(row - door_row)
            min_dist = min(min_dist, dist)
        return int(min_dist)

    # Sort by score (prefer tiles far from doors)
    floor_tiles.sort(key=score_tile, reverse=True)

    # Return the best tile that has room for a 2-tile-wide NPC
    for col, row in floor_tiles:
        # Check that both tiles of the 2-wide base are floor
        if dungeon.is_tile_walkable(row, col) and dungeon.is_tile_walkable(
            row, col + 1
        ):
            # Check there's at least one adjacent walkable tile (for hero approach)
            if (
                dungeon.is_tile_walkable(row + 1, col)
                or dungeon.is_tile_walkable(row + 1, col + 1)
                or dungeon.is_tile_walkable(row - 1, col)
                or dungeon.is_tile_walkable(row - 1, col + 1)
                or dungeon.is_tile_walkable(row, col - 1)
                or dungeon.is_tile_walkable(row, col + 2)
            ):
                return (col, row)

    return None


def create_dungeon_with_priest(num_rooms: int) -> tuple[Dungeon, NPC, Hero]:
    """
    Create a dungeon with a robot priest NPC and a hero.

    The dungeon is generated without a goal. When the hero talks to the priest,
    the priest places the goal in a randomly selected room and the hero's
    search state is reset so it can find the newly placed goal.

    Returns:
        Tuple of (dungeon, priest_npc, hero)
    """
    # Generate dungeon without goal - priest will place it after conversation
    dungeon = create_random_dungeon(num_rooms, place_goal=False)

    # Find a suitable position in room 1 (second room)
    priest_pos = find_floor_tile_in_room(dungeon, room_id=1)

    if priest_pos is None:
        # Fallback: try room 0
        priest_pos = find_floor_tile_in_room(dungeon, room_id=0)

    if priest_pos is None:
        raise RuntimeError("Could not find suitable position for robot priest")

    col, row = priest_pos
    priest = create_robot_priest(col, row)
    dungeon.add_npc(priest)

    # Create hero with goal-seeking strategy
    strategy = GoalSeekingStrategy()
    hero = Hero(
        x=dungeon.start_pos[0],
        y=dungeon.start_pos[1],
        strategy=strategy,
    )
    dungeon.add_hero(hero)

    # Set up callback: when conversation completes, place goal and reset hero's search
    def on_priest_conversation_complete() -> None:
        # Pick a random room for the goal (excluding room 0 where hero starts)
        available_rooms = [r for r in dungeon.room_positions.keys() if r != 0]
        goal_room = random.choice(available_rooms)
        dungeon.place_goal(goal_room)
        strategy.reset_search_state()

    priest.on_conversation_complete = on_priest_conversation_complete

    return dungeon, priest, hero
