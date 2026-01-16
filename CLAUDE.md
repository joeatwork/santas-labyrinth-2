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

This is a **procedural animation streaming system** that generates synthetic dungeon exploration animations and streams them via RTMP. The system is composed of several key layers:

### Core Architecture

**Content Pipeline**: `Content` abstract base class defines scenes that can be composed into streams:
- `TitleCard`: Static image content
- `DungeonWalk`: Procedural dungeon exploration with hero movement
- `VideoClip`: Pre-recorded video segments from `large_media/` directory
- `Stream`: Orchestrator that sequences different content types over time

**Streaming Pipeline**:
- `stream_animation.py`: Entry point that creates content sequence and manages streaming loop
- `streaming.py`: `Streamer` class handles video/audio encoding using PyAV (outputs FLV)
- `stream_to_twitch.sh`: FFmpeg wrapper for RTMP streaming to Twitch

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

### Streaming Architecture Notes

**Known Issues**:
- Audio/video sync problems in `stream_animation.py` lines 77-99 (produces video in chunks before audio)
- Only silence audio is generated (line 98), no audio extraction from video clips
- Large buffering delays due to 30-second video chunks before audio processing

**Testing**: Use `test_stream.py` and `test_stream_to_twitch.sh` to bypass animation system and test RTMP pipeline with known good media files.

## Key Configuration

- **Tile System**: 64x64 pixel tiles, tile IDs defined in `dungeon_gen.py` `Tile` class
- **Room Dimensions**: 12x10 tiles per room (`ROOM_WIDTH`, `ROOM_HEIGHT`)
- **Video Output**: Defaults to 1280x720 at 30fps, H.264/AAC encoding in FLV container
- **RTMP Endpoint**: Uses Twitch ingest server `rtmp://iad05.contribute.live-video.net/app/`