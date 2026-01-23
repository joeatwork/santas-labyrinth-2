import argparse
import sys
import os
import random
import glob
from dungeon.animation import AssetManager
from streaming import FFmpegStreamer
from content import AudioClip, VideoProgram, TitleCard, DungeonWalk, VideoClip, RandomChoiceContent


def log(message: str) -> None:
    """Log to stderr to avoid corrupting stdout stream."""
    print(message, file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, default="output.flv", help="File output")
    parser.add_argument(
        "--stdout", action="store_true", help="Output FLV to stdout for piping"
    )
    parser.add_argument(
        "--rtmp", type=str, help="RTMP URL to stream to (e.g., rtmp://server/app/key)"
    )
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument(
        "--seed", type=int, default=None, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--num-rooms", type=int, default=20, help="Number of rooms in dungeon"
    )
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        log(f"Using random seed: {args.seed}")

    # Validate arguments
    num_outputs = sum([args.stdout, args.rtmp is not None, args.output != "output.flv"])
    if num_outputs > 1:
        print(
            "Error: Cannot specify multiple output targets (--stdout, --rtmp, --output)",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load Assets
    assets = AssetManager()
    assets.load_images()
    assets.load_fonts()

    title_card_images = [
        os.path.join("assets", "stills", "title_card_youre_soaking_in_it.png"),
        os.path.join("assets", "stills", "title_card_taste_the_quality.png"),
    ]

    # Initialize Stream Loop
    video_program = VideoProgram()

    movie_videos = glob.glob(os.path.join("large_media", "*.mp4"))
    random.shuffle(movie_videos)

    title_card_songs = glob.glob(os.path.join("large_audio", "*.mp3"))
    random.shuffle(title_card_songs)

    title_cards = []
    for path in title_card_images:
        title_audio = title_card_songs.pop(0)
        title_card_songs.append(title_audio)  # Rotate title audios
        title_cards.append(TitleCard(path, AudioClip(title_audio, 0.2)))

    random_title_card = RandomChoiceContent(title_cards)
    random_video = RandomChoiceContent(
        [VideoClip(video_path, 15, output_fps=args.fps) for video_path in movie_videos]
    )

    dungeon_audio_file = os.path.join("assets", "dungeon_audio", "drones.mp3")
    dungeon_audio = AudioClip(dungeon_audio_file, 0.2)

    video_program.add_content(random_title_card, 30.0)
    video_program.add_content(DungeonWalk(args.num_rooms, assets, random_video, dungeon_audio), 120.0)

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
    streamer = FFmpegStreamer(
        args.width, args.height, args.fps, target, audio_sample_rate, audio_channels
    )
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
            audio = video_program.get_audio(
                samples_per_frame, audio_sample_rate, audio_channels
            )
            if audio is not None:
                if not streamer.write_audio(audio):
                    break
            else:
                if not streamer.write_silence(1):
                    break

            frame_count += 1
    finally:
        log("Stopping stream...")
        streamer.close()


if __name__ == "__main__":
    main()
