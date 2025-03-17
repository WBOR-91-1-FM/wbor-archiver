"""
The backend is connected to the archive file system (as read-only) and provides
an API to list and download recordings. As needed (determined by the request),
concatenation of multiple files into a single download is supported for gapless
playback across a given time range.

Processing includes:
- Computing the SHA-256 hash of the file.
- Storing the metadata in the database.

Absolute paths should not be used. Instead, use `ARCHIVE_BASE` to refer to the
archive root directory.

By default, public users are anonymous and have read-only access to the archive.
Administrators have full access to the archive and can perform administrative
tasks such as hiding recordings.

Admin users are identified by a secret token that is passed in the
`X-Admin-Token` header. An admin user table is stored in the database, which
maps tokens to user IDs. An endpoint is provided to add new admin users,
provided a super-admin token is passed in the `X-Super-Admin-Token` header
(which is hardcoded in the service).

TODO:
- Record fields from file (using ffprobe):
    - bit_rate
    - sample_rate
    - icy-br
    - icy-genre
    - icy-name
    - icy-url
    - encoder
"""

import os
import time
import sys
import json
import threading
from pathlib import Path
import logging
import pytz
import pika
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d in %(funcName)s()] - %(message)s",
)

# Load environment variables from .env file if present
load_dotenv()

try:
    # Ensure environment variables are stripped of leading/trailing spaces
    ARCHIVE_DIR = os.getenv("ARCHIVE_DIR").strip()
    UNMATCHED_DIR = os.getenv("UNMATCHED_DIR").strip()

    # Parse and validate SEGMENT_DURATION_SECONDS
    segment_duration_str = os.getenv("SEGMENT_DURATION_SECONDS").strip()
    if not segment_duration_str.isdigit():
        raise ValueError(
            f"SEGMENT_DURATION_SECONDS must be an integer, got '{segment_duration_str}'"
        )
    SEGMENT_DURATION_SECONDS = int(segment_duration_str)

    # Use UTC timezone for consistency
    TZ = pytz.UTC

    # RabbitMQ configuration - passed in from docker-compose.yml
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST").strip()
    RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE").strip()
    RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE").strip()

    logging.debug(
        "Configuration loaded successfully:"
        "ARCHIVE_DIR=`%s`, SEGMENT_DURATION_SECONDS=`%s`, UNMATCHED_DIR=`%s`",
        ARCHIVE_DIR,
        SEGMENT_DURATION_SECONDS,
        UNMATCHED_DIR,
    )
except (ValueError, AttributeError, TypeError) as e:
    logging.error("Failed to load environment variables: `%s`", e)
    sys.exit(1)

app = FastAPI()

ARCHIVE_BASE = Path("/archive")


def _on_rabbitmq_message(ch, method, _properties, body):
    logging.info("Received message from RabbitMQ: `%s`", body)
    try:
        payload = json.loads(body)
        filename = payload.get("filename")
        timestamp = payload.get("timestamp", {})
        year = timestamp.get("year")
        month = timestamp.get("month")
        day = timestamp.get("day")
        hour = timestamp.get("hour")
        minute = timestamp.get("minute")
        second = timestamp.get("second")

        logging.debug(
            "Message indicates new file: `%s` at `%s-%s-%s %s:%s:%s`",
            filename,
            year,
            month,
            day,
            hour,
            minute,
            second,
        )
        # TODO: Compute SHA-256 hash of the file, store metadata in DB, etc.

    except (json.JSONDecodeError, TypeError) as e:
        logging.error("Failed to parse message: `%s`", e)
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)


def _rabbitmq_consumer():
    """
    Runs in a background thread. Connects to RabbitMQ and consumes messages.
    """
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST, heartbeat=600)
            )
            channel = connection.channel()
            channel.exchange_declare(
                exchange=RABBITMQ_EXCHANGE, exchange_type="direct", durable=True
            )
            channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
            channel.queue_bind(exchange=RABBITMQ_EXCHANGE, queue=RABBITMQ_QUEUE)

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue=RABBITMQ_QUEUE,
                on_message_callback=_on_rabbitmq_message,
                auto_ack=False,
            )

            logging.info("RabbitMQ consumer connected. Waiting for messages...")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(
                "RabbitMQ connection error: `%s`. Retrying in 5 seconds...", e
            )
            # Sleep briefly and retry the connection.
            time.sleep(5)
        except KeyboardInterrupt:
            logging.info("RabbitMQ consumer received KeyboardInterrupt; stopping.")
            break


@app.on_event("startup")
def start_rabbitmq_consumer():
    """
    Start the RabbitMQ consumer in a background thread when the FastAPI app starts.
    """
    consumer_thread = threading.Thread(target=_rabbitmq_consumer, daemon=True)
    consumer_thread.start()
    logging.info("Started RabbitMQ consumer thread.")


@app.get("/")
def home():
    """
    Status check endpoint.
    """
    logging.debug("Received status check request")
    return {"service": "WBOR Archiver API", "status": "ok"}


@app.get("/recordings")
def list_recordings():
    """
    List all recordings in the archive.
    """
    # Simple example: list all .mp3 files in /archive
    recordings = list(ARCHIVE_BASE.glob("**/*.mp3"))
    # Return minimal data for demonstration
    return {"count": len(recordings), "files": [str(r) for r in recordings]}


@app.get("/download/{year}/{month}/{day}/{filename}")
def download_recording(year: str, month: str, day: str, filename: str):
    """
    Download a recording from the archive.
    """
    file_path = ARCHIVE_BASE / year / month / day / filename
    if file_path.exists():
        return FileResponse(path=str(file_path), filename=filename)
    return {"error": "Recording not found"}
