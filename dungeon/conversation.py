"""
Conversation data models for NPC interactions.

Conversations are driven by a ConversationEngine that generates pages on the fly,
allowing for dynamic, turn-based dialogue (e.g., via LLM or scripted sequences).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ConversationPage:
    """A single page of conversation text with optional portrait."""

    text: str
    speaker: str  # "npc" or "hero"
    portrait_sprite: Optional[str] = None  # Sprite name for AssetManager
    duration: float = 4.0  # Seconds to display this page


class ConversationEngine(ABC):
    """
    Abstract base for conversation generators.

    Subclasses can implement scripted, random, or LLM-driven conversations.
    The engine generates pages on the fly, allowing responses to depend on
    previous messages.
    """

    @abstractmethod
    def start(self) -> ConversationPage:
        """Return the first page of conversation."""
        pass

    @abstractmethod
    def respond(self, previous_page: ConversationPage) -> Optional[ConversationPage]:
        """
        Generate next page based on conversation state.

        Args:
            previous_page: The page that was just displayed

        Returns:
            The next page to display, or None if the conversation is complete.
        """
        pass


class ScriptedConversation(ConversationEngine):
    """
    Simple scripted conversation from a list of pages.

    Pages are displayed in order, with no dynamic generation.
    """

    def __init__(self, pages: List[ConversationPage]):
        if not pages:
            raise ValueError("ScriptedConversation must have at least one page")
        self.pages = pages
        self.index = 0

    def start(self) -> ConversationPage:
        self.index = 0
        return self.pages[0]

    def respond(self, previous_page: ConversationPage) -> Optional[ConversationPage]:
        self.index += 1
        if self.index < len(self.pages):
            return self.pages[self.index]
        return None
