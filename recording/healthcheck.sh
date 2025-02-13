#!/usr/bin/env bash

# Checks if at least one .mp3 file in /archive was updated in the last 5 minutes.

if [ "$(find /archive -maxdepth 1 -name '*.mp3' -mmin -5 | wc -l)" -gt "0" ]; then
    # Files updated in the last 5 min => container is healthy
    exit 0
else
    # No recent files => container is unhealthy
    exit 1
fi
