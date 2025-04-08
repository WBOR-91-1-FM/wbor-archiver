"""
API routes for handling recordings.
"""

from app.config import settings
from fastapi import APIRouter
from fastapi.responses import FileResponse

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
