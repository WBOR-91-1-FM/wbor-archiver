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

import logging
import os
import sys
from pathlib import Path

import pytz
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from rabbitmq import start_consumer_thread
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


def lifespan(_app: FastAPI):
    """
    Start/stop the RabbitMQ consumer thread when the FastAPI app
    starts/stops.
    """
    stop_event, consumer_thread = start_consumer_thread(ARCHIVE_BASE)
    yield
    stop_event.set()
    consumer_thread.join()
    logger.info("RabbitMQ consumer thread has shut down cleanly.")


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
