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

from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI()

ARCHIVE_BASE = Path("/archive")


@app.get("/")
def home():
    """
    Status check endpoint.
    """
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
