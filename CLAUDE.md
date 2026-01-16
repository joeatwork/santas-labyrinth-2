# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

This project uses `uv` for Python package management and execution:

```bash
# Install dependencies
uv venv && uv pip install -r requirements.txt

# Run animation generator (saves to output.flv)
uv run stream_animation.py

# Run with custom parameters
uv run stream_animation.py --width 1920 --height 1080 --fps 60 --map-width 5 --map-height 5

# Stream to Twitch (requires TWITCH_STREAM_KEY file)
./stream_to_twitch.sh

# Test streaming with known good media
./test_stream_to_twitch.sh --test-only --duration 10
./test_stream.py --test-only --duration 30
```

## Architecture Overview

This is an animation streaming system, intended to stream different kinds of generative audio and video content via RTMP.

### Core Architecture

#### Content and VideoProgram

The system has a number of different sorts of content that act as "Scenes" in the video stream. Right now
those scenes fall into a few varieties:

- `TitleCard`: Static image content
- `DungeonWalk`: Procedural dungeon exploration with hero movement
- `VideoClip`: Pre-recorded video segments from `large_media/` directory

It's likely that we'll add new varieties of content as the system grows.

Content is organized into a VideoProgram, which is an ordered, looping collection of content objects.

#### Streaming pipeline

The top level script, stream_animation.py, constructs and queries a VideoProgram, and uses
an FfmpegStreamer to manage pushing the audio and video into an ffmpeg subprocess. That subprocess
is responsible for the coding and streaming the video and audio into an flv suitable for streaming.

The flv stream is consumed by another ffmpeg process in stream_to_twitch.sh, which handles copying
the inbound stream to an RTMP output.

**World Generation**:
- `dungeon_gen.py`: Maze generation algorithms using DFS, outputs `DungeonMap` tile arrays
- `world.py`: `Dungeon` class (world state) and `Hero` class (player character with movement/collision)
- `animation.py`: `AssetManager` (sprite loading) + rendering functions that convert world state to pixels

### Key Data Flow

1. **Content Creation**: `stream_animation.py` creates a `Stream` and adds content segments (title card, dungeon walk, video clips)
2. **World Simulation**: `DungeonWalk` content generates procedural dungeons, simulates hero movement with collision detection
3. **Rendering**: `AssetManager` loads sprite tiles, `render_frame_camera` converts world coordinates to screen pixels
4. **Streaming**: `Streamer` encodes frames to FLV format, can output to file or stdout for RTMP piping

### Asset System

- **Sprites**: `assets/sprites/` contains tiled sprite sheets, `SPRITE_OFFSETS` in `animation.py` defines tile coordinates
- **Large Media**: `large_media/` contains video files that can be randomly selected as `VideoClip` content
- **Rendering**: Uses OpenCV (cv2) for image manipulation, 64x64 pixel tiles, camera system with world-to-screen coordinate translation

## Key Configuration

- **Tile System**: 64x64 pixel tiles, tile IDs defined in `dungeon_gen.py` `Tile` class
- **Room Dimensions**: 12x10 tiles per room (`ROOM_WIDTH`, `ROOM_HEIGHT`)
- **Video Output**: Defaults to 1280x720 at 30fps, H.264/AAC encoding in FLV container
- **RTMP Endpoint**: Uses Twitch ingest server `rtmp://iad05.contribute.live-video.net/app/`
