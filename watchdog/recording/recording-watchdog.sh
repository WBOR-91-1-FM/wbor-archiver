#!/bin/bash

CONTAINER_NAME="wbor-archiver-recorder"

docker events --filter 'event=health_status' | while read event; do
    if echo "$event" | grep -q "unhealthy"; then
        echo "Container $CONTAINER_NAME is unhealthy!"
        echo "Sending a message to webhook..."
        echo "Restarting the container..."
        docker restart $CONTAINER_NAME
    fi
done
