"""
API routes for handling recordings.
"""

from datetime import datetime

from app.config import settings
from app.core.database import get_db
from app.models.segment import Segment
from app.schemas.recording import SegmentPublic
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

router = APIRouter(tags=["Recordings"])


@router.get("/recordings", tags=["List"])
def list_recordings():
    """
    List all recordings in the archive.
    """
    # Simple example: list all .mp3 files in /archive
    recordings = list(settings.ARCHIVE_BASE.glob("**/*.mp3"))
    return {"count": len(recordings), "files": [str(r) for r in recordings]}


@router.get("/download/{year}/{month}/{day}/{filename}", tags=["Download"])
def download_recording(year: str, month: str, day: str, filename: str):
    """
    Download a recording from the archive.
    """
    file_path = settings.ARCHIVE_BASE / year / month / day / filename
    if file_path.exists():
        return FileResponse(path=str(file_path), filename=filename)
    return {"error": "Recording not found"}


@router.get("/segments", response_model=list[SegmentPublic])
def get_segments_in_range(
    start_time: datetime = Query(..., description="Start of the desired time range"),
    end_time: datetime = Query(..., description="End of the desired time range"),
    db: Session = Depends(get_db),
):
    """
    Return all Segments that intersect with [start_time, end_time).
    Since end_ts is never null, a simple coverage query suffices.
    """
    segments = (
        db.query(Segment)
        .filter(
            Segment.start_ts < end_time,
            Segment.end_ts > start_time,
        )
        .all()
    )

    return segments
