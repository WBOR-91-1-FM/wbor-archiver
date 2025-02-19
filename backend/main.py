"""
Backend is connected to the archive file system (as read-only) and provides an API to list and download recordings.

Metadata (outside of what is provided in the filename) is stored in a separate database.

The watchdog service is responsible for moving files from the temporary directory to the archive directory once they are fully uploaded.
This service will tell us when a new file is available to be processed. Processing includes:
- Computing the SHA-256 hash of the file.
- Parsing the filename to extract metadata.
- Storing the metadata in the database.

Absolute paths should not be used. Instead, use the `ARCHIVE_BASE` constant to refer to the archive root directory.

By default, public users are anonymous and have read-only access to the archive. No authentication is required.
Administrators have full access to the archive and can perform administrative tasks such as hiding recordings.

Admin users are identified by a secret token that is passed in the `X-Admin-Token` header. An admin user table
is stored in the database, which maps tokens to user IDs. An endpoint is provided to add new admin users, provided
a super-admin token is passed in the `X-Super-Admin-Token` header (which is hardcoded in the service).
"""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI()

ARCHIVE_BASE = Path("/archive")


@app.get("/")
def home():
    return {"service": "WBOR Archiver API", "status": "ok"}


@app.get("/recordings")
def list_recordings():
    # Simple example: list all .mp3 files in /archive
    recordings = list(ARCHIVE_BASE.glob("**/*.mp3"))
    # Return minimal data for demonstration
    return {"count": len(recordings), "files": [str(r) for r in recordings]}


@app.get("/download/{year}/{month}/{day}/{filename}")
def download_recording(year: str, month: str, day: str, filename: str):
    file_path = ARCHIVE_BASE / year / month / day / filename
    if file_path.exists():
        return FileResponse(path=str(file_path), filename=filename)
    return {"error": "Recording not found"}
