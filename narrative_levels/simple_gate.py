"""
Simple Gate Level

A minimal narrative level demonstrating the event-based pattern.

Narrative:
- Hero spawns in a dungeon with a goal behind a gate
- A robot priest blocks the way
- When the hero talks to the priest, the gate opens
- The hero can then reach the goal
"""

from dungeon.setup import create_dungeon_with_priest
from dungeon.world import Dungeon
from dungeon.event_system import EventBus, Event, EventData


# TODO: This isn't complete. Rather than delegate to
# create_dungeon_with_priest(), we'd like to use this level
# as a complete example of a narrative level, setting
# up the NPCs, events and map here where readers
# can use it to understand how to define a level.
def create_level() -> Dungeon:
    """
    Create the simple gate level.

    This level reuses the existing create_dungeon_with_priest() dungeon generator
    but demonstrates the narrative level pattern.
    """
    # For now, we use the existing dungeon generator
    # In the future, this will be replaced with explicit room placement
    dungeon = create_dungeon_with_priest(num_rooms=5)

    return dungeon


# Register this level
from narrative_levels import register_level
register_level("simple_gate", create_level)
