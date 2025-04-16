"""
Module to handle the processing of new recordings.

Processing includes:
- Computing the SHA-256 hash of the file.
- Storing segment metadata in the database.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from app.config import settings
from app.core import database
from app.core.logging import configure_logging
from app.models.segment import Segment
from app.utils.ffprobe import probe as get_ffprobe_output
from app.utils.hash import hash_file

logger = configure_logging(__name__)


def parse_timestamp(timestamp: Dict) -> datetime:
    """
    Convert a timestamp dict into a Python datetime.
    """
    return datetime(
        year=int(timestamp["year"]),
        month=int(timestamp["month"]),
        day=int(timestamp["day"]),
        hour=int(timestamp["hour"]),
        minute=int(timestamp["minute"]),
        second=int(timestamp["second"]),
    )


def build_expected_filename(timestamp: Dict) -> str:
    """
    Build the expected filename based on the provided timestamp.
    """
    return (
        f"WBOR-{timestamp['year']}-{timestamp['month']}-{timestamp['day']}"
        f"T{timestamp['hour']}:{timestamp['minute']}:{timestamp['second']}Z.mp3"
    )


def extract_ffprobe_metadata(ffprobe_data: dict) -> dict:
    """
    Extract relevant metadata from the ffprobe output.
    """
    stream = ffprobe_data["streams"][0] if ffprobe_data.get("streams") else {}
    format_info = ffprobe_data.get("format", {})
    tags = stream.get("tags", {})
    format_tags = format_info.get("tags", {})

    return {
        # Use whichever bit_rate we find, typically stream or format
        "bit_rate": stream.get("bit_rate") or format_info.get("bit_rate"),
        "sample_rate": stream.get("sample_rate"),
        # Pull from format_tags first, then stream.tags as fallback
        "icy_br": format_tags.get("icy-br") or tags.get("icy-br"),
        "icy_genre": format_tags.get("icy-genre") or tags.get("icy-genre"),
        "icy_name": format_tags.get("icy-name") or tags.get("icy-name"),
        "icy_url": format_tags.get("icy-url") or tags.get("icy-url"),
        # Prefer the format-level encoder (e.g., "Lavf59.27.100")
        "encoder": format_tags.get("encoder") or tags.get("encoder"),
        # Duration in seconds (str -> float)
        # No fallback as there should always be a duration
        "duration": float(format_info.get("duration")),
    }


def process_new_recording(
    filename: str,
    timestamp: Dict,
    archive_base: Path = settings.ARCHIVE_BASE,
) -> None:
    """
    Validate and process a new recording.
    """
    expected_filename = build_expected_filename(timestamp)
    if filename != expected_filename:
        logger.error(
            "Filename mismatch: got `%s`, expected `%s`", filename, expected_filename
        )
        return

    file_path = (
        archive_base
        / timestamp["year"]
        / timestamp["month"]
        / timestamp["day"]
        / filename
    )

    if not file_path.exists():
        logger.error("File not found at expected path: `%s`", file_path)
        return

    sha256 = hash_file(str(file_path))
    ffprobe_data = get_ffprobe_output(str(file_path))
    if not ffprobe_data:
        logger.error("ffprobe failed for file `%s`", file_path)
        return

    dt_start = parse_timestamp(timestamp)
    metadata = extract_ffprobe_metadata(ffprobe_data)

    duration = metadata.pop("duration")
    dt_end = dt_start + timedelta(seconds=duration) if duration else None

    segment = Segment(
        filename=filename,
        archived_path=str(file_path),
        start_ts=dt_start,
        end_ts=dt_end,  # e.g. 4:34:53.9902 if ~5 minutes
        sha256_hash=sha256,
        **metadata,  # bit_rate, sample_rate, etc.
    )

    db = database.SessionLocal()
    try:
        db.add(segment)
        db.commit()
        logger.info("Successfully inserted new segment: `%s`", filename)
    except Exception as ex:  # pylint: disable=broad-except
        db.rollback()
        logger.error("DB insert failed for `%s`: %s", filename, ex)
    finally:
        db.close()
