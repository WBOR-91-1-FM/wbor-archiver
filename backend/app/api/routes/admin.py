"""
Admin protected routes.

TODO: endpoints for:
- block/unblock recordings
"""

from app.config import settings
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


@router.get("/", dependencies=[Depends(verify_admin)])
def home():
    """
    Admin status check endpoint.
    """
    return {"service": "WBOR Archiver ADMIN API", "status": "ok"}
