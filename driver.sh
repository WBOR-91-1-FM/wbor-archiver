#!/bin/bash

STREAM_URL="https://listen.wbor.org:8000/stream"

# Directory to store recordings
RECORDINGS_DIR="/archive"

# Loop to continuously record audio
while true; do
    TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
    ffmpeg -i "$STREAM_URL" -t 1800 -acodec copy "$RECORDINGS_DIR/$TIMESTAMP.mp3"
    sleep 1800  # Wait for 30 minutes
done
