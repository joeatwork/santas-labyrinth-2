#!/bin/bash
# Stream animation directly to Twitch
#
# Usage: ./stream_to_twitch.sh [OPTIONS]
#
# Options are passed through to stream_animation.py (e.g. --width, --height, --fps)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load stream key
if [[ -f "TWITCH_STREAM_KEY" ]]; then
    STREAM_KEY=$(cat TWITCH_STREAM_KEY)
else
    echo "Error: TWITCH_STREAM_KEY file not found" >&2
    echo "Create a file named TWITCH_STREAM_KEY containing your Twitch stream key" >&2
    exit 1
fi

RTMP_URL="rtmp://iad05.contribute.live-video.net/app/${STREAM_KEY}"

echo "Streaming to Twitch..." >&2

uv run stream_animation.py --rtmp "$RTMP_URL" "$@"
