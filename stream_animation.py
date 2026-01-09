import argparse
import time
from animation import AssetManager, create_level_background, render_frame
from streaming import Streamer

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', type=str, default='', help='RTMP URL')
    parser.add_argument('--output', type=str, default='output.flv', help='File output')
    parser.add_argument('--width', type=int, default=800)
    parser.add_argument('--height', type=int, default=600)
    parser.add_argument('--fps', type=int, default=30)
    args = parser.parse_args()

    # Load Assets
    try:
        assets = AssetManager()
        assets.load_images()
    except Exception as e:
        print(f"Error loading assets: {e}")
        return

    # Pre-render static background
    print("Generating background...")
    background = create_level_background(args.width, args.height, assets)

    # Setup Streamer
    target = args.url if args.url else args.output
    streamer = Streamer(args.width, args.height, args.fps, target)
    streamer.start()

    start_time = time.time()
    
    try:
        while True:
            t = time.time() - start_time
            frame = render_frame(background, assets, t)
            
            if not streamer.write_frame(frame):
                break
            
            elapsed = (time.time() - start_time) - t
            sleep_time = max(0, (1.0/args.fps) - elapsed)
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        pass
    finally:
        print("Stopping stream...")
        streamer.close()

if __name__ == '__main__':
    main()
