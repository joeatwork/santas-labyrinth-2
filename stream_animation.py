import argparse
import cv2
import numpy as np
import subprocess
import time

def create_animation_frame(width, height, t):
    """
    Generates a synthetic frame for the animation.
    A simple bouncing ball effect with changing background color.
    """
    # Create a blank image
    img = np.zeros((height, width, 3), np.uint8)
    
    # Dynamic background color
    b = int(127 + 127 * np.sin(t * 0.5))
    g = int(127 + 127 * np.cos(t * 0.5))
    r = int(127 + 127 * np.sin(t * 0.3))
    img[:] = (b, g, r)

    # Bouncing ball
    # x = A * sin(omega * t) + offset
    # y = A * cos(omega * t) + offset
    radius = 50
    center_x = int(width/2 + (width/3) * np.sin(t * 2))
    center_y = int(height/2 + (height/3) * np.cos(t * 3))
    
    cv2.circle(img, (center_x, center_y), radius, (255, 255, 255), -1)
    
    # Add some text
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, f"Time: {t:.2f}", (30, 50), font, 1, (0, 0, 0), 2, cv2.LINE_AA)
    
    return img

def main():
    parser = argparse.ArgumentParser(description='Stream synthetic animation via RTMP or to file using ffmpeg.')
    parser.add_argument('--url', type=str, help='RTMP URL to stream to (e.g., rtmp://localhost/live/stream). If not provided, defaults to file output.', default='')
    parser.add_argument('--output', type=str, help='Output filename if not streaming (default: output.flv)', default='output.flv')
    parser.add_argument('--width', type=int, default=1280, help='Video width')
    parser.add_argument('--height', type=int, default=720, help='Video height')
    parser.add_argument('--fps', type=int, default=30, help='Frames per second')
    
    args = parser.parse_args()
    
    width = args.width
    height = args.height
    fps = args.fps
    
    # FFmpeg command setup
    command = ['ffmpeg',
               '-y', # Overwrite output files without asking
               '-f', 'rawvideo',
               '-vcodec', 'rawvideo',
               '-s', f'{width}x{height}',
               '-pix_fmt', 'bgr24',
               '-r', str(fps),
               '-i', '-', # Input from pipe
               '-c:v', 'libx264',
               '-pix_fmt', 'yuv420p',
               '-preset', 'ultrafast',
               '-f', 'flv']

    if args.url:
        print(f"Streaming to: {args.url}")
        command.append(args.url)
    else:
        print(f"Saving to file: {args.output}")
        command.append(args.output)

    # Start ffmpeg process
    process = subprocess.Popen(command, stdin=subprocess.PIPE)

    print("Starting stream... Press Ctrl+C to stop.")
    
    start_time = time.time()
    
    try:
        while True:
            t = time.time() - start_time
            frame = create_animation_frame(width, height, t)
            
            # Write raw video frame to ffmpeg stdin
            try:
                process.stdin.write(frame.tobytes())
            except BrokenPipeError:
                print("FFmpeg process terminated.")
                break
                
            # Maintain FPS roughly (simple sleep)
            # In a production app, checking diffs would be more precise
            elapsed = (time.time() - start_time) - t
            sleep_time = max(0, (1.0/fps) - elapsed)
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        if process.stdin:
            process.stdin.close()
        process.wait()

if __name__ == '__main__':
    main()
