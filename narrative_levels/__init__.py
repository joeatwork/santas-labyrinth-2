"""Narrative level registry."""

from typing import Callable
from dungeon.world import Dungeon

# Type for level factory functions
LevelFactory = Callable[[], Dungeon]

# Registry of available levels
_LEVELS: dict[str, LevelFactory] = {}


def register_level(name: str, factory: LevelFactory) -> None:
    """Register a level factory function."""
    _LEVELS[name] = factory


def get_level(name: str) -> LevelFactory:
    """Get a level factory by name."""
    if name not in _LEVELS:
        raise ValueError(f"Unknown level: {name}")
    return _LEVELS[name]


def list_levels() -> list[str]:
    """List all registered level names."""
    return sorted(_LEVELS.keys())
