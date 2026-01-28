"""Tests for the event system."""

import pytest
from dungeon.event_system import EventBus, Event, EventData


class TestEventBus:
    """Test EventBus functionality."""

    def test_create_empty_bus(self):
        """Should create an empty event bus."""
        bus = EventBus()
        assert bus.handler_count() == 0

    def test_subscribe_handler(self):
        """Should allow subscribing handlers to events."""
        bus = EventBus()
        called = []

        def handler(event_data: EventData) -> None:
            called.append(event_data.event)

        bus.subscribe(Event.LEVEL_START, handler)
        assert bus.handler_count(Event.LEVEL_START) == 1
        assert bus.handler_count() == 1

    def test_emit_calls_handler(self):
        """Emitting an event should call subscribed handlers."""
        bus = EventBus()
        called = []

        def handler(event_data: EventData) -> None:
            called.append(event_data)

        bus.subscribe(Event.HERO_ENTERS_ROOM, handler)
        bus.emit(Event.HERO_ENTERS_ROOM, room_id=5)

        assert len(called) == 1
        assert called[0].event == Event.HERO_ENTERS_ROOM
        assert called[0].kwargs["room_id"] == 5

    def test_emit_calls_multiple_handlers(self):
        """Should call all handlers subscribed to an event."""
        bus = EventBus()
        called1 = []
        called2 = []

        def handler1(event_data: EventData) -> None:
            called1.append(event_data.event)

        def handler2(event_data: EventData) -> None:
            called2.append(event_data.event)

        bus.subscribe(Event.NPC_INTERACTION, handler1)
        bus.subscribe(Event.NPC_INTERACTION, handler2)
        bus.emit(Event.NPC_INTERACTION, npc_id="test_npc")

        assert len(called1) == 1
        assert len(called2) == 1

    def test_emit_only_calls_matching_event_handlers(self):
        """Should only call handlers subscribed to the emitted event."""
        bus = EventBus()
        called_start = []
        called_end = []

        def handler_start(event_data: EventData) -> None:
            called_start.append(event_data.event)

        def handler_end(event_data: EventData) -> None:
            called_end.append(event_data.event)

        bus.subscribe(Event.LEVEL_START, handler_start)
        bus.subscribe(Event.LEVEL_END, handler_end)
        bus.emit(Event.LEVEL_START)

        assert len(called_start) == 1
        assert len(called_end) == 0

    def test_unsubscribe_handler(self):
        """Should allow unsubscribing handlers."""
        bus = EventBus()
        called = []

        def handler(event_data: EventData) -> None:
            called.append(event_data.event)

        bus.subscribe(Event.CONVERSATION_END, handler)
        bus.emit(Event.CONVERSATION_END, npc_id="test")
        assert len(called) == 1

        bus.unsubscribe(Event.CONVERSATION_END, handler)
        bus.emit(Event.CONVERSATION_END, npc_id="test")
        assert len(called) == 1  # Still 1, not called again

    def test_unsubscribe_nonexistent_handler_raises(self):
        """Unsubscribing a handler that wasn't subscribed should raise ValueError."""
        bus = EventBus()

        def handler(event_data: EventData) -> None:
            pass

        with pytest.raises(ValueError):
            bus.unsubscribe(Event.LEVEL_START, handler)

    def test_clear_removes_all_handlers(self):
        """Clear should remove all event handlers."""
        bus = EventBus()

        def handler1(event_data: EventData) -> None:
            pass

        def handler2(event_data: EventData) -> None:
            pass

        bus.subscribe(Event.LEVEL_START, handler1)
        bus.subscribe(Event.NPC_ADDED, handler2)
        assert bus.handler_count() == 2

        bus.clear()
        assert bus.handler_count() == 0

    def test_handler_error_does_not_crash_bus(self):
        """If a handler raises an error, other handlers should still be called."""
        bus = EventBus()
        called = []

        def bad_handler(event_data: EventData) -> None:
            raise RuntimeError("Handler failed")

        def good_handler(event_data: EventData) -> None:
            called.append(True)

        bus.subscribe(Event.TILE_CHANGED, bad_handler)
        bus.subscribe(Event.TILE_CHANGED, good_handler)

        # Should not raise, good handler should still be called
        bus.emit(Event.TILE_CHANGED, row=5, col=10, tile=None)
        assert len(called) == 1

    def test_event_data_kwargs(self):
        """EventData should correctly store event kwargs."""
        bus = EventBus()
        received = []

        def handler(event_data: EventData) -> None:
            received.append(event_data)

        bus.subscribe(Event.NPC_INTERACTION, handler)
        bus.emit(Event.NPC_INTERACTION, npc_id="priest", room_id=3)

        assert len(received) == 1
        assert received[0].kwargs["npc_id"] == "priest"
        assert received[0].kwargs["room_id"] == 3

    def test_emit_event_with_no_handlers(self):
        """Emitting an event with no handlers should not raise an error."""
        bus = EventBus()
        # Should not raise
        bus.emit(Event.LEVEL_START)

    def test_multiple_subscriptions_to_different_events(self):
        """Should track handlers for different events separately."""
        bus = EventBus()

        def handler(event_data: EventData) -> None:
            pass

        bus.subscribe(Event.LEVEL_START, handler)
        bus.subscribe(Event.LEVEL_END, handler)
        bus.subscribe(Event.NPC_ADDED, handler)

        assert bus.handler_count(Event.LEVEL_START) == 1
        assert bus.handler_count(Event.LEVEL_END) == 1
        assert bus.handler_count(Event.NPC_ADDED) == 1
        assert bus.handler_count() == 3


class TestEventData:
    """Test EventData class."""

    def test_create_event_data(self):
        """Should create EventData with event and kwargs."""
        data = EventData(event=Event.HERO_ENTERS_ROOM, kwargs={"room_id": 5})
        assert data.event == Event.HERO_ENTERS_ROOM
        assert data.kwargs["room_id"] == 5

    def test_event_data_repr_with_kwargs(self):
        """EventData repr should include kwargs."""
        data = EventData(event=Event.NPC_INTERACTION, kwargs={"npc_id": "priest"})
        repr_str = repr(data)
        assert "NPC_INTERACTION" in repr_str
        assert "npc_id=priest" in repr_str

    def test_event_data_repr_without_kwargs(self):
        """EventData repr should work without kwargs."""
        data = EventData(event=Event.LEVEL_START)
        repr_str = repr(data)
        assert "LEVEL_START" in repr_str
