from dataclasses import dataclass
from typing import Optional


@dataclass
class Sprite:
    # File is a path usable by AssetManager
    # to load an image
    file: str

    # x and y are offsets into a source image.
    # The sprite is the section of the source image
    # at x,y and to w,h
    x: int
    y: int
    width: int = 64
    height: int = 64

    # base width and base height
    # are the blocking area of the
    # entity represented by the sprite,
    # some sprites are larger images
    # than the logical space they
    # take up in the world
    # If not provided, base_width and base_height
    # should be just width and height
    base_width: Optional[int] = None
    base_height: Optional[int] = None

    # Similar to base_width and base_height,
    # some sprites should be offset from
    # the tiles they're rendered in.
    offset_x: int = 0
    offset_y: int = 0

