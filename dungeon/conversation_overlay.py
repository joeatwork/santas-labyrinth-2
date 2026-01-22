"""
Conversation overlay for displaying NPC dialogue.

Renders conversation pages with optional portraits, advancing via ConversationEngine.
"""

import cv2
import numpy as np
from typing import Optional, List, Dict
from PIL import Image as PILImage, ImageDraw, ImageFont

from .conversation import ConversationEngine, ConversationPage

# Type alias matching animation.py
Image = np.ndarray


class ConversationOverlay:
    """
    Renders conversation pages, advancing via the ConversationEngine.

    Similar to CrashOverlay but with:
    - Multiple pages with auto-advance based on duration
    - Optional portrait images
    - Speaker name display
    - Word wrapping for long text
    """

    def __init__(self, engine: ConversationEngine):
        self.engine = engine
        self.current_page: Optional[ConversationPage] = None
        self.page_elapsed: float = 0.0
        self._portrait_cache: Dict[str, Image] = {}

    def enter(self) -> None:
        """Start the conversation."""
        self.current_page = self.engine.start()
        self.page_elapsed = 0.0

    def update(self, dt: float) -> None:
        """Advance time, moving to next page when current page duration expires."""
        if self.current_page is None:
            return

        self.page_elapsed += dt
        if self.page_elapsed >= self.current_page.duration:
            self.current_page = self.engine.respond(self.current_page)
            self.page_elapsed = 0.0

    def is_complete(self) -> bool:
        """Returns True when all pages have been shown."""
        return self.current_page is None

    def _load_portrait(self, path: str) -> Optional[Image]:
        """Load and cache portrait image."""
        if path in self._portrait_cache:
            return self._portrait_cache[path]

        portrait = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if portrait is not None:
            self._portrait_cache[path] = portrait
        return portrait

    def _wrap_text(
        self, text: str, draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, max_width: int
    ) -> List[str]:
        """Word wrap text to fit within max_width."""
        words = text.split()
        lines: List[str] = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        return lines

    def render(self, base_frame: Image, width: int, height: int) -> Image:
        """Render conversation box with text and optional portrait on top of base frame."""
        if self.is_complete() or self.current_page is None:
            return base_frame

        # Convert BGR numpy array to RGB PIL Image
        rgb_frame = cv2.cvtColor(base_frame, cv2.COLOR_BGR2RGB)
        pil_image = PILImage.fromarray(rgb_frame)
        draw = ImageDraw.Draw(pil_image)

        # Calculate box dimensions (bottom of screen, full width minus margins)
        margin = 40
        box_height = int(height * 0.25)
        box_x = margin
        box_y = height - box_height - margin
        box_width = width - (2 * margin)

        # Draw semi-transparent dark box
        overlay = PILImage.new("RGBA", (box_width, box_height), (20, 20, 40, 220))
        pil_image.paste(overlay, (box_x, box_y), overlay)

        # Reload draw after paste
        draw = ImageDraw.Draw(pil_image)

        # Draw border
        draw.rectangle(
            [box_x, box_y, box_x + box_width, box_y + box_height],
            outline=(200, 200, 220),
            width=2,
        )

        # Portrait area (left side of box if portrait exists)
        text_x_offset = 20
        portrait_size = box_height - 20

        if self.current_page.portrait_path:
            portrait = self._load_portrait(self.current_page.portrait_path)
            if portrait is not None:
                # Resize portrait to fit
                portrait_resized = cv2.resize(portrait, (portrait_size, portrait_size))

                # Portrait position
                portrait_x = box_x + 10
                portrait_y = box_y + 10

                # Convert portrait and overlay onto PIL image
                if portrait_resized.shape[2] == 4:
                    portrait_pil = PILImage.fromarray(
                        cv2.cvtColor(portrait_resized, cv2.COLOR_BGRA2RGBA)
                    )
                else:
                    portrait_pil = PILImage.fromarray(
                        cv2.cvtColor(portrait_resized, cv2.COLOR_BGR2RGB)
                    )
                pil_image.paste(portrait_pil, (portrait_x, portrait_y))

                # Shift text to right of portrait
                text_x_offset = portrait_size + 30

        # Load font
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
            small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        except (IOError, OSError):
            font = ImageFont.load_default()
            small_font = font

        # Draw speaker name
        text_x = box_x + text_x_offset
        text_y = box_y + 15
        speaker_name = self.current_page.speaker.upper()
        draw.text((text_x, text_y), speaker_name, fill=(180, 180, 220), font=small_font)

        # Draw text (with word wrapping)
        text_y += 25
        max_text_width = box_width - text_x_offset - 20

        lines = self._wrap_text(self.current_page.text, draw, font, max_text_width)

        # Draw each line
        line_height = 28
        for i, line in enumerate(lines):
            draw.text((text_x, text_y + i * line_height), line, fill=(255, 255, 255), font=font)

        # Convert back to BGR numpy array
        rgb_result = np.array(pil_image)
        return cv2.cvtColor(rgb_result, cv2.COLOR_RGB2BGR)
