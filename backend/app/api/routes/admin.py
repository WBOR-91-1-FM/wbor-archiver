"""
Admin protected routes.
"""

from app.config import Uptime, settings
from fastapi import APIRouter, Depends, Header, HTTPException

router = APIRouter()


def verify_admin(x_admin_token: str = Header(...)):
    """
    Naive admin token verification.
    """
    valid_admin_token = settings.BACKEND_APP_PASS
    if x_admin_token != valid_admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    return True


@router.get("/uptime")
def uptime():
    """
    Returns the uptime of the backend service.
    """
    return {"uptime": Uptime.get_uptime()}


@router.get("/most_recent")
def most_recent():
    """
    Returns the timestamp of the most recent file in the archive directory.
    """
    return "TODO: Implement most recent file retrieval"
    # most_recent_file = max(
    #     settings.ARCHIVE_BASE.glob("*.mp3"), key=lambda f: f.stat().st_mtime
    # )
    # return {
    #     "most_recent": most_recent_file.name,
    #     "timestamp": most_recent_file.stat().st_mtime,
    # }


@router.get("/", dependencies=[Depends(verify_admin)])
def home():
    """
    Admin status check endpoint.
    """
    return {"service": "WBOR Archiver ADMIN API", "status": "ok"}
