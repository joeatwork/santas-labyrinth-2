# Animation Streamer

This tool generates a synthetic animation using assets from *Santa's Labyrinth* and streams it via RTMP or saves it to an FLV file using `ffmpeg`.

This project was created with heavy use of LLM coding agents.

## Prerequisites

1.  **Python 3.x**
2.  **uv**: This project uses `uv` for fast Python package management and execution.
    *   **Install uv**: [See uv installation guide](https://github.com/astral-sh/uv?tab=readme-ov-file#installation) or run:
        ```bash
        curl -LsSf https://astral.sh/uv/install.sh | sh
        ```
3.  **FFmpeg**: This tool requires `ffmpeg` to be installed and available in your system's PATH.
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

You can run the script using `uv run`.

### 1. Save to File (Testing)

By default, without a `--url` argument, the script will save the output to `output.flv`.

```bash
uv run stream_animation.py
```

**Options:**
*   `--output <filename>`: Specify detailed output filename (default: `output.flv`).
*   `--width <int>`: Video width (default: 800).
*   `--height <int>`: Video height (default: 600).
*   `--fps <int>`: Frames per second (default: 30).

**Example:**
```bash
uv run stream_animation.py --output my_animation.flv --width 1280 --height 720
```

### 2. Stream to RTMP

To stream to an RTMP server (e.g., YouTube Live, Twitch, or a local Nginx RTMP module), use the `--url` argument.

```bash
uv run stream_animation.py --url rtmp://localhost/live/stream_key
```

Here is the current US East Twitch RTMP URL:

```
rtmp://iad05.contribute.live-video.net/app/$TWITCH_STREAM_KEY
```

**Note:** Ensure your RTMP server is running and accessible.

## Project Structure

*   `stream_animation.py`: Entry point script. Orchestrates the animation loop and streaming.
*   `animation.py`: Handles asset loading (`AssetManager`) and frame rendering.
*   `streaming.py`: Handles the `FFmpeg` process via `subprocess`.
*   `assets/`: Contains game sprites and tiles.

## Testing

### Testing File Output
1.  Run the script: `uv run stream_animation.py`
2.  Wait for a few seconds.
3.  Press `Ctrl+C` to stop.
4.  Open `output.flv` with a video player like VLC to verify the animation.

### Testing RTMP Streaming
1.  Start your RTMP server.
2.  Run the script: `uv run stream_animation.py --url rtmp://your-server/app/key`
3.  Open a media player (like VLC) and point it to your RTMP URL.
4.  Verify the animation is playing live.
