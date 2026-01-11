import cv2
import numpy as np
import time
import random
from abc import ABC, abstractmethod
from typing import Tuple, List, Optional, Any

from animation import AssetManager, Image, create_dungeon_background, render_frame_camera
from world import Dungeon, Hero

class Content(ABC):
    @abstractmethod
    def enter(self) -> None:
        """Called when this content becomes active."""
        pass

    @abstractmethod
    def update(self, dt: float) -> None:
        """Update logic."""
        pass

    @abstractmethod
    def render(self, width: int, height: int) -> Image:
        """Render frame."""
        pass

class TitleCard(Content):
    def __init__(self, image_path: str, asset_manager: AssetManager):
        self.image_path = image_path
        self.image = cv2.imread(image_path)
        if self.image is None:
            # Fallback to black if missing
            print(f"Warning: Could not load title card {image_path}")
            self.image = None
        
    def enter(self) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def render(self, width: int, height: int) -> Image:
        if self.image is None:
             return np.zeros((height, width, 3), np.uint8)
        
        # Resize to fit stream dimensions
        return cv2.resize(self.image, (width, height))

class DungeonWalk(Content):
    def __init__(self, map_width_rooms: int, map_height_rooms: int, assets: AssetManager):
        self.map_width = map_width_rooms
        self.map_height = map_height_rooms
        self.assets = assets
        self.dungeon: Optional[Dungeon] = None
        self.hero: Optional[Hero] = None
        self.background: Optional[Image] = None

    def enter(self) -> None:
        print("Entering DungeonWalk: Generating new world...")
        self.dungeon = Dungeon(self.map_width, self.map_height)
        self.hero = Hero(self.dungeon.start_pos[0], self.dungeon.start_pos[1])
        self.background = create_dungeon_background(self.dungeon.map, self.assets)

    def update(self, dt: float) -> None:
        if self.hero and self.dungeon:
            self.hero.update(dt, self.dungeon)

    def render(self, width: int, height: int) -> Image:
        if self.hero and self.background is not None:
             return render_frame_camera(self.background, self.assets, self.hero, width, height)
        return np.zeros((height, width, 3), np.uint8)

class VideoClip(Content):
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.cap: Optional[cv2.VideoCapture] = None
        self.total_frames: int = 0
        self.fps: float = 30.0

    def enter(self) -> None:
        if self.cap is not None:
             self.cap.release()
        
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            print(f"Error: Could not open video {self.video_path}")
            return
            
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            self.fps = 30.0
            
        # Required frames for 30s playback
        req_seconds = 30.0
        req_frames = int(req_seconds * self.fps)
        
        start_frame = 0
        if self.total_frames > req_frames:
             max_start = self.total_frames - req_frames
             start_frame = random.randint(0, max_start)
             
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        print(f"Playing video {self.video_path} from frame {start_frame}...")

    def update(self, dt: float) -> None:
        pass

    def render(self, width: int, height: int) -> Image:
        if self.cap is None or not self.cap.isOpened():
            return np.zeros((height, width, 3), np.uint8)
            
        ret, frame = self.cap.read()
        if not ret:
            return np.zeros((height, width, 3), np.uint8)
            
        return cv2.resize(frame, (width, height))

class Stream:
    def __init__(self):
        # List of (Content, duration_seconds)
        self.playlist: List[Tuple[Content, float]] = []
        self.current_index = 0
        self.time_in_current = 0.0

    def add_content(self, content: Content, duration: float):
        self.playlist.append((content, duration))

    def start(self):
        if not self.playlist:
            return
        self.current_index = 0
        self.time_in_current = 0.0
        self.playlist[self.current_index][0].enter()

    def update(self, dt: float):
        if not self.playlist:
            return

        self.time_in_current += dt
        current_content, duration = self.playlist[self.current_index]
        
        current_content.update(dt)

        if self.time_in_current >= duration:
            # Advance to next
            self.current_index = (self.current_index + 1) % len(self.playlist)
            self.time_in_current = 0.0
            self.playlist[self.current_index][0].enter()

    def render(self, width: int, height: int) -> Image:
        if not self.playlist:
            return np.zeros((height, width, 3), np.uint8)
        
        return self.playlist[self.current_index][0].render(width, height)
