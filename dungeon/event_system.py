"""
Event system for dungeon narratives.

This module provides an event bus for dungeon events and narrative state management.
Events can be emitted by the dungeon, hero, NPCs, and content systems, and handlers
can subscribe to respond to these events.
"""

from enum import Enum, auto
from typing import Callable, Any, Dict, List, Optional
from dataclasses import dataclass, field


class Event(Enum):
    """Event types that can occur during dungeon gameplay."""

    # Level lifecycle
    LEVEL_START = auto()
    LEVEL_END = auto()

    # Hero movement events
    HERO_ENTERS_ROOM = auto()  # kwargs: room_id
    HERO_EXITS_ROOM = auto()  # kwargs: room_id
    HERO_REACHES_TILE = auto()  # kwargs: row, col

    # NPC interaction events
    NPC_INTERACTION = auto()  # kwargs: npc_id
    CONVERSATION_START = auto()  # kwargs: npc_id
    CONVERSATION_END = auto()  # kwargs: npc_id

    # Dungeon state events
    NPC_ADDED = auto()  # kwargs: npc_id
    NPC_REMOVED = auto()  # kwargs: npc_id
    GOAL_PLACED = auto()  # kwargs: room_id
    GOAL_REMOVED = auto()
    TILE_CHANGED = auto()  # kwargs: row, col, tile

    # Media events
    VIDEO_START = auto()  # kwargs: video_id
    VIDEO_END = auto()  # kwargs: video_id

    # Custom events
    FLAG_SET = auto()  # kwargs: flag_name
    FLAG_CLEARED = auto()  # kwargs: flag_name


@dataclass
class EventData:
    """Container for event data passed to handlers."""

    event: Event
    kwargs: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        if self.kwargs:
            kwargs_str = ", ".join(f"{k}={v}" for k, v in self.kwargs.items())
            return f"EventData({self.event.name}, {kwargs_str})"
        return f"EventData({self.event.name})"


# Event handler signature: takes event data, returns nothing
EventHandler = Callable[[EventData], None]


class EventBus:
    """
    Event bus for publishing and subscribing to dungeon events.

    The event bus allows decoupled communication between dungeon components.
    Subscribers can register handlers for specific event types, and publishers
    can emit events that trigger those handlers.
    """

    def __init__(self) -> None:
        """Initialize an empty event bus."""
        self._handlers: Dict[Event, List[EventHandler]] = {}
        self._debug: bool = False

    def set_debug(self, debug: bool) -> None:
        """Enable or disable debug logging of events."""
        self._debug = debug

    def subscribe(self, event: Event, handler: EventHandler) -> None:
        """
        Subscribe a handler to an event type.

        Args:
            event: The event type to listen for
            handler: Callable that takes EventData and returns None
        """
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def unsubscribe(self, event: Event, handler: EventHandler) -> None:
        """
        Unsubscribe a handler from an event type.

        Args:
            event: The event type
            handler: The handler to remove

        Raises:
            ValueError: If handler was not subscribed to this event
        """
        if event not in self._handlers:
            raise ValueError(f"No handlers registered for event {event}")
        if handler not in self._handlers[event]:
            raise ValueError(f"Handler not subscribed to event {event}")
        self._handlers[event].remove(handler)

    def emit(self, event: Event, **kwargs: Any) -> None:
        """
        Emit an event, triggering all subscribed handlers.

        Args:
            event: The event type to emit
            **kwargs: Event-specific data passed to handlers
        """
        event_data = EventData(event=event, kwargs=kwargs)

        if self._debug:
            print(f"[EventBus] Emitting: {event_data}")

        if event in self._handlers:
            for handler in self._handlers[event]:
                try:
                    handler(event_data)
                except Exception as e:
                    # Log but don't crash - one handler failing shouldn't stop others
                    print(f"[EventBus] Handler error for {event.name}: {e}")
                    if self._debug:
                        raise

    def clear(self) -> None:
        """Remove all event handlers."""
        self._handlers.clear()

    def handler_count(self, event: Optional[Event] = None) -> int:
        """
        Get the number of handlers registered.

        Args:
            event: If provided, count handlers for this event only.
                   If None, count total handlers across all events.

        Returns:
            Number of handlers
        """
        if event is not None:
            return len(self._handlers.get(event, []))
        return sum(len(handlers) for handlers in self._handlers.values())
