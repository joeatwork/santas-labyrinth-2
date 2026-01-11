import subprocess
import numpy as np
from typing import Optional

class Streamer:
    def __init__(self, width: int, height: int, fps: int, output_target: str) -> None:
        self.width: int = width
        self.height: int = height
        self.fps: int = fps
        self.output_target: str = output_target
        self.process: Optional[subprocess.Popen] = None

    def start(self) -> None:
        print(f"Starting stream to: {self.output_target}")
        
        # Determine format based on extension or protocol
        format_name = 'flv' # Default to FLV
        
        command = [
            'ffmpeg',
            '-y', # Overwrite output
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{self.width}x{self.height}',
            '-pix_fmt', 'bgr24',
            '-r', str(self.fps),
            '-i', '-', # Input from stdin
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-preset', 'veryfast',
            '-b:v', '3000k',
            '-maxrate', '3000k',
            '-bufsize', '6000k',
            '-g', str(self.fps * 2), # GOP size 2 seconds
            '-f', format_name,
            self.output_target
        ]
        
        try:
            self.process = subprocess.Popen(
                command, 
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE, 
                stdout=subprocess.PIPE
            )
        except FileNotFoundError:
            print("Error: ffmpeg not found. Please install ffmpeg.")
            self.process = None

    def write_frame(self, frame_bgr: np.ndarray) -> bool:
        if not self.process:
            return False
            
        try:
            if self.process.stdin:
                self.process.stdin.write(frame_bgr.tobytes())
                return True
            return False
        except (BrokenPipeError, IOError):
            print("FFmpeg process crashed or stopped.")
            self.process = None
            return False

    def close(self) -> None:
        if self.process:
            if self.process.stdin:
                self.process.stdin.close()
            self.process.wait()
            self.process = None
