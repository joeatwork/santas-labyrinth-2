import argparse
import sys
import os
import random
import glob
from animation import AssetManager
from streaming import FFmpegStreamer
from content import VideoProgram, TitleCard, DungeonWalk, VideoClip


def log(message: str) -> None:
    """Log to stderr to avoid corrupting stdout stream."""
    print(message, file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=str, default='output.flv', help='File output')
    parser.add_argument('--stdout', action='store_true', help='Output FLV to stdout for piping')
    parser.add_argument('--rtmp', type=str, help='RTMP URL to stream to (e.g., rtmp://server/app/key)')
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
    num_outputs = sum([args.stdout, args.rtmp is not None, args.output != 'output.flv'])
    if num_outputs > 1:
        print("Error: Cannot specify multiple output targets (--stdout, --rtmp, --output)", file=sys.stderr)
        sys.exit(1)

    # Load Assets
    try:
        assets = AssetManager()
        assets.load_images()
    except Exception as e:
        log(f"Error loading assets: {e}")
        return
 
    title_cards = [
        os.path.join('assets', 'stills', 'title_card_youre_soaking_in_it.png'),
        os.path.join('assets', 'stills', 'title_card_taste_the_quality.png'),
    ]

    # Initialize Stream Loop
    video_program = VideoProgram()
    
    video_files = glob.glob(os.path.join('large_media', '*.mp4'))
    random.shuffle(video_files)

    for video_path in video_files:
        title_path = title_cards.pop(0)
        title_cards.append(title_path)  # Rotate title cards
        video_program.add_content(TitleCard(title_path, assets), 15.0)
        video_program.add_content(DungeonWalk(args.map_width, args.map_height, assets), 120.0)
        video_program.add_content(VideoClip(video_path, 30, output_fps=args.fps), 20.0)
     
    video_program.start()

    # Setup Streamer
    if args.rtmp:
        target = args.rtmp
    elif args.stdout:
        target = "-"
    else:
        target = args.output
    audio_sample_rate = 44100
    audio_channels = 2
    streamer = FFmpegStreamer(args.width, args.height, args.fps, target,
                               audio_sample_rate, audio_channels)
    streamer.start()

    # Audio samples needed per video frame
    samples_per_frame = audio_sample_rate // args.fps

    frame_count = 0
    dt = 1.0 / args.fps  # Fixed timestep for consistent simulation

    try:
        while True:
            # Update Stream
            video_program.update(dt)

            # Render Stream
            frame = video_program.render(args.width, args.height)

            if not streamer.write_frame(frame):
                break

            # Get audio from content (or use silence if none available)
            audio = video_program.get_audio(samples_per_frame, audio_sample_rate, audio_channels)
            if audio is not None:
                if not streamer.write_audio(audio):
                    break
            else:
                if not streamer.write_silence(1):
                    break

            frame_count += 1

            # Progress indicator every second
            if frame_count % args.fps == 0:
                log(f"Frame {frame_count} ({frame_count // args.fps}s)")
            
    except KeyboardInterrupt:
        pass
    finally:
        log("Stopping stream...")
        streamer.close()

if __name__ == '__main__':
    main()
