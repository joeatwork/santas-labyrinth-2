"""
Dungeon setup utilities for creating pre-configured dungeons with NPCs.
"""

from typing import Optional, Callable

from .conversation import ConversationPage, ScriptedConversation
from .npc import NPC, TILE_SIZE
from .strategy import GoalSeekingStrategy
from .dungeon_gen import create_dungeon_with_gated_goal, Direction
from .world import Dungeon, Hero

def create_north_gate_npc(
    tile_col: int,
    tile_row: int,
) -> NPC:
    """
    Create a north gate NPC at the given tile position.

    The north gate is a 128x128 sprite (2 tiles wide, 2 tiles tall) that blocks
    a north door. It can be removed to allow the hero to pass through.

    Args:
        tile_col: Column of the left tile of the base
        tile_row: Row of the top tile of the base
    """
    # Calculate pixel position (center of 2-tile-wide, 2-tile-tall base)
    x = tile_col * TILE_SIZE + TILE_SIZE  # Center of 2 tiles
    y = tile_row * TILE_SIZE + TILE_SIZE  # Center of 2 tiles

    return NPC(
        x=x,
        y=y,
        sprite_name="north_gate",
        npc_id="north_gate",
    )


# TODO: create_goal_npc should be inlined where it is used.
def create_goal_npc(
    tile_col: int,
    tile_row: int,
) -> NPC:
    """
    Create a Goal NPC at the given tile position.

    The goal is a 64x64 sprite (single tile) that the hero can interact with.
    Unlike other NPCs, the goal has no conversation - instead it triggers
    a callback when the hero interacts with it.

    Args:
        tile_col: Column of the tile
        tile_row: Row of the tile
    """
    # Calculate pixel position (center of 1-tile base)
    x = tile_col * TILE_SIZE + TILE_SIZE / 2
    y = tile_row * TILE_SIZE + TILE_SIZE / 2

    return NPC(
        x=x,
        y=y,
        sprite_name="goal",
        npc_id="goal",
        is_goal=True,
    )


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
                portrait_sprite="robot_priest_portrait",
                duration=4.0,
            ),
            ConversationPage(
                text=" ".join(
                    [
                        "The prize is a lil' cut scene. We're still working on it,",
                        "it might not have as much context as we'd like right now.",
                    ]
                ),
                speaker="Placeholder Robot Priest",
                portrait_sprite="robot_priest_portrait",
                duration=4.0,
            ),
            ConversationPage(
                text=" ".join(
                    [
                        "We're still in an alpha release, so we'd appreciate it",
                        "if you'd report any bugs you find.",
                    ]
                ),
                speaker="Placeholder Robot Priest",
                portrait_sprite="robot_priest_portrait",
                duration=4.0,
            ),
        ]
    )

    return NPC(
        x=x,
        y=y,
        sprite_name="robot_priest",
        conversation_engine=conversation,
        npc_id="robot_priest",
    )


def has_4x4_walkable_area(dungeon: Dungeon, room_id: int) -> bool:
    """
    Check if a room has at least a 4x4 contiguous area of walkable tiles.

    Args:
        dungeon: The dungeon containing the room
        room_id: The room to check

    Returns:
        True if room has at least a 4x4 walkable area, False otherwise
    """
    from .dungeon_gen import Tile

    if room_id not in dungeon.room_positions:
        return False

    base_col, base_row = dungeon.room_positions[room_id]
    template = dungeon.room_templates[room_id]

    # Check if room is even large enough to contain a 4x4 area
    if template.width < 4 or template.height < 4:
        return False

    # Scan through room looking for a 4x4 walkable area
    for start_row in range(template.height - 3):
        for start_col in range(template.width - 3):
            # Check if all tiles in this 4x4 area are walkable
            all_walkable = True
            for dr in range(4):
                for dc in range(4):
                    map_row = base_row + start_row + dr
                    map_col = base_col + start_col + dc
                    if not (0 <= map_row < dungeon.rows and 0 <= map_col < dungeon.cols):
                        all_walkable = False
                        break
                    if dungeon.map[map_row, map_col] != Tile.FLOOR:
                        all_walkable = False
                        break
                if not all_walkable:
                    break
            if all_walkable:
                return True

    return False


def find_floor_tile_in_room(
    dungeon: Dungeon,
    room_id: int,
) -> Optional[tuple[int, int]]:
    """
    Find a floor tile in the given room suitable for placing an NPC.

    Returns (col, row) in tile coordinates, or None if no suitable tile found.
    Tries to find a tile away from doors for better placement.
    Only considers rooms with at least a 4x4 walkable area.
    """
    from .dungeon_gen import Tile

    # First check if this room has a 4x4 walkable area
    if not has_4x4_walkable_area(dungeon, room_id):
        return None

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
        # Check that both tiles of the 2-wide base are floor tiles
        # We need to check the raw map tiles, not walkability (which includes NPC checks)
        if (
            0 <= row < dungeon.rows
            and 0 <= col + 1 < dungeon.cols
            and dungeon.map[row, col] == Tile.FLOOR
            and dungeon.map[row, col + 1] == Tile.FLOOR
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


def get_gate_npc_position(
    gate_direction: Direction,
    door_position_row: int,
    door_position_col: int,
) -> tuple[int, int]:
    """
    Calculate the tile position for a gate NPC based on the door direction.

    The gate blocks the door from the inside of the goal room.

    Args:
        gate_direction: Direction the door faces (always SOUTH now - the gate
                        blocks the SOUTH door of the south-only goal room)
        door_position_row: Row of the door's first tile
        door_position_col: Column of the door's first tile

    Returns:
        (tile_col, tile_row) for placing the gate NPC
    """
    if gate_direction == Direction.SOUTH:
        # South door: gate goes just above the door (inside goal room, blocking entry from south)
        return (door_position_col, door_position_row)
    else:
        raise ValueError(f"Unsupported gate direction: {gate_direction}")


def create_dungeon_with_priest(num_rooms: int) -> tuple[Dungeon, NPC, Hero]:
    """
    Create a dungeon with a robot priest NPC, a gated goal room, and a hero.

    The dungeon has:
    - A goal always present in a special room with only one door
    - A north_gate NPC blocking the door to the goal room
    - A robot priest who removes the gate when talked to

    Returns:
        Tuple of (dungeon, priest_npc, hero)
    """
    # Generate dungeon with a gated goal room
    dungeon, gate_direction, door_position = create_dungeon_with_gated_goal(num_rooms)

    # Place the north_gate NPC blocking the door
    gate_col, gate_row = get_gate_npc_position(
        gate_direction, door_position.row, door_position.column
    )
    gate = create_north_gate_npc(gate_col, gate_row)
    dungeon.add_npc(gate)

    # Find the goal room (to exclude it from priest placement)
    goal_npc = dungeon.find_goal_npc()
    goal_room_id = dungeon.get_room_id(goal_npc.x, goal_npc.y) if goal_npc else None

    # Find a suitable room for the priest (with at least a 4x4 walkable area)
    priest_pos = None
    for room_id in sorted(dungeon.room_positions.keys(), reverse=True):
        if room_id == goal_room_id:
            continue
        priest_pos = find_floor_tile_in_room(dungeon, room_id)
        if priest_pos is not None:
            break

    if priest_pos is None:
        raise RuntimeError(
            "Could not find suitable position for robot priest. "
            "No room with 4x4 walkable area found."
        )

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

    # Set up callback: when conversation completes, remove the gate
    def on_priest_conversation_complete() -> None:
        dungeon.remove_npc("north_gate")
        strategy.reset_search_state()

    priest.on_conversation_complete = on_priest_conversation_complete

    return dungeon, priest, hero
