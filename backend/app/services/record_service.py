"""
Module to handle the processing of new recordings.
"""

from pathlib import Path
from typing import Dict

from app.core import database
from app.core.logging import configure_logging
from app.models.segment import Segment
from app.utils.ffprobe import probe as get_ffprobe_output
from app.utils.hash import hash_file

logger = configure_logging(__name__)


def process_new_recording(filename: str, timestamp: Dict, archive_base: Path) -> None:
    """
    Validate the file, compute hashes, gather metadata, and save a new
    record in the DB. This function encapsulates your "business logic"
    around newly-arrived recordings.
    """

    # Build the expected name, check if it matches
    expected = (
        f"WBOR-{timestamp.get('year')}-{timestamp.get('month')}-{timestamp.get('day')}"
        f"T{timestamp.get('hour')}:{timestamp.get('minute')}:{timestamp.get('second')}Z.mp3"
    )
    if filename != expected:
        logger.error(
            "Filename '%s' does not match expected format: '%s'", filename, expected
        )
        return

    # Construct the file path
    file_path = (
        archive_base
        / timestamp.get("year")
        / timestamp.get("month")
        / timestamp.get("day")
        / filename
    )

    # Compute hash and gather ffprobe data
    sha256_hash = hash_file(str(file_path))
    ffprobe = get_ffprobe_output(str(file_path))

    db = database.SessionLocal()
    try:
        new_rec = Segment(
            filename=filename,
            archived_path=str(file_path),
            start_ts=timestamp,
            sha256_hash=sha256_hash,
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
        logger.info("Successfully inserted new segment: %s", filename)
    except Exception as ex:  # pylint: disable=broad-except
        db.rollback()
        logger.error("Error inserting record for file '%s': %s", filename, ex)
    finally:
        db.close()
