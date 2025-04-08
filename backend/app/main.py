"""
The backend is connected to the archive file system (as read-only) and
provides an API to list and download recordings. As needed (determined
by the request), concatenation of multiple files into a single download
is supported for gapless playback across a given time range.

Processing includes:
- Computing the SHA-256 hash of the file.
- Storing the metadata in the database.

Absolute paths should not be used. Instead, use `ARCHIVE_BASE` to refer
to the archive root directory.

By default, public users are anonymous and have read-only access to the
archive. Administrators have full access to the archive and can perform
administrative tasks such as hiding recordings.

Admin users are identified by a secret token that is passed in the
`X-Admin-Token` header. An admin user table is stored in the database,
which maps tokens to user IDs. An endpoint is provided to add new admin
users, provided a super-admin token is passed in the
`X-Super-Admin-Token` header (which is hardcoded in the service).

NOTE: All routes are prefixed with `/api`.

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

from app.api.routes.admin import router as admin_router
from app.api.routes.health import router as health_router
from app.api.routes.recordings import router as recordings_router
from app.core.rabbitmq import start_consumer_thread
from fastapi import APIRouter, FastAPI

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(recordings_router)
api_router.include_router(admin_router, prefix="/admin")


def lifespan(_app: FastAPI):
    """
    Start/stop the RabbitMQ consumer thread when the FastAPI app
    starts/stops.
    """
    stop_event, consumer_thread = start_consumer_thread()
    yield
    stop_event.set()
    consumer_thread.join()


app = FastAPI(lifespan=lifespan)
app.include_router(api_router)
