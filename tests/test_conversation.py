"""Unit tests for conversation data models."""

import pytest

from dungeon.conversation import ConversationPage, ConversationEngine, ScriptedConversation


class TestConversationPage:
    """Tests for ConversationPage dataclass."""

    def test_page_has_required_fields(self):
        """ConversationPage has text and speaker fields."""
        page = ConversationPage(text="Hello!", speaker="npc")
        assert page.text == "Hello!"
        assert page.speaker == "npc"

    def test_page_has_default_duration(self):
        """ConversationPage has default duration of 4.0 seconds."""
        page = ConversationPage(text="Hello!", speaker="npc")
        assert page.duration == 4.0

    def test_page_custom_duration(self):
        """ConversationPage accepts custom duration."""
        page = ConversationPage(text="Hello!", speaker="npc", duration=2.5)
        assert page.duration == 2.5

    def test_page_optional_portrait(self):
        """ConversationPage has optional portrait_sprite."""
        page = ConversationPage(text="Hello!", speaker="npc")
        assert page.portrait_sprite is None

        page_with_portrait = ConversationPage(
            text="Hello!",
            speaker="npc",
            portrait_sprite="wizard_portrait"
        )
        assert page_with_portrait.portrait_sprite == "wizard_portrait"


class TestScriptedConversation:
    """Tests for ScriptedConversation engine."""

    def test_requires_at_least_one_page(self):
        """ScriptedConversation raises if no pages provided."""
        with pytest.raises(ValueError):
            ScriptedConversation(pages=[])

    def test_start_returns_first_page(self):
        """start() returns the first page."""
        pages = [
            ConversationPage(text="First", speaker="npc"),
            ConversationPage(text="Second", speaker="hero"),
        ]
        conv = ScriptedConversation(pages)

        first = conv.start()
        assert first.text == "First"
        assert first.speaker == "npc"

    def test_respond_advances_pages(self):
        """respond() returns subsequent pages in order."""
        pages = [
            ConversationPage(text="First", speaker="npc"),
            ConversationPage(text="Second", speaker="hero"),
            ConversationPage(text="Third", speaker="npc"),
        ]
        conv = ScriptedConversation(pages)

        first = conv.start()
        second = conv.respond(first)
        assert second is not None
        assert second.text == "Second"

        third = conv.respond(second)
        assert third is not None
        assert third.text == "Third"

    def test_respond_returns_none_when_complete(self):
        """respond() returns None after last page."""
        pages = [
            ConversationPage(text="Only page", speaker="npc"),
        ]
        conv = ScriptedConversation(pages)

        first = conv.start()
        result = conv.respond(first)
        assert result is None

    def test_start_resets_to_beginning(self):
        """Calling start() again resets to the first page."""
        pages = [
            ConversationPage(text="First", speaker="npc"),
            ConversationPage(text="Second", speaker="hero"),
        ]
        conv = ScriptedConversation(pages)

        # Go through pages
        first = conv.start()
        conv.respond(first)

        # Reset
        reset_first = conv.start()
        assert reset_first.text == "First"
