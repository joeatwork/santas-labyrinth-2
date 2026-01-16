import av
import subprocess
import sys
import numpy as np
from typing import Optional, IO, Union


class FFmpegStreamer:
    """
    Streamer that uses PyAV to mux video+audio into NUT format on a single pipe,
    then ffmpeg re-encodes to FLV for output.

    This avoids deadlocks from multiple pipes by using a single interleaved stream.
    """

    def __init__(
        self,
        width: int,
        height: int,
        fps: int,
        output_target: str,
        audio_sample_rate: int = 44100,
        audio_channels: int = 2,
    ) -> None:
        self.width = width
        self.height = height
        self.fps = fps
        self.output_target = output_target
        self.audio_sample_rate = audio_sample_rate
        self.audio_channels = audio_channels

        self.ffmpeg_process: Optional[subprocess.Popen] = None
        self.container: Optional[av.container.OutputContainer] = None
        self.video_stream: Optional[av.stream.Stream] = None
        self.audio_stream: Optional[av.stream.Stream] = None

        self.frame_count = 0
        self.audio_sample_count = 0
        self.samples_per_frame = audio_sample_rate // fps

    def start(self) -> None:
        # Build ffmpeg command to read NUT from stdin and output FLV
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "nut",
            "-i", "pipe:0",
            # Video encoding
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-pix_fmt", "yuv420p",
            # Audio encoding
            "-c:a", "aac",
            "-ar", str(self.audio_sample_rate),
            # Output
            "-f", "flv",
        ]

        if self.output_target == "-":
            cmd.append("pipe:1")
            print("Starting FFmpeg stream to: stdout", file=sys.stderr)
        else:
            cmd.append(self.output_target)
            print(f"Starting FFmpeg stream to: {self.output_target}", file=sys.stderr)

        print(f"FFmpeg command: {' '.join(cmd)}", file=sys.stderr)

        # Start ffmpeg
        self.ffmpeg_process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=sys.stdout.buffer if self.output_target == "-" else None,
            stderr=subprocess.DEVNULL,
        )

        # Open PyAV container writing NUT to ffmpeg's stdin
        self.container = av.open(
            self.ffmpeg_process.stdin,
            mode='w',
            format='nut',
        )

        # Add video stream (raw RGB, will be encoded by ffmpeg)
        self.video_stream = self.container.add_stream('rawvideo', rate=self.fps)
        self.video_stream.width = self.width
        self.video_stream.height = self.height
        self.video_stream.pix_fmt = 'rgb24'

        # Add audio stream (raw PCM, will be encoded by ffmpeg)
        self.audio_stream = self.container.add_stream('pcm_s16le', rate=self.audio_sample_rate)
        self.audio_stream.layout = 'stereo' if self.audio_channels == 2 else 'mono'

        self.frame_count = 0
        self.audio_sample_count = 0

        print(f"PyAV container opened, muxing to NUT format", file=sys.stderr)

    def write_frame(self, frame_bgr: np.ndarray) -> bool:
        if not self.video_stream or not self.container:
            return False

        try:
            # Convert BGR to RGB
            frame_rgb = frame_bgr[:, :, ::-1].copy()

            # Create video frame
            video_frame = av.VideoFrame.from_ndarray(frame_rgb, format='rgb24')
            video_frame.pts = self.frame_count

            # Encode and mux
            for packet in self.video_stream.encode(video_frame):
                self.container.mux(packet)

            self.frame_count += 1
            return True

        except BrokenPipeError:
            print("FFmpeg pipe closed", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Error writing video frame: {e}", file=sys.stderr)
            return False

    def write_silence(self, frames: int) -> bool:
        """Write silence for the given number of video frames."""
        silence = np.zeros((frames * self.samples_per_frame, self.audio_channels), dtype=np.int16)
        return self.write_audio(silence)

    def write_audio(self, samples: Optional[np.ndarray]) -> bool:
        """
        Write audio samples to the stream.

        Args:
            samples: Audio samples as numpy array.
                     Shape should be (num_samples, channels) for stereo.
                     Expected dtype: int16.
        """
        if not self.audio_stream or not self.container:
            return False

        if samples is None:
            return True

        try:
            # Ensure int16
            if samples.dtype != np.int16:
                if samples.dtype == np.float32:
                    samples = (samples * 32767).astype(np.int16)
                else:
                    samples = samples.astype(np.int16)

            # Input is (num_samples, channels), e.g. (1470, 2)
            # PyAV with format='s16p' (planar) expects (channels, num_samples)
            if samples.ndim == 2:
                num_samples = samples.shape[0]
                samples = np.ascontiguousarray(samples.T)  # (channels, num_samples)
            else:
                num_samples = samples.shape[0]
                samples = np.ascontiguousarray(samples.reshape(1, -1))

            # Create audio frame using planar format (s16p)
            audio_frame = av.AudioFrame.from_ndarray(samples, format='s16p', layout=self.audio_stream.layout.name)
            audio_frame.sample_rate = self.audio_sample_rate
            audio_frame.pts = self.audio_sample_count

            # Encode and mux
            for packet in self.audio_stream.encode(audio_frame):
                self.container.mux(packet)

            self.audio_sample_count += num_samples
            return True

        except BrokenPipeError:
            print("FFmpeg pipe closed", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Error writing audio: {e}", file=sys.stderr)
            return False

    def close(self) -> None:
        if self.container:
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
                print(f"Error closing container: {e}", file=sys.stderr)
            finally:
                self.container = None
                self.video_stream = None
                self.audio_stream = None

        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.wait(timeout=5)
            except Exception as e:
                print(f"Error closing ffmpeg: {e}", file=sys.stderr)
                self.ffmpeg_process.kill()
            finally:
                self.ffmpeg_process = None


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
        # Producing an audio stream with no samples breaks RTMP
        # (It's likely that ffmpeg waits for samples and never sends the stream)
        self.audio_stream = self.container.add_stream("aac", rate=self.audio_sample_rate)
        self.audio_stream.layout = "stereo" if self.audio_channels == 2 else "mono"

        # Reset counters
        self.video_frame_count = 0
        self.audio_sample_count = 0


    def write_frame(self, frame_bgr: np.ndarray) -> bool:
        if not self.video_stream:
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

    def write_silence(self, frames: int) -> bool:
        """
        Write silence to the stream. Note the duration is in frames, not audio samples or seconds.
        """
        samples_per_frame = self.audio_sample_rate // self.fps
        silence = np.zeros((frames * samples_per_frame, self.audio_channels), dtype=np.int16)

        return self.write_audio(silence)

    def write_audio(self, samples: Optional[np.ndarray]) -> bool:
        """
        Write audio samples to the stream.

        Args:
            samples: Audio samples as numpy array.
                     Shape should be (num_samples,) for mono or (num_samples, 2) for stereo.
                     Expected dtype: int16 (s16) or float32.
        """
        if not self.audio_stream:
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
