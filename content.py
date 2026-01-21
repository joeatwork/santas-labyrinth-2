import av
import cv2
import sys
import numpy as np
import random
from abc import ABC, abstractmethod
from typing import Tuple, List, Optional, Any
from PIL import Image as PILImage, ImageDraw, ImageFont

from dungeon.animation import AssetManager, Image, create_dungeon_background, create_dungeon_foreground, render_frame_camera
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
    
class RandomChoiceContent(Content):
    """
    Chooses randomly from a list of content options each time it is entered.
    """
    def __init__(self, options: List[Content]):
        self.options = options
        self.current_content: Optional[Content] = None

    def enter(self) -> None:
        self.current_content = random.choice(self.options)
        self.current_content.enter()

    def update(self, dt: float) -> None:
        if self.current_content:
            self.current_content.update(dt)

    def render(self, width: int, height: int) -> Image:
        if self.current_content:
            return self.current_content.render(width, height)
        return np.zeros((height, width, 3), np.uint8)

    def get_audio(self, num_samples: int, sample_rate: int, channels: int) -> Optional[np.ndarray]:
        if self.current_content:
            return self.current_content.get_audio(num_samples, sample_rate, channels)
        return None

    def is_complete(self) -> bool:
        if self.current_content:
            return self.current_content.is_complete()
        return False

class TitleCard(Content):
    # TODO: get rid of the optional argument and always require audio, reorder the arguments to a more natural order
    def __init__(self, image_path: str, asset_manager: AssetManager, audio_path: Optional[str] = None, volume: float = 1.0):
        self.image_path = image_path
        self.audio_path = audio_path
        self.volume = volume
        self.image = cv2.imread(image_path)
        if self.image is None:
            raise ValueError(f"Could not load title card image {image_path}")

        # Audio state
        self.audio_container: Optional[av.container.InputContainer] = None
        self.audio_stream: Optional[av.stream.Stream] = None
        self.audio_resampler: Optional[av.audio.resampler.AudioResampler] = None
        self.audio_buffer: np.ndarray = np.zeros((0, 2), dtype=np.int16)
        self.audio_sample_rate: int = 44100
        self.audio_finished: bool = False

    def enter(self) -> None:
        # Reset audio state
        self.audio_buffer = np.zeros((0, 2), dtype=np.int16)
        self.audio_finished = False

        if self.audio_container is not None:
            self.audio_container.close()
            self.audio_container = None

        if self.audio_path is None:
            return

        try:
            self.audio_container = av.open(self.audio_path)
        except Exception as e:
            print(f"Error: Could not open audio {self.audio_path}: {e}", file=sys.stderr)
            self.audio_finished = True
            return

        # Get audio stream
        audio_streams = [s for s in self.audio_container.streams if s.type == 'audio']
        if audio_streams:
            self.audio_stream = audio_streams[0]
            # Create resampler to convert to output format (44100Hz stereo s16 planar)
            self.audio_resampler = av.audio.resampler.AudioResampler(
                format='s16p',
                layout='stereo',
                rate=self.audio_sample_rate,
            )
            print(f"TitleCard audio: {self.audio_stream.sample_rate}Hz {self.audio_stream.format.name} -> {self.audio_sample_rate}Hz s16p stereo", file=sys.stderr)
        else:
            raise ValueError("no audio stream in {self.audio_path}")

    def _decode_audio(self) -> bool:
        """Decode more audio into the buffer. Returns False if EOF reached or if the stream can't be read."""
        if self.audio_container is None or self.audio_stream is None or self.audio_resampler is None:
            return False

        try:
            for packet in self.audio_container.demux(self.audio_stream):
                for frame in packet.decode():
                    resampled = self.audio_resampler.resample(frame)
                    if resampled:
                        for rf in resampled:
                            arr = rf.to_ndarray()
                            arr = arr.T  # (channels, samples) -> (samples, channels)
                            self.audio_buffer = np.vstack([self.audio_buffer, arr])
                return True  # Got some audio
        except av.error.EOFError:
            # Flush the resampler
            try:
                resampled = self.audio_resampler.resample(None)
                if resampled:
                    for rf in resampled:
                        arr = rf.to_ndarray()
                        arr = arr.T
                        self.audio_buffer = np.vstack([self.audio_buffer, arr])
            except:
                pass
            return False
        except Exception as e:
            print(f"Error decoding audio: {e}", file=sys.stderr)
            return False

    def update(self, dt: float) -> None:
        pass

    def render(self, width: int, height: int) -> Image:
        if self.image is None:
             return np.zeros((height, width, 3), np.uint8)

        # Resize to fit stream dimensions
        return cv2.resize(self.image, (width, height))

    def get_audio(self, num_samples: int, sample_rate: int, channels: int) -> Optional[np.ndarray]:
        """Return audio samples for this frame."""
        if self.audio_path is None or self.audio_finished:
            return None

        # Decode more audio if buffer is running low
        while len(self.audio_buffer) < num_samples and not self.audio_finished:
            if not self._decode_audio():
                self.audio_finished = True
                break

        if len(self.audio_buffer) == 0:
            return None

        if len(self.audio_buffer) < num_samples:
            # Return what we have padded with silence (final chunk)
            result = np.zeros((num_samples, channels), dtype=np.int16)
            result[:len(self.audio_buffer)] = self.audio_buffer[:, :channels]
            self.audio_buffer = np.zeros((0, 2), dtype=np.int16)
        else:
            # Return requested samples and keep the rest buffered
            result = self.audio_buffer[:num_samples, :channels].copy()
            self.audio_buffer = self.audio_buffer[num_samples:]

        # Apply volume scaling
        if self.volume != 1.0:
            result = (result.astype(np.float32) * self.volume).astype(np.int16)

        return result

    def is_complete(self) -> bool:
        """Complete when audio finishes (if audio was provided)."""
        if self.audio_path is None:
            return False  # No audio, rely on duration
        return self.audio_finished and len(self.audio_buffer) == 0

class CrashOverlay:
    """
    Renders a white box overlay with dynamic text lines.
    Used to display crash/error messages on top of content.
    """
    def __init__(self, text_lines: List[str], duration: float = 10.0):
        self.text_lines = text_lines
        self.elapsed: float = 0.0
        self.duration = duration

    def update(self, dt: float) -> None:
        self.elapsed += dt

    def is_complete(self) -> bool:
        return self.elapsed >= self.duration

    def render(self, base_frame: Image, width: int, height: int) -> Image:
        """Render white box with text on top of base frame."""
        # Convert BGR numpy array to RGB PIL Image
        rgb_frame = cv2.cvtColor(base_frame, cv2.COLOR_BGR2RGB)
        pil_image = PILImage.fromarray(rgb_frame)
        draw = ImageDraw.Draw(pil_image)

        # Calculate box dimensions (60% of screen, centered)
        box_width = int(width * 0.6)
        box_height = int(height * 0.4)
        box_x = (width - box_width) // 2
        box_y = (height - box_height) // 2

        # Draw white box with black border
        draw.rectangle(
            [box_x, box_y, box_x + box_width, box_y + box_height],
            fill='white',
            outline='black',
            width=3
        )

        # Load a font (use default if no specific font available)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        except (IOError, OSError):
            font = ImageFont.load_default()

        # Draw text lines centered in the box
        text_y = box_y + 40
        for line in self.text_lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = box_x + (box_width - text_width) // 2
            draw.text((text_x, text_y), line, fill='black', font=font)
            text_y += 35

        # Convert back to BGR numpy array
        rgb_result = np.array(pil_image)
        return cv2.cvtColor(rgb_result, cv2.COLOR_RGB2BGR)


class DungeonWalk(Content):
    def __init__(self, num_rooms: int, assets: AssetManager, goal_movie: Content):
        self.num_rooms = num_rooms
        self.assets = assets
        self.dungeon: Optional[Dungeon] = None
        self.hero: Optional[Hero] = None
        self.background: Optional[Image] = None
        self.foreground: Optional[Image] = None

        # Crash detection state
        self.idle_time: float = 0.0
        self.idle_threshold: float = 3.0  # seconds before crash is triggered
        self.crash_overlay: Optional[CrashOverlay] = None
        
        self.goal_movie = goal_movie
        self.playing_goal_movie: bool = False


    def enter(self) -> None:
        print("Entering DungeonWalk: Generating new world...", file=sys.stderr)
        self.dungeon = Dungeon(self.num_rooms)
        self.hero = Hero(self.dungeon.start_pos[0], self.dungeon.start_pos[1])
        self.background = create_dungeon_background(self.dungeon.map, self.assets)
        self.foreground = create_dungeon_foreground(self.dungeon.map, self.assets)

        # Reset crash state and win state
        self.idle_time = 0.0
        self.crash_overlay = None
        self.playing_goal_movie = False

    def update(self, dt: float) -> None:
        # If crash overlay is active, update it and skip hero updates
        if self.crash_overlay:
            self.crash_overlay.update(dt)
            return

        if self.playing_goal_movie:
            self.goal_movie.update(dt)
            return

        if self.dungeon.is_on_goal(self.hero.x, self.hero.y):
            print("DungeonWalk: Hero reached goal, starting goal movie...", file=sys.stderr)
            self.goal_movie.enter()
            self.playing_goal_movie = True
            return

        # Otherwise, update the dungeon
        self.hero.update(dt, self.dungeon)

        # Track idle time for crash detection
        if self.hero.state == 'idle':
            self.idle_time += dt
            if self.idle_time > self.idle_threshold:
                self._trigger_crash()
        else:
            self.idle_time = 0.0
        

    def _trigger_crash(self) -> None:
        """Trigger crash overlay when hero is stuck."""
        print("DungeonWalk: Hero crash detected, showing overlay...", file=sys.stderr)
        self.crash_overlay = CrashOverlay([
            "robot crash detected ... rebooting ..."
        ])

    def render(self, width: int, height: int) -> Image:
        if self.playing_goal_movie:
            return self.goal_movie.render(width, height)

        # Render base dungeon frame
        if self.hero and self.background is not None:
            base_frame = render_frame_camera(self.background, self.assets, self.hero, width, height, self.foreground)
        else:
            base_frame = np.zeros((height, width, 3), np.uint8)

        # Overlay crash box if active
        if self.crash_overlay:
            return self.crash_overlay.render(base_frame, width, height)

        return base_frame

    def get_audio(self, num_samples, sample_rate, channels):
        if self.playing_goal_movie:
            return self.goal_movie.get_audio(num_samples, sample_rate, channels)
        
        # TODO: dungeon should have it's own audio
        return None

    def is_complete(self) -> bool:
        if self.playing_goal_movie:
            return self.goal_movie.is_complete()

        # Complete if crash overlay finished
        if self.crash_overlay and self.crash_overlay.is_complete():
            return True

        return False

class VideoClip(Content):
    """
    Video clip content that plays both video and audio from a file.
    Uses PyAV for decoding to get synchronized audio.
    """

    def __init__(self, video_path: str, max_length_seconds: int, output_fps: float = 30.0):
        self.video_path = video_path
        self.container: Optional[av.container.InputContainer] = None
        self.video_stream: Optional[av.stream.Stream] = None
        self.audio_stream: Optional[av.stream.Stream] = None
        self.source_fps: float = 30.0  # Will be read from file
        self.output_fps: float = output_fps
        self.audio_sample_rate: int = 44100
        self.max_length_seconds = max_length_seconds

        # Decoded frame/audio buffers
        self.current_frame: Optional[np.ndarray] = None
        self.audio_buffer: np.ndarray = np.zeros((0, 2), dtype=np.int16)

        # Frame rate conversion: track source time to decide when to decode new frames
        self.source_time: float = 0.0  # Accumulated time in source video
        self.last_decoded_frame: Optional[np.ndarray] = None

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

        # Get video stream and read source fps
        video_streams = [s for s in self.container.streams if s.type == 'video']
        if video_streams:
            self.video_stream = video_streams[0]
            self.source_fps = float(self.video_stream.average_rate) if self.video_stream.average_rate else 30.0
            print(f"Video stream: {self.source_fps:.3f} fps source -> {self.output_fps:.3f} fps output", file=sys.stderr)
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

        # Clear buffers and reset timing state
        self.current_frame = None
        self.last_decoded_frame = None
        self.audio_buffer = np.zeros((0, 2), dtype=np.int16)
        self.source_time = 0.0

        # Pre-decode first frame
        self._decode_next()
        self.last_decoded_frame = self.current_frame

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
        # Advance source time by how much real time one output frame represents
        output_frame_duration = 1.0 / self.output_fps
        self.source_time += output_frame_duration

        # Calculate how much source video time we should have consumed
        source_frame_duration = 1.0 / self.source_fps

        # Decode frames until we catch up to where source_time says we should be
        # This handles both dropping frames (source faster than output) and
        # duplicating frames (source slower than output - we just don't decode)
        frames_to_decode = int(self.source_time / source_frame_duration)
        frames_decoded = 0

        while frames_decoded < frames_to_decode:
            self._decode_next()
            if self.current_frame is not None:
                self.last_decoded_frame = self.current_frame
            frames_decoded += 1

        # Subtract the time we've consumed
        self.source_time -= frames_to_decode * source_frame_duration

        # Return the last decoded frame (may be duplicated if source is slower)
        frame_to_show = self.last_decoded_frame
        if frame_to_show is None:
            return np.zeros((height, width, 3), np.uint8)

        return cv2.resize(frame_to_show, (width, height))

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
