"""
Conversation overlay for displaying NPC dialogue.

Renders conversation pages with optional portraits, advancing via ConversationEngine.
"""

import cv2
import numpy as np
from typing import Optional, List
from PIL import Image as PILImage, ImageDraw, ImageFont

from dungeon.animation import AssetManager

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

    def __init__(self, engine: ConversationEngine, assets: AssetManager):
        self.engine = engine
        self.assets = assets
        self.current_page: Optional[ConversationPage] = None
        self.page_elapsed: float = 0.0

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

        # Calculate box dimensions
        box_width = int(width * 0.6)
        box_height = int(height * 0.8)
        box_x = (width - box_width) // 2
        box_y = (height - box_height) // 2

        # Draw white box with black border
        draw.rectangle(
            [box_x, box_y, box_x + box_width, box_y + box_height],
            fill="white",
            outline="black",
            width=3,
        )

        # Portrait area (right side of box if portrait exists)
        text_right_margin = 20

        if self.current_page.portrait_sprite:
            portrait = self.assets.get_sprite(self.current_page.portrait_sprite)
            if portrait is not None:
                # Use original sprite size
                portrait_height, portrait_width = portrait.shape[:2]

                # Portrait position (right side top)
                portrait_x = box_x + box_width - portrait_width - 10
                portrait_y = box_y + 10

                # Convert portrait and overlay onto PIL image
                if portrait.shape[2] == 4:
                    portrait_pil = PILImage.fromarray(
                        cv2.cvtColor(portrait, cv2.COLOR_BGRA2RGBA)
                    )
                else:
                    portrait_pil = PILImage.fromarray(
                        cv2.cvtColor(portrait, cv2.COLOR_BGR2RGB)
                    )
                pil_image.paste(portrait_pil, (portrait_x, portrait_y))

                # Reduce text width to account for portrait
                text_right_margin = portrait_width + 30

        # Draw speaker name
        text_x = box_x + 20
        text_y = box_y + 15
        speaker_name = self.current_page.speaker.upper()
        draw.text((text_x, text_y), speaker_name, fill=(0, 0, 0), font=self.assets.fonts['small'])

        # Draw text (with word wrapping)
        text_y += 25
        max_text_width = box_width - 20 - text_right_margin

        lines = self._wrap_text(self.current_page.text, draw, self.assets.fonts['regular'], max_text_width)

        # Draw each line
        line_height = int(self.assets.font_sizes['regular'] * 1.5)
        for i, line in enumerate(lines):
            draw.text((text_x, text_y + i * line_height), line, fill=(35, 35, 35), font=self.assets.fonts['regular'])

        # Convert back to BGR numpy array
        rgb_result = np.array(pil_image)
        return cv2.cvtColor(rgb_result, cv2.COLOR_RGB2BGR)
