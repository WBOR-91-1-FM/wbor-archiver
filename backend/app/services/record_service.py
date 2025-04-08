"""
Module to handle the processing of new recordings.

Processing includes:
- Computing the SHA-256 hash of the file.
- Storing the metadata in the database.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

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


def extract_ffprobe_metadata(ffprobe_data: dict) -> dict:
    """
    Extract bit_rate, sample_rate, and tag-based fields from ffprobe JSON.
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
        "duration": float(format_info.get("duration")),
    }


def process_new_recording(filename: str, timestamp: Dict, archive_base: Path) -> None:
    """
    Validate the file, compute hashes, gather metadata, and save a new
    record in the DB.
    """
    # Build the expected filename
    expected_filename = (
        f"WBOR-{timestamp['year']}-{timestamp['month']}-{timestamp['day']}"
        f"T{timestamp['hour']}:{timestamp['minute']}:{timestamp['second']}Z.mp3"
    )
    if filename != expected_filename:
        logger.error(
            "Filename `%s` does not match expected format: `%s`",
            filename,
            expected_filename,
        )
        return

    # Construct the file path
    file_path = (
        archive_base
        / timestamp["year"]
        / timestamp["month"]
        / timestamp["day"]
        / filename
    )

    # Compute hash and gather ffprobe data
    sha256_hash = hash_file(str(file_path))
    ffprobe_data = get_ffprobe_output(str(file_path))

    # Parse timestamp and ffprobe metadata
    dt_obj = parse_timestamp(timestamp)
    metadata = extract_ffprobe_metadata(ffprobe_data)

    # The nominal start_ts is exactly what's in the filename (dt_obj).
    # We can compute end_ts based on the duration from ffprobe.
    duration_seconds = metadata.pop("duration")
    end_dt = dt_obj + timedelta(seconds=duration_seconds) if duration_seconds else None

    db = database.SessionLocal()
    try:
        new_rec = Segment(
            filename=filename,
            archived_path=str(file_path),
            start_ts=dt_obj,  # e.g. 4:29:54 if that's the filename
            end_ts=end_dt,  # e.g. 4:34:53.9902 if ~5 minutes
            sha256_hash=sha256_hash,
            **metadata,  # bit_rate, sample_rate, etc.
        )
        db.add(new_rec)
        db.commit()
        logger.info("Successfully inserted new segment: `%s`", filename)
    except Exception as ex:  # pylint: disable=broad-except
        db.rollback()
        logger.error("Error inserting record for file `%s`: %s", filename, ex)
    finally:
        db.close()
