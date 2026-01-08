# Animation Streamer

This tool generates a synthetic animation (a bouncing ball with dynamic background) and streams it via RTMP or saves it to an FLV file using `ffmpeg`.

## Prerequisites

1.  **Python 3.x**
2.  **uv**: This project uses `uv` for fast Python package management.
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
2.  Create a virtual environment and install dependencies using `uv`:

    ```bash
    # Create a virtual environment
    uv venv

    # Activate the virtual environment
    # On macOS/Linux:
    source .venv/bin/activate
    # On Windows:
    # .venv\Scripts\activate

    # Install dependencies
    uv pip install -r requirements.txt
    ```

## Usage

You can run the script in two modes: saving to a file or streaming via RTMP.

### 1. Save to File (Testing)

By default, without a `--url` argument, the script will save the output to `output.flv`.

```bash
python stream_animation.py
```

**Options:**
*   `--output <filename>`: Specify detailed output filename (default: `output.flv`).
*   `--width <int>`: Video width (default: 1280).
*   `--height <int>`: Video height (default: 720).
*   `--fps <int>`: Frames per second (default: 30).

**Example:**
```bash
python stream_animation.py --output my_animation.flv --width 1920 --height 1080
```

### 2. Stream to RTMP

To stream to an RTMP server (e.g., YouTube Live, Twitch, or a local NGINX RTMP module), use the `--url` argument.

```bash
python stream_animation.py --url rtmp://localhost/live/stream_key
```

**Note:** Ensure your RTMP server is running and accessible.

## Testing

### Testing File Output
1.  Run the script: `python stream_animation.py`
2.  Wait for a few seconds.
3.  Press `Ctrl+C` to stop.
4.  Open `output.flv` with a video player like VLC or mpv to verify the animation.

### Testing RTMP Streaming
1.  Start your RTMP server (or use a service).
2.  Run the script with the correct URL: `python stream_animation.py --url rtmp://your-server/app/key`
3.  Open a media player capable of playing network streams (like VLC).
4.  Open Network Stream in VLC and point it to your RTMP URL (or the viewing URL provided by your server).
5.  Verify the bouncing ball animation is playing live.
