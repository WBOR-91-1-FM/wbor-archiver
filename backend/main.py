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
