import argparse
import time
from animation import AssetManager, create_dungeon_background, render_frame_camera
from world import Dungeon, Hero
from streaming import Streamer

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', type=str, default='', help='RTMP URL')
    parser.add_argument('--output', type=str, default='output.flv', help='File output')
    parser.add_argument('--width', type=int, default=800)
    parser.add_argument('--height', type=int, default=600)
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

    # Initialize World
    print("Generating dungeon world...")
    dungeon = Dungeon(args.map_width, args.map_height)
    
    print("Generating background image...")
    background = create_dungeon_background(dungeon.map, assets)
    
    # Initialize Hero
    hero = Hero(dungeon.start_pos[0], dungeon.start_pos[1])
    print(f"Hero starting at: {hero.x}, {hero.y}")

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
            
            # Update World State
            hero.update(dt, dungeon)
            
            # Render View
            frame = render_frame_camera(background, assets, hero, args.width, args.height)
            
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
