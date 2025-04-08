"""
Health check.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def home():
    """
    Status check endpoint.
    """
    return {"service": "WBOR Archiver API", "status": "ok"}
