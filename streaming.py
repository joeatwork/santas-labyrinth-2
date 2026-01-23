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

            # log progress once per minute
            "-stats_period", "60",

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
        ]

        # Determine output destination and add appropriate options
        is_rtmp = self.output_target.startswith("rtmp://")

        if is_rtmp:
            # We write to the ffmpeg process as fast as we can,
            # and the -re flag ensures we don't overwhelm client buffers
            # by getting too far ahead.
            cmd.append("-re")

            # RTMP-specific buffering and rate control
            cmd.extend([
                # Rate control for smoother streaming
                "-maxrate", "3000k",
                "-bufsize", "6000k",  # 2 seconds of buffer at 3Mbps
                # Keyframe interval (every 2 seconds for Twitch)
                "-g", str(self.fps * 2),
                # FLV flags to avoid header update issues
                "-flvflags", "no_duration_filesize",
                # Output format
                "-f", "flv",
            ])
            cmd.append(self.output_target)
            print(f"Starting FFmpeg stream to RTMP: {self.output_target[:50]}...", file=sys.stderr)
        elif self.output_target == "-":
            cmd.extend(["-f", "flv"])
            cmd.append("pipe:1")
            print("Starting FFmpeg stream to: stdout", file=sys.stderr)
        else:
            cmd.extend(["-f", "flv"])
            cmd.append(self.output_target)
            print(f"Starting FFmpeg stream to file: {self.output_target}", file=sys.stderr)

        print(f"FFmpeg command: {' '.join(cmd[:20])}...", file=sys.stderr)

        # Start ffmpeg
        # Only redirect stdout if we're piping to stdout
        stdout_dest = sys.stdout.buffer if self.output_target == "-" else None
        self.ffmpeg_process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=stdout_dest,
            stderr=None,  # Let ffmpeg errors show for debugging
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
        # This can take a long time, since ffmpeg runs in -re
        # mode and may have buffered a lot of video.
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
                self.ffmpeg_process.wait(timeout=60)
            except Exception as e:
                print(f"Error closing ffmpeg: {e}", file=sys.stderr)
                self.ffmpeg_process.kill()
            finally:
                self.ffmpeg_process = None
