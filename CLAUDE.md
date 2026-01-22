# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## General Guidelines and Style

We prefer to write unit tests and use them to validate new features and prevent regressions. Prefer simple tests that are short and easy to understand to exhaustive tests, it's ok to test a few cases rather than overcomplicate the tests.

In many cases, we prefer to fail with exceptions when inputs are nonsensical.

We prefer explicit arguments to default arguments.

This is a small code base (at the moment) and often breaking changes to APIs are
easier than maintaining old versions, since it may be practical to update all callers
with little effort.

Prefer data classes to naked tuples for arguments and return values when not
doing pure mathematics.

We prefer small modules with clear boundaries to large python modules. Modules should use well defined, clear types to call one another.

## Development Commands

This project uses `uv` for Python package management and execution:

```bash
# Install dependencies
uv venv && uv pip install -r requirements.txt

# Run animation generator (saves to output.flv)
uv run stream_animation.py

# Run with custom parameters
uv run stream_animation.py --width 1920 --height 1080 --fps 60 --num-rooms 30 --seed 42

# Stream to Twitch (requires TWITCH_STREAM_KEY file)
./stream_to_twitch.sh

# Test streaming with known good media
./test_stream_to_twitch.sh --test-only --duration 10
./test_stream.py --test-only --duration 30

# Run unit tests
uv run python -m pytest tests/ -v
```

## Architecture Overview

This is an animation streaming system, intended to stream different kinds of generative audio and video content via RTMP.

### Core Architecture

#### Content and VideoProgram

All content types inherit from the `Content` abstract base class in `content.py`, which defines:
- `enter()`: Called when content becomes active
- `update(dt)`: Update logic each frame
- `render(width, height)`: Returns the current frame as a numpy array
- `get_audio(num_samples, sample_rate, channels)`: Returns audio samples (optional)
- `is_complete()`: Allows content to signal completion before duration expires

Current content types:
- `TitleCard`: Static image with optional synchronized audio (PyAV-decoded, with volume control)
- `DungeonWalk`: Procedural dungeon exploration with hero movement and crash detection
- `VideoClip`: Pre-recorded video segments from `large_media/` directory (uses PyAV for decoding, random seek within video)
- `RandomChoiceContent`: Wrapper that randomly selects from a list of content options each time entered
- `CrashOverlay`: White box overlay with centered black text, used for error messages when hero gets stuck

Content is organized into a `VideoProgram`, which is an ordered, looping collection of content objects with durations. The program advances when duration expires OR when content signals completion via `is_complete()`.

#### Streaming pipeline

The top level script, stream_animation.py, constructs and queries a VideoProgram, and uses
an FfmpegStreamer to manage pushing the audio and video into an ffmpeg subprocess. That subprocess
is responsible for the coding and streaming the video and audio into an flv suitable for streaming.

The flv stream is consumed by another ffmpeg process in stream_to_twitch.sh, which handles copying
the inbound stream to an RTMP output.

**FFmpeg Pipeline Details**:
- Uses NUT (Nu Trackable) as intermediate format between PyAV and FFmpeg
- PyAV writes raw video/audio to NUT format on stdin
- FFmpeg subprocess reads NUT and transcodes to FLV
- RTMP mode uses specific rate control: `-maxrate 3000k`, `-bufsize 6000k`
- Keyframe interval: every 2 seconds (fps * 2)

**World Generation**:

The DungeonWalk content type is a top down dungeon crawl video game, where a robot walks through a
maze-like dungeon. The code below generates that dungeon.

- `dungeon/dungeon_gen.py`: Procedural dungeon generation via organic room growth with door connections. Uses 11 pre-defined ASCII room templates. Algorithm: place initial room, queue open doors, iteratively attach compatible templates, replace unconnected doors with walls, place goal in last room, crop to bounding box.
- `dungeon/pathfinding.py`: BFS pathfinding algorithm with configurable max_distance.
- `dungeon/animation.py`: `AssetManager` (sprite loading) + rendering functions that convert world state to pixels.
- `dungeon/world.py`: `Dungeon` class (world state) and `Hero` class (player character with navigation AI). The hero navigates toward the goal using door-based pathfinding with dead-end tracking to avoid re-exploring rooms with no exits.

### Key Data Flow

1. **Content Creation**: `stream_animation.py` creates a `VideoProgram` and adds content segments (title card, dungeon walk, video clips)
2. **World Simulation**: `DungeonWalk` content generates procedural dungeons, simulates hero movement with collision detection
3. **Rendering**: `AssetManager` loads sprite tiles, `render_frame_camera` converts world coordinates to screen pixels
4. **Streaming**: `Streamer` encodes frames to FLV format, can output to file or stdout for RTMP piping

### Asset System

- **Sprites**: `assets/sprites/` contains tiled sprite sheets, `SPRITE_OFFSETS` in `dungeon/animation.py` defines tile coordinates
- **Title Cards**: `assets/stills/` contains static images for title card content
- **Large Media**: `large_media/` contains video files that can be randomly selected as `VideoClip` content
- **Large Audio**: `large_audio/` contains audio files (MP3) paired with title cards
- **Rendering**: Uses OpenCV (cv2) for image manipulation, 64x64 pixel tiles, camera system with world-to-screen coordinate translation

## Key Configuration

- **Tile System**: 64x64 pixel tiles (TILE_SIZE), tile IDs defined in `dungeon/dungeon_gen.py` `Tile` class (~48 tile types including walls, floors, doors, doorframes, pillars, and decorative variants)
- **Room Dimensions**: Vary by template (e.g., 12x10, 8x8, 14x6, 9x4, 4x8)
- **Video Output**: Defaults to 1280x720 at 30fps, H.264/AAC encoding in FLV container
- **Audio**: 44100Hz sample rate, stereo, 16-bit signed
- **Content Durations**: Title cards 30s, DungeonWalk 120s, VideoClips 20s
- **RTMP Endpoint**: Uses Twitch ingest server `rtmp://iad05.contribute.live-video.net/app/`
- **Crash Detection**: Hero idle for 3+ seconds triggers crash overlay

## Testing

Unit tests are in `tests/`. The `Hero` class accepts an optional `random_choice` parameter for dependency injection, allowing deterministic testing of navigation logic. Tests use a `MockDungeon` class for controlled tile layouts without full dungeon generation.

Test files:
- `tests/test_hero_navigation.py`: Hero navigation including goal approach, door selection, entry door avoidance, and dead-end detection
- `tests/test_dungeon_generation.py`: Dungeon generation algorithm properties
- `tests/test_hero_dungeon_integration.py`: Integration tests with real dungeons
- `tests/test_pathfinding.py`: BFS pathfinding edge cases
- `tests/test_room_templates.py`: Room template ASCII parsing validation

### Tools

- `tools/render_dungeon_ascii.py`: ASCII dungeon visualization utility for debugging

## Code TODOs

The following TODOs exist in the codebase:
- `dungeon/world.py`: `find_goal_position()` returns pixel position but should return tile position
- `dungeon/world.py`: Door tuples should use data classes
- `dungeon/world.py`: `get_room_id()` called with pixel positions instead of tile positions in some places
- `dungeon/dungeon_gen.py`: Tile class mixes logical tiles with rendering details (should be separate types)
- `dungeon/dungeon_gen.py`: Foreground generation should not be in dungeon_gen.py
- `dungeon/animation.py`: AssetManager should be in its own module (used by non-dungeon code)
- `content.py`: TitleCard should always require audio and reorder arguments