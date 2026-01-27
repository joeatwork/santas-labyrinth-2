# Narrative Dungeon Levels Design Document

# Objective

Our VideoProgram should include "narrative" dungeon levels alongside the randomly
generated levels currently produced by dungeon_gen.py. These narrative levels
will be dungeons that are laid out to accommodate a series of narrative events
and challenges and move in a satisfying way from beginning to end,
with a hero using a strategy with goals that make sense for the narrative of the level.

This design should include:
* How a narrative level will be specified, stored on disk and loaded as code
* What changes to the current system will be required to accommodate narrative levels
* A step-by-step implementation plan including incremental milestones

In the future, we expect narrative levels to be designed by automatic systems, but
as an incremental improvement to the system as it is, our initial narrative levels
will be designed by a human.

# High Level Design

A narrative level is a Python module that produces a dungeon using a similar interface to dungeon_gen.py, creating an explicit dungeon shape, constructing a dungeon, and placing NPCs in that dungeon. This construction results in the initial state of the dungeon. In addition to the initial state, narrative levels also have a state machine which can change the state of the dungeon. This state machine observes events in the dungeon and changes the state of the dungeon based on those events.

## Events

We currently have an ad-hoc mechanism for changing the dungeon as a result of a hero's interaction with an NPC. We now formalize that mechanism as an *event* system.

Each level will have a state machine associated with it that can
transition based on hero and NPC actions. When Heroes and NPCs move
and interact, they can fire events. In response to those events, the
level state can show a movie (like the goal movies), add, remove, or move NPCs, change the strategy of the hero, or change the dungeon tiles and background.

The narrative of a level can be explained in terms of events and states, along with
the dungeon background tiles and NPC placements. Here is an example narrative, in English:

* The hero spawns in the spawning spot
* The hero walks into the first dungeon room
   * when the hero steps into the first room, the
     gate in the first door closes.
   * When the hero steps into the first room, the
     hero changes strategy to "Search for NPCs and talk to them once"
* The hero interacts with the small screen TV NPC
   * When the hero interacts with the small screen TV NPC,
     play a video in "design_for_dreaming.mp4" at time offset
     30 seconds for one minute
   * When the hero interacts with the small screen TV NPC,
     set the event flag "Hero Saw The Movie"
   * When the hero interacts with the small screen TV NPC,
     update the hero's strategy to forget whether the
     hero has spoken to the door guardian NPC
* The hero interacts with the door guardian NPC
   * When the hero interacts with the door guardian NPC,
     If the event flag "Hero Saw The Movie" is set,
     open the exit gate
   * When the hero interacts with the door guardian NPC,
     If the event flag "Hero Saw The Movie" is set,
     show a conversation congratulating the hero
   * When the hero interacts with the door guardian NPC,
     If the event flag "Hero Saw The Movie" is NOT set,
     show a conversation telling the hero that it should
     find a movie to watch.
* The exit gate opens
   * When the exit gate opens, the hero changes strategy to "Search for the Exit Gate"
* The hero walks through the exit gate
   * When the hero walks through the exit gate
     play the video "buck_rogers.mp4" at time offset 15 minutes for 20 seconds,
     then end the level.

## Design Considerations

The initial narrative levels will be designed by humans and by LLM AIs, so they
should be easy to edit, read and understand.

A narrative level should be able to be run through a standard test and validation
suite before it is run as part of a VideoProgram in a DungeonWalk.

A major goal for future work is to allow narrative levels to be produced
automatically by a collection of rules-based code, ML model output, and simple
LLMs. The design of narrative levels should accommodate this.

---

# Current System Architecture

Understanding the current system is essential for designing narrative levels that integrate cleanly.

## Dungeon Generation ([dungeon/dungeon_gen.py](dungeon/dungeon_gen.py))

The current system generates dungeons by organic room growth:

1. Start with an initial room template placed at a canvas center
2. Maintain a queue of "open doors" that don't have rooms attached
3. Iteratively pick open doors and attach compatible room templates
4. Replace unconnected doors with walls
5. Crop to bounding box

Key data structures:
- `DungeonMap`: 2D numpy array of `MetalTile` enum values
- `Position`: Frozen dataclass with `row` and `column` (tile coordinates)
- `Direction`: Enum for NORTH, SOUTH, EAST, WEST with `opposite()` and `step()` methods
- `RoomTemplate` / `MetalRoomTemplate`: Room definitions with ASCII art and door properties

The `generate_dungeon()` function returns:
```python
(dungeon_map, start_pos_pixel, room_positions, room_assignments, goal_room_id)
```

## World Representation ([dungeon/world.py](dungeon/world.py))

### Dungeon Class

The `Dungeon` class holds the world state:
- `map`: 2D tile array
- `npcs`: List of NPCs in the dungeon
- `hero`: The player character
- `room_positions`: Dict mapping room_id to (tile_x, tile_y) top-left corner
- `room_templates`: Dict mapping room_id to RoomTemplate

Key methods for narrative levels:
- `place_goal(room_id)`: Places goal NPC in a room (line 99)
- `remove_goal()`: Removes goal NPC (line 137)
- `add_npc(npc)`: Adds an NPC and sets its room_id (line 186)
- `find_doors_in_room(room_id)`: Returns door tiles as [(row, col)] (line 150)
- `is_tile_walkable(row, col)`: Checks walkability including NPC occupation (line 51)

### Hero Class

The `Hero` class (line 244) manages position, movement, and animation:
- States: "idle", "walking", "talking"
- Navigation delegated to a `Strategy` object
- `update(dt, dungeon)` returns `InteractCommand` when hero wants to talk to NPC

## Strategy System ([dungeon/strategy.py](dungeon/strategy.py))

Strategies decide where the hero moves. The abstract `Strategy` class defines:

```python
def decide_next_move(self, x, y, dungeon) -> StrategyCommand
```

Returns `MoveCommand`, `InteractCommand`, or `None`.

The current `GoalSeekingStrategy` (line 78):
- Tracks doors traversed in `lru_doors` (OrderedDict)
- Tracks NPCs talked to in `npcs_met` (Set)
- Uses BFS pathfinding to navigate
- `reset_search_state()` clears navigation memory (line 116) - **critical for narrative state changes**

## NPC System ([dungeon/npc.py](dungeon/npc.py))

NPCs are dataclasses with:
- Position (`x`, `y` in pixels)
- `sprite_name` for rendering
- `conversation_engine`: Optional conversation handler
- `on_interact`: Callback when hero interacts
- `on_conversation_complete`: Callback when conversation ends
- `is_goal`: Special flag for goal NPCs
- `room_id`: Set by Dungeon when added

## Content System ([content.py](content.py))

### Content Base Class

All content inherits from `Content` (line 32):
- `enter()`: Called when content becomes active
- `update(dt)`: Update logic each frame
- `render(width, height)`: Returns frame as numpy array
- `get_audio(...)`: Returns audio samples
- `is_complete()`: Signals completion

### DungeonWalk

`DungeonWalk` (line 332) manages dungeon gameplay:
- Takes a `dungeon_generator` callable that returns a `Dungeon`
- Handles hero movement, NPC interactions, conversations
- Manages crash detection (hero idle 3+ seconds)
- Plays `goal_movie` when hero reaches goal
- `is_complete()` returns True when goal reached and movie finished

Key interaction flow (lines 441-473):
1. `hero.update()` returns `InteractCommand` when hero talks to NPC
2. If goal NPC: set `hit_goal = True`, call `on_interact`
3. If regular NPC: create `ConversationOverlay`, call `on_interact`
4. When conversation ends: call `on_conversation_complete` callback

### VideoProgram

`VideoProgram` (line 753) is a looping playlist of Content with durations.

## Existing State Change Pattern ([dungeon/setup.py](dungeon/setup.py))

The `create_dungeon_with_priest()` function (line 231) demonstrates the current pattern for dynamic dungeons:

```python
# 1. Generate dungeon without goal
dungeon = create_random_dungeon(num_rooms, place_goal=False)

# 2. Place NPC with conversation
priest = create_robot_priest(col, row)
dungeon.add_npc(priest)

# 3. Capture dungeon/strategy in closure for callback
def on_priest_conversation_complete():
    dungeon.place_goal(chosen_room)
    strategy.reset_search_state()

priest.on_conversation_complete = on_priest_conversation_complete
```

This pattern enables sequential narrative beats through NPC callbacks.

---

# Narrative Level Specification

## File Format

A narrative level is a Python module in `narrative_levels/` that exports a `create_level()` function:

```python
# narrative_levels/example_level.py

from dungeon.narrative import NarrativeLevel, Event, State, Trigger
from dungeon.world import Dungeon
from dungeon.npc import NPC

def create_level() -> NarrativeLevel:
    """Create and return the narrative level definition."""
    level = NarrativeLevel(
        name="example_level",
        dungeon_layout=DUNGEON_ASCII,
        initial_state="start",
    )

    # Define dungeon layout
    level.add_room("entrance", ENTRANCE_ROOM_ASCII, position=(0, 0))
    level.add_room("main_hall", MAIN_HALL_ASCII, position=(0, 10))
    level.connect_rooms("entrance", "main_hall", door_direction="south")

    # Define NPCs
    level.add_npc(
        npc_id="tv_npc",
        room="main_hall",
        sprite_name="small_tv",
        conversation=TV_CONVERSATION,
    )

    # Define state machine
    level.add_state("start")
    level.add_state("watched_movie")
    level.add_state("gate_open")
    level.add_state("complete")

    # Define triggers
    level.add_trigger(
        event=Event.NPC_INTERACTION,
        npc_id="tv_npc",
        from_state="start",
        actions=[
            Action.PLAY_VIDEO("design_for_dreaming.mp4", start=30, duration=60),
            Action.SET_FLAG("saw_movie"),
            Action.TRANSITION_TO("watched_movie"),
        ],
    )

    return level
```

## NarrativeLevel Class

A new `NarrativeLevel` class encapsulates:

1. **Dungeon Layout**: Explicit room placement and connections (not random generation)
2. **NPC Definitions**: Initial NPC placements with conversations and sprites
3. **State Machine**: States, transitions, and triggers
4. **Event Flags**: Boolean flags that persist across state changes
5. **Hero Strategy**: Initial and per-state hero navigation strategies

## Event Types

Events that can trigger state transitions:

| Event | Description | Parameters |
|-------|-------------|------------|
| `LEVEL_START` | Level begins | - |
| `HERO_ENTERS_ROOM` | Hero crosses into a room | `room_id` |
| `HERO_EXITS_ROOM` | Hero leaves a room | `room_id` |
| `NPC_INTERACTION` | Hero talks to NPC | `npc_id` |
| `CONVERSATION_END` | Conversation finishes | `npc_id` |
| `VIDEO_END` | Video clip finishes | `video_id` |
| `HERO_REACHES_TILE` | Hero steps on specific tile | `row`, `col` |
| `FLAG_SET` | A flag becomes true | `flag_name` |

## Action Types

Actions that can be performed in response to events:

| Action | Description |
|--------|-------------|
| `SET_FLAG(name)` | Set a boolean flag to true |
| `CLEAR_FLAG(name)` | Set a boolean flag to false |
| `PLAY_VIDEO(path, start, duration)` | Play a video clip |
| `SHOW_CONVERSATION(pages)` | Display conversation overlay |
| `ADD_NPC(npc_def)` | Spawn an NPC |
| `REMOVE_NPC(npc_id)` | Remove an NPC |
| `MOVE_NPC(npc_id, room, tile)` | Teleport an NPC |
| `PLACE_GOAL(room_id)` | Place the goal crystal |
| `REMOVE_GOAL()` | Remove the goal |
| `SET_TILE(row, col, tile)` | Change a dungeon tile |
| `SET_HERO_STRATEGY(strategy)` | Change hero navigation |
| `RESET_HERO_MEMORY()` | Clear hero's visited doors/NPCs |
| `TRANSITION_TO(state)` | Change state machine state |
| `END_LEVEL()` | Signal level completion |

## Condition Guards

Triggers can have condition guards that must be true:

```python
level.add_trigger(
    event=Event.NPC_INTERACTION,
    npc_id="door_guardian",
    from_state="watched_movie",
    conditions=[
        Condition.FLAG_SET("saw_movie"),
    ],
    actions=[
        Action.SHOW_CONVERSATION(CONGRATULATIONS),
        Action.TRANSITION_TO("gate_open"),
    ],
)

# Alternative path when condition not met
level.add_trigger(
    event=Event.NPC_INTERACTION,
    npc_id="door_guardian",
    from_state="watched_movie",
    conditions=[
        Condition.FLAG_NOT_SET("saw_movie"),
    ],
    actions=[
        Action.SHOW_CONVERSATION(GO_WATCH_MOVIE),
    ],
)
```

## Dungeon Layout Specification

Narrative levels define explicit room layouts rather than random generation:

```python
ENTRANCE_ROOM = """
1---`nN~---2
[,,,,..,,,,]
[..........]
[..........]
[..........]
3__________4
"""

MAIN_HALL = """
1----------2
[,,,,,,,,,,]
[..........]
w..........e
W..........E
[..........]
[..........]
3____sS____4
"""
```

Rooms are placed at explicit positions and connected via door alignment:

```python
level.add_room("entrance", ENTRANCE_ROOM, position=(0, 0))
level.add_room("main_hall", MAIN_HALL, position=(0, 6))  # Below entrance
level.connect_rooms("entrance", "main_hall", "south", "north")
```

The `connect_rooms()` method aligns the specified doors and validates the connection.

---

# System Changes Required

## New Modules

### `dungeon/narrative.py`

New module containing:
- `NarrativeLevel` class
- `Event` enum
- `Action` classes
- `Condition` classes
- `Trigger` dataclass
- `NarrativeDungeonBuilder` - constructs Dungeon from level definition

### `dungeon/event_system.py`

Event dispatch system:
- `EventBus` class for publishing/subscribing to events
- `LevelEventHandler` that connects events to NarrativeLevel state machine

### `narrative_levels/`

New directory for narrative level modules:
- `__init__.py` with level registry
- Individual level files (e.g., `tutorial.py`, `tv_quest.py`)

## Changes to Existing Code

### `dungeon/world.py`

Add event hooks to `Dungeon` class:

```python
class Dungeon:
    def __init__(self, ...):
        ...
        self.event_bus: Optional[EventBus] = None

    def set_event_bus(self, bus: EventBus) -> None:
        self.event_bus = bus

    def _emit(self, event: Event, **kwargs) -> None:
        if self.event_bus:
            self.event_bus.emit(event, **kwargs)
```

Add tile modification method:

```python
def set_tile(self, row: int, col: int, tile: MetalTile) -> None:
    """Change a tile and regenerate affected background."""
    self.map[row, col] = tile
    self._emit(Event.TILE_CHANGED, row=row, col=col, tile=tile)
```

### `dungeon/strategy.py`

Add new strategies for narrative control:

```python
class NPCSeekingStrategy(Strategy):
    """Navigate to talk to specific NPCs, then idle."""

    def __init__(self, target_npc_ids: List[str]):
        self.target_npc_ids = target_npc_ids
        self.talked_to: Set[str] = set()

class RoomTargetStrategy(Strategy):
    """Navigate to a specific room."""

    def __init__(self, target_room_id: int):
        self.target_room_id = target_room_id

class TileTargetStrategy(Strategy):
    """Navigate to a specific tile."""

    def __init__(self, target_row: int, target_col: int):
        self.target_row = target_row
        self.target_col = target_col
```

### `content.py`

Modify `DungeonWalk` to support narrative levels:

```python
class DungeonWalk(Content):
    def __init__(
        self,
        dungeon_generator: DungeonGenerator,
        assets: AssetManager,
        goal_movie: Optional[Content] = None,
        ambient_audio: Optional[AudioClip] = None,
        mix_distance: float = 1024.0,
        narrative_level: Optional[NarrativeLevel] = None,  # NEW
    ):
        ...
        self.narrative_level = narrative_level
        self.event_handler: Optional[LevelEventHandler] = None
        self.pending_video: Optional[Content] = None  # Video triggered by event
```

Add event emission in update loop:

```python
def update(self, dt: float) -> None:
    ...
    # Track room changes for events
    if self.hero and self.event_handler:
        new_room = self.dungeon.get_room_id(self.hero.x, self.hero.y)
        if new_room != self._last_room:
            if self._last_room is not None:
                self.event_handler.emit(Event.HERO_EXITS_ROOM, room_id=self._last_room)
            self.event_handler.emit(Event.HERO_ENTERS_ROOM, room_id=new_room)
            self._last_room = new_room
```

### `stream_animation.py`

Add support for loading narrative levels:

```python
from narrative_levels import get_level

# Option to use narrative level instead of random
if args.narrative_level:
    level = get_level(args.narrative_level)
    dungeon_walk = DungeonWalk(
        level.create_dungeon,
        assets,
        narrative_level=level,
    )
else:
    dungeon_walk = DungeonWalk(make_dungeon_with_priest, assets, ...)
```

---

# Implementation Plan

## Phase 1: Event System Foundation

**Goal**: Create the event infrastructure without changing existing behavior.

### Milestone 1.1: Event Bus
- Create `dungeon/event_system.py`
- Implement `Event` enum with all event types
- Implement `EventBus` class with `emit()` and `subscribe()` methods
- Add unit tests for event dispatch

### Milestone 1.2: Event Hooks in Dungeon
- Add optional `event_bus` to `Dungeon` class
- Add `_emit()` helper method
- Emit events for: NPC added, NPC removed, goal placed, tile changed
- Verify existing tests still pass (no behavior change when event_bus is None)

### Milestone 1.3: Event Hooks in DungeonWalk
- Track hero room transitions, emit `HERO_ENTERS_ROOM` / `HERO_EXITS_ROOM`
- Emit `NPC_INTERACTION` when hero talks to NPC
- Emit `CONVERSATION_END` when conversation finishes
- Emit `LEVEL_START` in `enter()`

## Phase 2: Narrative Level Definition

**Goal**: Create the data structures for defining narrative levels.

### Milestone 2.1: NarrativeLevel Class
- Create `dungeon/narrative.py`
- Implement `NarrativeLevel` dataclass with:
  - `name`, `initial_state`
  - Room definitions list
  - NPC definitions list
  - State machine (states, triggers)
  - Event flags dict

### Milestone 2.2: Action and Condition Classes
- Implement `Action` base class and subclasses for each action type
- Implement `Condition` base class and subclasses
- Implement `Trigger` dataclass linking events to actions with conditions

### Milestone 2.3: State Machine
- Implement state machine logic in `NarrativeLevel`
- `process_event(event, **kwargs)` method that:
  - Finds matching triggers for current state
  - Evaluates condition guards
  - Executes actions
  - Transitions state if specified

## Phase 3: Dungeon Building from Narrative

**Goal**: Generate a Dungeon from a NarrativeLevel definition.

### Milestone 3.1: Room Placement
- Implement `NarrativeDungeonBuilder` class
- Parse room ASCII art using existing `parse_metal_ascii_room()`
- Place rooms at specified positions on a canvas
- Apply `ROOM_REPAIR_PATTERNS` for tile cleanup

### Milestone 3.2: Room Connection
- Implement `connect_rooms()` to align doors between rooms
- Validate door compatibility (north connects to south, etc.)
- Handle door tile placement at connection points

### Milestone 3.3: NPC Placement
- Place NPCs in specified rooms at specified tiles
- Wire up `on_interact` and `on_conversation_complete` to event system
- Create `create_dungeon()` method that returns fully configured `Dungeon`

## Phase 4: Action Execution

**Goal**: Implement all action types.

### Milestone 4.1: Simple Actions
- `SET_FLAG`, `CLEAR_FLAG` - modify level flags dict
- `TRANSITION_TO` - change state machine state
- `END_LEVEL` - set completion flag

### Milestone 4.2: NPC Actions
- `ADD_NPC` - create and add NPC to dungeon
- `REMOVE_NPC` - remove NPC from dungeon
- `MOVE_NPC` - update NPC position and room_id
- `PLACE_GOAL`, `REMOVE_GOAL` - delegate to Dungeon methods

### Milestone 4.3: Hero Actions
- `SET_HERO_STRATEGY` - swap hero's strategy object
- `RESET_HERO_MEMORY` - call `strategy.reset_search_state()`
- Implement new strategy classes as needed

### Milestone 4.4: Video Actions
- `PLAY_VIDEO` - create VideoClip, set as pending overlay in DungeonWalk
- Handle video completion event
- `SHOW_CONVERSATION` - create ConversationOverlay with specified pages

### Milestone 4.5: Tile Actions
- `SET_TILE` - modify dungeon map
- Regenerate background/foreground images for affected area
- Handle walkability changes (may trap hero - add validation)

## Phase 5: Integration

**Goal**: Wire narrative levels into the streaming pipeline.

### Milestone 5.1: LevelEventHandler
- Create `LevelEventHandler` class that:
  - Subscribes to EventBus
  - Routes events to NarrativeLevel.process_event()
  - Applies actions to Dungeon/Hero/DungeonWalk

### Milestone 5.2: DungeonWalk Integration
- Add `narrative_level` parameter to DungeonWalk
- Create EventBus and LevelEventHandler in `enter()`
- Handle `pending_video` overlay in update/render
- Handle `END_LEVEL` action by setting `is_complete()` True

### Milestone 5.3: Level Registry
- Create `narrative_levels/__init__.py` with `get_level(name)` function
- Add command-line argument `--narrative-level` to stream_animation.py
- Document level loading in CLAUDE.md

## Phase 6: Testing and Validation

**Goal**: Ensure narrative levels work correctly.

### Milestone 6.1: Unit Tests
- Test event dispatch
- Test state machine transitions
- Test condition evaluation
- Test action execution
- Test dungeon building from ASCII

### Milestone 6.2: Level Validation
- Create `validate_level(level)` function that checks:
  - All rooms connected (no orphan rooms)
  - All referenced NPCs defined
  - All referenced rooms exist
  - State machine is well-formed (no orphan states)
  - Hero can reach all trigger locations

### Milestone 6.3: Example Narrative Level
- Create `narrative_levels/tutorial.py` implementing the example from this document
- Test full playthrough
- Verify video playback, conversations, state transitions

## Phase 7: Documentation and Polish

### Milestone 7.1: Documentation
- Update CLAUDE.md with narrative level architecture
- Add docstrings to all new classes
- Create example level template

### Milestone 7.2: Developer Tools
- Add `--validate-level` CLI option to check level without running
- Add ASCII visualization of narrative level layout
- Consider hot-reload for level development

---

# Future Considerations

## Automatic Level Generation

The design supports future automatic generation by:
- Separating level definition (data) from execution (code)
- Using simple, composable primitives (events, actions, conditions)
- Keeping state machine logic declarative

An LLM could generate a narrative level by:
1. Generating room layouts as ASCII art
2. Defining NPC placements and conversations
3. Specifying the state machine as a list of triggers

## Level Complexity

For complex levels, consider:
- Hierarchical state machines (sub-states)
- Parallel state regions
- Timed triggers (events after N seconds)
- Randomized elements within narrative structure

## Asset Requirements

Narrative levels may require:
- New NPC sprites (TV, door guardian, etc.)
- New tile types (gates that open/close)
- Per-level ambient audio
- Per-level video clips

---

# Appendix: Example Narrative Level

```python
# narrative_levels/tv_quest.py

from dungeon.narrative import (
    NarrativeLevel, Event, Action, Condition, ConversationPage
)

# Room layouts
SPAWN_ROOM = """
1----2
[,,,,]
[....]
[....]
[....]
3_sS_4
"""

MAIN_ROOM = """
1`nN~-------2
[,,..,,,,,,]
[..........]
w..........e
W..........E
[..........]
3____sS____4
"""

EXIT_ROOM = """
1`nN~2
[,,..]
[....]
[....]
3____4
"""

# Conversations
GUARDIAN_NO_MOVIE = [
    ConversationPage(
        text="You haven't watched the movie yet! Find the TV and watch it.",
        speaker="Door Guardian",
        duration=4.0,
    ),
]

GUARDIAN_YES_MOVIE = [
    ConversationPage(
        text="Excellent! You've watched the movie. The exit is now open!",
        speaker="Door Guardian",
        duration=4.0,
    ),
]

def create_level() -> NarrativeLevel:
    level = NarrativeLevel(name="tv_quest", initial_state="exploring")

    # Layout
    level.add_room("spawn", SPAWN_ROOM, position=(0, 0))
    level.add_room("main", MAIN_ROOM, position=(0, 5))
    level.add_room("exit", EXIT_ROOM, position=(12, 5))
    level.connect_rooms("spawn", "main", "south", "north")
    level.connect_rooms("main", "exit", "east", "west")

    level.set_spawn_room("spawn")

    # NPCs
    level.add_npc("tv", room="main", tile=(3, 5), sprite="small_tv")
    level.add_npc("guardian", room="main", tile=(9, 5), sprite="robot_priest")

    # States
    level.add_state("exploring")
    level.add_state("watched_movie")
    level.add_state("gate_open")

    # Triggers
    level.add_trigger(
        event=Event.NPC_INTERACTION,
        npc_id="tv",
        from_state="exploring",
        actions=[
            Action.PLAY_VIDEO("large_media/design_for_dreaming.mp4", start=30, duration=60),
            Action.SET_FLAG("saw_movie"),
            Action.RESET_HERO_MEMORY(),
            Action.TRANSITION_TO("watched_movie"),
        ],
    )

    level.add_trigger(
        event=Event.NPC_INTERACTION,
        npc_id="guardian",
        from_state="exploring",
        conditions=[Condition.FLAG_NOT_SET("saw_movie")],
        actions=[
            Action.SHOW_CONVERSATION(GUARDIAN_NO_MOVIE),
        ],
    )

    level.add_trigger(
        event=Event.NPC_INTERACTION,
        npc_id="guardian",
        from_state="watched_movie",
        conditions=[Condition.FLAG_SET("saw_movie")],
        actions=[
            Action.SHOW_CONVERSATION(GUARDIAN_YES_MOVIE),
            Action.PLACE_GOAL("exit"),
            Action.RESET_HERO_MEMORY(),
            Action.TRANSITION_TO("gate_open"),
        ],
    )

    level.add_trigger(
        event=Event.NPC_INTERACTION,
        npc_id="goal",  # The goal crystal placed in exit room
        from_state="gate_open",
        actions=[
            Action.PLAY_VIDEO("large_media/buck_rogers.mp4", start=900, duration=20),
            Action.END_LEVEL(),
        ],
    )

    return level
```
