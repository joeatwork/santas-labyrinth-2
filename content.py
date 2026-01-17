import av
import cv2
import sys
import numpy as np
import random
from abc import ABC, abstractmethod
from typing import Tuple, List, Optional, Any

from animation import AssetManager, Image, create_dungeon_background, create_dungeon_foreground, render_frame_camera
from world import Dungeon, Hero

class Content(ABC):
    """
    A unit of Content is a scene or segment that can be streamed. Callers can organize and select different units of Content
    over time.
    """
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

    def get_audio(self, num_samples: int, sample_rate: int, channels: int) -> Optional[np.ndarray]:
        """
        Get audio samples for the current frame.
        Returns None if no audio is available (silence will be used).
        Shape should be (num_samples, channels), dtype int16.
        """
        return None

    def is_complete(self) -> bool:
        """
        Returns True if this content has finished and should advance to the next.
        By default, content never completes on its own (relies on duration).
        """
        return False

class TitleCard(Content):
    def __init__(self, image_path: str, asset_manager: AssetManager):
        self.image_path = image_path
        self.image = cv2.imread(image_path)
        if self.image is None:
            # Fallback to black if missing
            print(f"Warning: Could not load title card {image_path}", file=sys.stderr)
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
        self.foreground: Optional[Image] = None

    def enter(self) -> None:
        print("Entering DungeonWalk: Generating new world...", file=sys.stderr)
        self.dungeon = Dungeon(self.map_width, self.map_height)
        self.hero = Hero(self.dungeon.start_pos[0], self.dungeon.start_pos[1])
        self.background = create_dungeon_background(self.dungeon.map, self.assets)
        self.foreground = create_dungeon_foreground(self.dungeon.map, self.assets)

    def update(self, dt: float) -> None:
        if self.hero and self.dungeon:
            self.hero.update(dt, self.dungeon)

    def render(self, width: int, height: int) -> Image:
        if self.hero and self.background is not None:
            return render_frame_camera(self.background, self.assets, self.hero, width, height, self.foreground)
        return np.zeros((height, width, 3), np.uint8)

    def is_complete(self) -> bool:
        if self.hero and self.dungeon:
            return self.dungeon.is_on_goal(self.hero.x, self.hero.y)
        return False

class VideoClip(Content):
    """
    Video clip content that plays both video and audio from a file.
    Uses PyAV for decoding to get synchronized audio.
    """

    def __init__(self, video_path: str, max_length_seconds: int):
        self.video_path = video_path
        self.container: Optional[av.container.InputContainer] = None
        self.video_stream: Optional[av.stream.Stream] = None
        self.audio_stream: Optional[av.stream.Stream] = None
        self.fps: float = 30.0
        self.audio_sample_rate: int = 44100
        self.max_length_seconds = max_length_seconds

        # Decoded frame/audio buffers
        self.current_frame: Optional[np.ndarray] = None
        self.audio_buffer: np.ndarray = np.zeros((0, 2), dtype=np.int16)

        # Audio resampler for consistent output format
        self.audio_resampler: Optional[av.audio.resampler.AudioResampler] = None

    def enter(self) -> None:
        if self.container is not None:
            self.container.close()

        try:
            self.container = av.open(self.video_path)
        except Exception as e:
            print(f"Error: Could not open video {self.video_path}: {e}", file=sys.stderr)
            return

        # Get video stream
        video_streams = [s for s in self.container.streams if s.type == 'video']
        if video_streams:
            self.video_stream = video_streams[0]
            self.fps = float(self.video_stream.average_rate) if self.video_stream.average_rate else 30.0

        else:
            print(f"Warning: No video stream in {self.video_path}", file=sys.stderr)
            self.video_stream = None

        # Get audio stream
        audio_streams = [s for s in self.container.streams if s.type == 'audio']
        if audio_streams:
            self.audio_stream = audio_streams[0]
            # Create resampler to convert to our output format (44100Hz stereo s16 planar)
            # Using s16p (planar) gives consistent (channels, samples) shape from to_ndarray()
            self.audio_resampler = av.audio.resampler.AudioResampler(
                format='s16p',
                layout='stereo',
                rate=self.audio_sample_rate,
            )
            print(f"Audio stream: {self.audio_stream.sample_rate}Hz {self.audio_stream.format.name} -> {self.audio_sample_rate}Hz s16p stereo", file=sys.stderr)
        else:
            print(f"Warning: No audio stream in {self.video_path}", file=sys.stderr)
            self.audio_stream = None
            self.audio_resampler = None

        # Seek to random position for variety
        if self.video_stream and self.container.duration:
            end_buffer_time = av.time_base * self.max_length_seconds
            if self.container.duration > end_buffer_time:
                # Pick a random start point, leaving room for 30s of content
                max_start = self.container.duration - end_buffer_time
                start_pts = random.randint(0, max_start)
                start_sec = start_pts / av.time_base
                self.container.seek(start_pts)
                print(f"Playing video {self.video_path} from {start_sec:.1f}s {start_pts}pts...", file=sys.stderr)
            else:
                print(f"Playing video {self.video_path} from start...", file=sys.stderr)

        # Clear buffers
        self.current_frame = None
        self.audio_buffer = np.zeros((0, 2), dtype=np.int16)

        # Pre-decode first frame
        self._decode_next()

    def _decode_next(self) -> None:
        """Decode the next video frame and associated audio."""
        if self.container is None:
            return

        try:
            for packet in self.container.demux(self.video_stream, self.audio_stream):
                if packet.stream == self.video_stream:
                    for frame in packet.decode():
                        # Convert to BGR for OpenCV compatibility
                        img = frame.to_ndarray(format='bgr24')
                        self.current_frame = img
                        return  # Got a video frame, stop

                elif packet.stream == self.audio_stream and self.audio_resampler:
                    for frame in packet.decode():
                        # Resample to target format (s16p stereo)
                        resampled = self.audio_resampler.resample(frame)
                        if resampled:
                            for rf in resampled:
                                # With s16p format, to_ndarray() returns (channels, samples) as int16
                                arr = rf.to_ndarray()
                                # Transpose to (samples, channels) for our buffer format
                                arr = arr.T
                                self.audio_buffer = np.vstack([self.audio_buffer, arr])

        except av.error.EOFError:
            pass
        except Exception as e:
            print(f"Error decoding: {e}", file=sys.stderr)

    def update(self, dt: float) -> None:
        pass

    def render(self, width: int, height: int) -> Image:
        # Decode next frame
        self._decode_next()

        if self.current_frame is None:
            return np.zeros((height, width, 3), np.uint8)

        return cv2.resize(self.current_frame, (width, height))

    def get_audio(self, num_samples: int, sample_rate: int, channels: int) -> Optional[np.ndarray]:
        """Return audio samples for this frame."""
        if len(self.audio_buffer) < num_samples:
            # Not enough audio buffered, return what we have padded with silence
            if len(self.audio_buffer) == 0:
                return None  # No audio, use silence

            result = np.zeros((num_samples, channels), dtype=np.int16)
            result[:len(self.audio_buffer)] = self.audio_buffer[:, :channels]
            self.audio_buffer = np.zeros((0, 2), dtype=np.int16)
            return result

        # Return requested samples and keep the rest buffered
        result = self.audio_buffer[:num_samples, :channels].copy()
        self.audio_buffer = self.audio_buffer[num_samples:]
        return result

class VideoProgram:
    """
    A Stream is a sequence of content objects, that are played one after another.
    """
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

        # Advance if duration exceeded or content signals completion
        if self.time_in_current >= duration or current_content.is_complete():
            self.current_index = (self.current_index + 1) % len(self.playlist)
            self.time_in_current = 0.0
            self.playlist[self.current_index][0].enter()

    def render(self, width: int, height: int) -> Image:
        if not self.playlist:
            return np.zeros((height, width, 3), np.uint8)

        return self.playlist[self.current_index][0].render(width, height)

    def get_audio(self, num_samples: int, sample_rate: int, channels: int) -> Optional[np.ndarray]:
        """Get audio from current content."""
        if not self.playlist:
            return None

        return self.playlist[self.current_index][0].get_audio(num_samples, sample_rate, channels)
