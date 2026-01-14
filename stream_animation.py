import argparse
import sys
import time
import os
import random
import glob
from animation import AssetManager
from streaming import Streamer
from content import Stream, TitleCard, DungeonWalk, VideoClip


def log(message: str) -> None:
    """Log to stderr to avoid corrupting stdout stream."""
    print(message, file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=str, default='output.flv', help='File output')
    parser.add_argument('--stdout', action='store_true', help='Output FLV to stdout for piping')
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=720)
    parser.add_argument('--fps', type=int, default=30)
    parser.add_argument('--seed', type=int, default=None, help='Random seed for reproducibility')
    parser.add_argument('--map-width', type=int, default=3, help='Map width in rooms')
    parser.add_argument('--map-height', type=int, default=3, help='Map height in rooms')
    args = parser.parse_args()

    # Set random seed if specified
    if args.seed is not None:
        random.seed(args.seed)
        log(f"Using random seed: {args.seed}")

    # Validate arguments
    if args.stdout and args.output != 'output.flv':
        print("Error: Cannot specify both --stdout and --output", file=sys.stderr)
        sys.exit(1)

    # Load Assets
    try:
        assets = AssetManager()
        assets.load_images()
    except Exception as e:
        log(f"Error loading assets: {e}")
        return

    # Initialize Stream Loop
    stream = Stream()
    
    title_path = os.path.join('assets', 'stills', 'title_cart_taste_the_quality.png')
    stream.add_content(TitleCard(title_path, assets), 15.0)
      
    stream.add_content(DungeonWalk(args.map_width, args.map_height, assets), 40.0)
   
    video_files = glob.glob(os.path.join('large_media', '*.mp4'))
    if video_files:
        video_path = random.choice(video_files)
        log(f"Selected video clip: {video_path}")
        stream.add_content(VideoClip(video_path), 20.0)
    else:
        log("Warning: No MP4 videos found in large_media directory")
   
    stream.start()

    # Setup Streamer
    target = "-" if args.stdout else args.output
    streamer = Streamer(args.width, args.height, args.fps, target)
    streamer.start()

    start_time = time.time()
    last_frame_time = start_time
    
    try:
        while True:
            current_time = time.time()
            dt = current_time - last_frame_time
            last_frame_time = current_time
            
            # Update Stream
            stream.update(dt)
            
            # Render Stream
            frame = stream.render(args.width, args.height)
            
            if not streamer.write_frame(frame):
                break
            
            # Maintain FPS
            elapsed = time.time() - current_time
            sleep_time = max(0, (1.0/args.fps) - elapsed)
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        pass
    finally:
        log("Stopping stream...")
        streamer.close()

if __name__ == '__main__':
    main()
