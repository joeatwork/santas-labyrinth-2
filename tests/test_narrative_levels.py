"""Tests for narrative level loading."""

import pytest
from narrative_levels import register_level, get_level, list_levels
from dungeon.world import Dungeon


def test_level_registry():
    """Should be able to register and retrieve levels."""
    # Clean registry for test isolation
    from narrative_levels import _LEVELS
    original_levels = _LEVELS.copy()
    _LEVELS.clear()

    try:
        # Register a test level
        def test_level():
            from dungeon.setup import create_dungeon_with_priest
            return create_dungeon_with_priest(3)

        register_level("test", test_level)

        # Should be able to retrieve it
        factory = get_level("test")
        assert factory is test_level

        # Should appear in level list
        assert "test" in list_levels()

    finally:
        # Restore original registry
        _LEVELS.clear()
        _LEVELS.update(original_levels)


def test_get_unknown_level_raises():
    """Getting an unknown level should raise ValueError."""
    with pytest.raises(ValueError, match="Unknown level"):
        get_level("nonexistent_level_name")


def test_simple_gate_level():
    """simple_gate level should create a valid dungeon."""
    # Import to register the level
    import narrative_levels.simple_gate

    factory = get_level("simple_gate")
    dungeon = factory()

    # Should create a valid dungeon
    assert isinstance(dungeon, Dungeon)
    assert dungeon.hero is not None

    # Should have the priest, gate, and goal NPCs
    assert len(dungeon.npcs) == 3

    npc_ids = {npc.npc_id for npc in dungeon.npcs}
    assert "robot_priest" in npc_ids
    assert "north_gate" in npc_ids
    assert "goal" in npc_ids


def test_simple_gate_level_is_registered():
    """simple_gate should be in the registry."""
    import narrative_levels.simple_gate

    assert "simple_gate" in list_levels()
