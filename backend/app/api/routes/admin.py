"""
Admin protected routes.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def home():
    """
    Admin status check endpoint.
    """
    return {"service": "WBOR Archiver ADMIN API", "status": "ok"}
