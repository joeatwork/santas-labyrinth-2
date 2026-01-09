import subprocess

class Streamer:
    def __init__(self, width, height, fps, target):
        self.width = width
        self.height = height
        self.fps = fps
        self.target = target
        self.process = None

    def start(self):
        command = ['ffmpeg',
                   '-y',
                   '-f', 'rawvideo',
                   '-vcodec', 'rawvideo',
                   '-s', f'{self.width}x{self.height}',
                   '-pix_fmt', 'bgr24',
                   '-r', str(self.fps),
                   '-i', '-',
                   '-c:v', 'libx264',
                   '-pix_fmt', 'yuv420p',
                   '-preset', 'ultrafast',
                   '-f', 'flv',
                   self.target]

        print(f"Starting stream to: {self.target}")
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE)

    def write_frame(self, frame):
        if self.process and self.process.stdin:
            try:
                self.process.stdin.write(frame.tobytes())
                return True
            except BrokenPipeError:
                print("FFmpeg process terminated.")
                return False
        return False

    def close(self):
        if self.process:
            if self.process.stdin:
                self.process.stdin.close()
            self.process.wait()
            self.process = None
