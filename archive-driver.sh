#!/bin/bash

STREAM_URL="https://listen.wbor.org:8000/stream"

# Container for audio files. Match source!
CONTAINER="mp3"

# Date at time of script start
CURRENT_YEAR=$(date +%Y)
CURRENT_MONTH=$(date +%m)
CURRENT_DAY=$(date +%d)

# Initial directory to store recordings
RECORDINGS_DIR="/archive/$CURRENT_YEAR/$CURRENT_MONTH/$CURRENT_DAY"
mkdir -p "$RECORDINGS_DIR"

# Start ffmpeg - 1hr recordings
ffmpeg \
    -i "$STREAM_URL" \
    -f segment \
    -segment_time 3600 \
    -segment_atclocktime 1 \
    -strftime 1 \
    -c copy \
    "$RECORDINGS_DIR/stream_%Y-%m-%dT%H-%M-%SZ.$CONTAINER" &

# Store PID of ffmpeg
FFMPEG_PID=$!

# Continuously update directory structure
while true; do
    NEW_YEAR=$(date +%Y)
    NEW_MONTH=$(date +%m)
    NEW_DAY=$(date +%d)

    NEW_RECORDINGS_DIR="/archive/$NEW_YEAR/$NEW_MONTH/$NEW_DAY"

    # Create directory if it doesn't exist
    mkdir -p "$NEW_RECORDINGS_DIR"

    # If directory has changed, move recording
    if [ "$NEW_RECORDINGS_DIR" != "$RECORDINGS_DIR" ]; then
        mv "$RECORDINGS_DIR"/* "$NEW_RECORDINGS_DIR"/
        RECORDINGS_DIR="$NEW_RECORDINGS_DIR"
    fi

    sleep 10
done
