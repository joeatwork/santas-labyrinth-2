import argparse
import time
import os
import random
import glob
from animation import AssetManager
from streaming import Streamer
from content import Stream, TitleCard, DungeonWalk, VideoClip

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', type=str, default='', help='RTMP URL')
    parser.add_argument('--output', type=str, default='output.flv', help='File output')
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=720)
    parser.add_argument('--fps', type=int, default=30)
    parser.add_argument('--map-width', type=int, default=3, help='Map width in rooms')
    parser.add_argument('--map-height', type=int, default=3, help='Map height in rooms')
    args = parser.parse_args()

    # Load Assets
    try:
        assets = AssetManager()
        assets.load_images()
    except Exception as e:
        print(f"Error loading assets: {e}")
        return

    # Initialize Stream Loop
    stream = Stream()
    
    title_path = os.path.join('assets', 'stills', 'title_cart_taste_the_quality.png')
    stream.add_content(TitleCard(title_path, assets), 15.0)
      
    stream.add_content(DungeonWalk(args.map_width, args.map_height, assets), 40.0)
   
    video_files = glob.glob(os.path.join('large_media', '*.mp4'))
    if video_files:
        video_path = random.choice(video_files)
        print(f"Selected video clip: {video_path}")
        stream.add_content(VideoClip(video_path), 20.0)
    else:
        print("Warning: No MP4 videos found in large_media directory")
   
    stream.start()

    # Setup Streamer
    target = args.url if args.url else args.output
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
        print("Stopping stream...")
        streamer.close()

if __name__ == '__main__':
    main()
