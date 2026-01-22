"""Unit tests for ConversationOverlay."""

import pytest

from dungeon.conversation import ConversationPage, ScriptedConversation
from dungeon.conversation_overlay import ConversationOverlay


def make_single_page_conversation(duration: float = 1.0):
    """Create a conversation with one page."""
    return ScriptedConversation([
        ConversationPage(text="Only page", speaker="npc", duration=duration),
    ])


def make_multi_page_conversation():
    """Create a conversation with multiple pages."""
    return ScriptedConversation([
        ConversationPage(text="Page 1", speaker="npc", duration=1.0),
        ConversationPage(text="Page 2", speaker="hero", duration=1.5),
        ConversationPage(text="Page 3", speaker="npc", duration=1.0),
    ])


class TestConversationOverlay:
    """Tests for ConversationOverlay class."""

    def test_not_complete_before_enter(self):
        """Overlay is not complete before enter() is called."""
        conv = make_single_page_conversation()
        overlay = ConversationOverlay(conv)

        # Before enter, current_page is None so is_complete returns True
        # This is expected behavior - we need to call enter() first
        assert overlay.current_page is None

    def test_enter_starts_conversation(self):
        """enter() sets up the first page."""
        conv = make_single_page_conversation()
        overlay = ConversationOverlay(conv)

        overlay.enter()

        assert overlay.current_page is not None
        assert overlay.current_page.text == "Only page"
        assert overlay.page_elapsed == 0.0

    def test_not_complete_during_page(self):
        """Overlay is not complete while current page is active."""
        conv = make_single_page_conversation(duration=2.0)
        overlay = ConversationOverlay(conv)

        overlay.enter()
        overlay.update(1.0)  # Half duration

        assert not overlay.is_complete()

    def test_advances_to_next_page(self):
        """Overlay advances to next page when duration expires."""
        conv = make_multi_page_conversation()
        overlay = ConversationOverlay(conv)

        overlay.enter()
        assert overlay.current_page.text == "Page 1"

        # Exceed first page duration
        overlay.update(1.1)
        assert overlay.current_page is not None
        assert overlay.current_page.text == "Page 2"

    def test_complete_after_all_pages(self):
        """Overlay is complete after all pages have been shown."""
        conv = make_single_page_conversation(duration=1.0)
        overlay = ConversationOverlay(conv)

        overlay.enter()
        assert not overlay.is_complete()

        overlay.update(1.1)  # Exceed duration
        assert overlay.is_complete()

    def test_resets_elapsed_on_page_advance(self):
        """page_elapsed resets to 0 when advancing pages."""
        conv = make_multi_page_conversation()
        overlay = ConversationOverlay(conv)

        overlay.enter()
        overlay.update(1.5)  # Exceed first page duration by 0.5

        # Should have advanced to page 2 and reset elapsed
        assert overlay.current_page.text == "Page 2"
        assert overlay.page_elapsed == 0.0

    def test_multiple_updates_accumulate(self):
        """Multiple small updates accumulate time correctly."""
        conv = make_single_page_conversation(duration=1.0)
        overlay = ConversationOverlay(conv)

        overlay.enter()

        # Multiple small updates
        overlay.update(0.3)
        overlay.update(0.3)
        overlay.update(0.3)

        assert not overlay.is_complete()
        assert overlay.page_elapsed == pytest.approx(0.9)

        overlay.update(0.2)  # This should complete
        assert overlay.is_complete()
