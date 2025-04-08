"""
The backend is connected to the archive file system (as read-only) and
provides an API to list and download recordings. As needed (determined
by the request), concatenation of multiple files into a single download
is supported for gapless playback across a given time range.

Processing includes:
- Computing the SHA-256 hash of the file.
- Storing the metadata in the database.

Absolute paths should not be used. Instead, use `ARCHIVE_BASE` to refer
to the archive root directory.

By default, public users are anonymous and have read-only access to the
archive. Administrators have full access to the archive and can perform
administrative tasks such as hiding recordings.

Admin users are identified by a secret token that is passed in the
`X-Admin-Token` header. An admin user table is stored in the database,
which maps tokens to user IDs. An endpoint is provided to add new admin
users, provided a super-admin token is passed in the
`X-Super-Admin-Token` header (which is hardcoded in the service).

NOTE: All routes are prefixed with `/api`.

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

import json
import logging
import os
import sys
import threading
import time
from pathlib import Path

import pika
import pytz
import sqlalchemy
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import FileResponse
from models import Segment
from sqlalchemy.orm import Session
from utils.ffprobe import probe as get_ffprobe_output
from utils.hash import hash_file
from utils.logging import configure_logging

from database import SessionLocal

logging.root.handlers = []
logging.getLogger("pika").setLevel(logging.WARNING)
logger = configure_logging()

load_dotenv()

try:
    ARCHIVE_DIR = os.getenv("ARCHIVE_DIR").strip()
    UNMATCHED_DIR = os.getenv("UNMATCHED_DIR").strip()
    segment_duration_str = os.getenv("SEGMENT_DURATION_SECONDS").strip()
    if not segment_duration_str.isdigit():
        raise ValueError(
            f"SEGMENT_DURATION_SECONDS must be an integer, got '{segment_duration_str}'"
        )
    SEGMENT_DURATION_SECONDS = int(segment_duration_str)

    # Use UTC timezone for backend consistency
    TZ = pytz.UTC

    # RabbitMQ configuration (these are passed in docker-compose.yml)
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST").strip()
    RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE").strip()
    RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE").strip()

    logger.debug(
        "Configuration loaded successfully:"
        "ARCHIVE_DIR=`%s`, SEGMENT_DURATION_SECONDS=`%s`, UNMATCHED_DIR=`%s`",
        ARCHIVE_DIR,
        SEGMENT_DURATION_SECONDS,
        UNMATCHED_DIR,
    )
except (ValueError, AttributeError, TypeError) as e:
    logger.error("Failed to load environment variables: `%s`", e)
    sys.exit(1)

ARCHIVE_BASE = Path(ARCHIVE_DIR)
router = APIRouter()


def get_db():
    """
    Dependency to get a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _on_rabbitmq_message(ch, method, _properties, body):
    """
    Callback function to handle messages from RabbitMQ.
    """
    logger.debug("Received message from RabbitMQ with payload: `%s`", body)
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

        if filename != f"WBOR-{year}-{month}-{day}T{hour}:{minute}:{second}Z.mp3":
            logger.error(
                "Filename does not match expected format: `%s`",
                filename,
            )
            return

        logger.info(
            "New file: `WBOR-%s-%s-%sT%s:%s:%sZ`",
            year,
            month,
            day,
            hour,
            minute,
            second,
        )
        hash = hash_file(str(ARCHIVE_BASE / year / month / day / filename))
        ffprobe = get_ffprobe_output(str(ARCHIVE_BASE / year / month / day / filename))

        db = SessionLocal()
        try:
            new_rec = Segment(
                filename=filename,
                archived_path=str(ARCHIVE_BASE / year / month / day / filename),
                start_ts=timestamp,
                # end_ts=,
                sha256_hash=hash,
                bit_rate=ffprobe.get("bit_rate"),
                sample_rate=ffprobe.get("sample_rate"),
                icy_br=ffprobe.get("icy_br"),
                icy_genre=ffprobe.get("icy_genre"),
                icy_name=ffprobe.get("icy_name"),
                icy_url=ffprobe.get("icy_url"),
                encoder=ffprobe.get("encoder"),
            )
            db.add(new_rec)
            db.commit()
        except (sqlalchemy.exc.SQLAlchemyError, AttributeError, TypeError) as e:
            db.rollback()
            logger.error("Error inserting record: %s", e)
        finally:
            db.close()

    except (json.JSONDecodeError, TypeError) as e:
        logger.error("Failed to parse message: `%s`", e)
    finally:
        # NOTE: `finally` runs even if an exception is raised
        # Acknowledge the message, regardless of success/failure
        ch.basic_ack(delivery_tag=method.delivery_tag)


def _rabbitmq_consumer(stop_event: threading.Event):
    """
    Runs in a background thread. Connects to RabbitMQ and consumes
    messages.
    """
    while not stop_event.is_set():
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

            logger.info("RabbitMQ consumer connected. Waiting for messages...")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logger.error("RabbitMQ connection error: `%s`. Retrying in 5 seconds...", e)
            # Sleep briefly and retry the connection.
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("RabbitMQ consumer received KeyboardInterrupt; stopping.")
            break


def lifespan(_application: FastAPI):
    """
    Start/stop the RabbitMQ consumer thread when the FastAPI app
    starts/stops.
    """
    stop_event = threading.Event()

    # Startup
    # `daemon=False` is set so that the consumer thread isn't killed
    # when the main thread (lifespan) exits - it is kept alive until
    # finished.
    consumer_thread = threading.Thread(
        target=_rabbitmq_consumer, args=(stop_event,), daemon=False
    )
    consumer_thread.start()
    logger.info("Started RabbitMQ consumer thread via lifespan.")

    yield

    # On shutdown, send stop event to rabbitmq consumer thread and wait
    # for it to exit cleanly (important, since it may be in the middle
    # of processing a message).
    stop_event.set()
    consumer_thread.join()
    logger.info("Consumer thread has exited cleanly.")


app = FastAPI(lifespan=lifespan)


@router.get("/")
def home():
    """
    Status check endpoint.
    """
    return {"service": "WBOR Archiver API", "status": "ok"}


@router.get("/recordings")
def list_recordings():
    """
    List all recordings in the archive.
    """
    # Simple example: list all .mp3 files in /archive
    recordings = list(ARCHIVE_BASE.glob("**/*.mp3"))
    # Return minimal data for demonstration
    return {"count": len(recordings), "files": [str(r) for r in recordings]}


@router.get("/download/{year}/{month}/{day}/{filename}")
def download_recording(year: str, month: str, day: str, filename: str):
    """
    Download a recording from the archive.
    """
    file_path = ARCHIVE_BASE / year / month / day / filename
    if file_path.exists():
        return FileResponse(path=str(file_path), filename=filename)
    return {"error": "Recording not found"}


app.include_router(router, prefix="/api")
