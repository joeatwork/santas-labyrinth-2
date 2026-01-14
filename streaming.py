import av
import sys
import numpy as np
from typing import Optional, IO, Union


class Streamer:
    def __init__(
        self,
        width: int,
        height: int,
        fps: int,
        output_target: str,
        audio_sample_rate: int = 44100,
        audio_channels: int = 2,
    ) -> None:
        self.width: int = width
        self.height: int = height
        self.fps: int = fps
        self.output_target: str = output_target
        self.audio_sample_rate: int = audio_sample_rate
        self.audio_channels: int = audio_channels

        # PyAV objects
        self.container: Optional[av.container.OutputContainer] = None
        self.video_stream: Optional[av.stream.Stream] = None
        self.audio_stream: Optional[av.stream.Stream] = None

        # Frame counters for PTS calculation
        self.video_frame_count: int = 0
        self.audio_sample_count: int = 0

    def start(self) -> None:
        # Determine output target
        if self.output_target == "-":
            output: Union[str, IO[bytes]] = sys.stdout.buffer
            print("Starting stream to: stdout", file=sys.stderr)
        else:
            output = self.output_target
            print(f"Starting stream to: {self.output_target}", file=sys.stderr)

        # Always use FLV format
        format_name = "flv"

        try:
            self.container = av.open(output, mode="w", format=format_name)

            # Video stream: H.264
            self.video_stream = self.container.add_stream("libx264", rate=self.fps)
            self.video_stream.width = self.width
            self.video_stream.height = self.height
            self.video_stream.pix_fmt = "yuv420p"
            self.video_stream.options = {
                "preset": "veryfast",
                "crf": "23",
            }

            # Audio stream: AAC
            self.audio_stream = self.container.add_stream("aac", rate=self.audio_sample_rate)
            self.audio_stream.layout = "stereo" if self.audio_channels == 2 else "mono"

            # Reset counters
            self.video_frame_count = 0
            self.audio_sample_count = 0

        except Exception as e:
            print(f"Error initializing PyAV container: {e}", file=sys.stderr)
            self.container = None

    def write_frame(self, frame_bgr: np.ndarray) -> bool:
        if not self.container or not self.video_stream:
            return False

        try:
            # Convert BGR to RGB (PyAV expects RGB)
            frame_rgb = frame_bgr[:, :, ::-1].copy()

            # Create PyAV VideoFrame from numpy array
            video_frame = av.VideoFrame.from_ndarray(frame_rgb, format="rgb24")

            # Set PTS based on frame count (stream handles time_base)
            video_frame.pts = self.video_frame_count

            # Encode and mux
            for packet in self.video_stream.encode(video_frame):
                self.container.mux(packet)

            self.video_frame_count += 1
            return True

        except Exception as e:
            print(f"Error writing video frame: {e}", file=sys.stderr)
            return False

    def write_audio(self, samples: np.ndarray) -> bool:
        """
        Write audio samples to the stream.

        Args:
            samples: Audio samples as numpy array.
                     Shape should be (num_samples,) for mono or (num_samples, 2) for stereo.
                     Expected dtype: int16 (s16) or float32.
        """
        if not self.container or not self.audio_stream:
            return False

        try:
            # Ensure correct shape for PyAV (channels, samples)
            if samples.ndim == 1:
                # Mono: reshape to (1, num_samples)
                samples = samples.reshape(1, -1)
            elif samples.ndim == 2:
                # Stereo input is (num_samples, channels), transpose to (channels, num_samples)
                samples = samples.T

            # Convert to the format PyAV expects
            if samples.dtype == np.float32:
                # Convert float32 [-1.0, 1.0] to int16
                samples = (samples * 32767).astype(np.int16)
            elif samples.dtype != np.int16:
                samples = samples.astype(np.int16)

            # Create AudioFrame
            audio_frame = av.AudioFrame.from_ndarray(samples, format="s16", layout=self.audio_stream.layout.name)
            audio_frame.sample_rate = self.audio_sample_rate
            audio_frame.pts = self.audio_sample_count

            # Encode and mux
            for packet in self.audio_stream.encode(audio_frame):
                self.container.mux(packet)

            self.audio_sample_count += samples.shape[1]  # Add number of samples
            return True

        except Exception as e:
            print(f"Error writing audio: {e}", file=sys.stderr)
            return False

    def close(self) -> None:
        if not self.container:
            return

        try:
            # Flush video encoder
            if self.video_stream:
                for packet in self.video_stream.encode():
                    self.container.mux(packet)

            # Flush audio encoder
            if self.audio_stream:
                for packet in self.audio_stream.encode():
                    self.container.mux(packet)

            self.container.close()
        except Exception as e:
            print(f"Error closing stream: {e}", file=sys.stderr)
        finally:
            self.container = None
            self.video_stream = None
            self.audio_stream = None
