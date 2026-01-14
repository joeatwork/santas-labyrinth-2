# Animation Streamer

This tool generates a synthetic animation using assets from *Santa's Labyrinth* and saves it to an FLV file or streams it via RTMP using `ffmpeg`.

This project was created with heavy use of LLM coding agents.

## Prerequisites

1.  **Python 3.x**
2.  **uv**: This project uses `uv` for fast Python package management and execution.
    *   **Install uv**: [See uv installation guide](https://github.com/astral-sh/uv?tab=readme-ov-file#installation) or run:
        ```bash
        curl -LsSf https://astral.sh/uv/install.sh | sh
        ```
3.  **FFmpeg**: Required for RTMP streaming. Install and add to your system's PATH.
    *   **macOS**: `brew install ffmpeg`
    *   **Ubuntu/Debian**: `sudo apt install ffmpeg`
    *   **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

## Installation

1.  Clone the repository or download the source files.
2.  Install dependencies using `uv`:

    ```bash
    # Create virtual environment and install dependencies
    uv venv
    uv pip install -r requirements.txt
    ```

## Usage

### 1. Save to File

By default, the script saves output to `output.flv`.

```bash
uv run stream_animation.py
```

**Options:**
*   `--output <filename>`: Output filename (default: `output.flv`)
*   `--width <int>`: Video width (default: 1280)
*   `--height <int>`: Video height (default: 720)
*   `--fps <int>`: Frames per second (default: 30)
*   `--map-width <int>`: Dungeon map width in rooms (default: 3)
*   `--map-height <int>`: Dungeon map height in rooms (default: 3)

**Example:**
```bash
uv run stream_animation.py --output my_animation.flv --width 1920 --height 1080
```

### 2. Stream to Twitch

Use the provided shell script to stream directly to Twitch:

1.  Create a file named `TWITCH_STREAM_KEY` containing your stream key
2.  Run the script:

```bash
chmod +x stream_to_twitch.sh
./stream_to_twitch.sh
```

You can pass additional options through to the animation script:

```bash
./stream_to_twitch.sh --width 1920 --height 1080 --fps 60
```

**Twitch RTMP URL used:** `rtmp://iad05.contribute.live-video.net/app/`

### 3. Stream to Other RTMP Servers

Use the `--stdout` flag to pipe FLV output to ffmpeg:

```bash
uv run stream_animation.py --stdout | ffmpeg -re -i pipe:0 -c copy -f flv rtmp://your-server/app/key
```

## Project Structure

*   `stream_animation.py`: Entry point script. Orchestrates the animation loop and streaming.
*   `streaming.py`: Handles video encoding using PyAV.
*   `animation.py`: Handles asset loading (`AssetManager`) and frame rendering.
*   `stream_to_twitch.sh`: Shell script to stream to Twitch via ffmpeg.
*   `assets/`: Contains game sprites and tiles.

## Testing

### Testing File Output
1.  Run the script: `uv run stream_animation.py`
2.  Wait for a few seconds.
3.  Press `Ctrl+C` to stop.
4.  Open `output.flv` with a video player like VLC to verify the animation.

### Testing Stdout Output
```bash
uv run stream_animation.py --stdout > test.flv
# Press Ctrl+C after a few seconds
ffprobe test.flv  # Verify the file is valid
```
