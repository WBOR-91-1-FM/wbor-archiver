"""
The backend is connected to the archive file system (read-only) and
provides an endpoints to list and download recordings. For downloads
containing multiple segments, we concatenate them together into a single
gapless recording.

Absolute paths should not be used. Instead, use `ARCHIVE_BASE` to refer
to the archive root directory.

By default, public users are anonymous and have read-only access to the
archive. Administrators have full access to the archive and can perform
administrative tasks such as hiding recordings.

Admin users are identified by a secret token that is passed in the
`X-Admin-Token` header. This is defined in the `.env` file. The token is
used to authenticate admin users and is required for all admin routes.

Example usage:
```bash
curl -i -H "X-Admin-Token: changeme" http://localhost/api/admin/
```

NOTE: All routes are prefixed with `/api`.
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
    Start/stop the RabbitMQ consumer thread when the app starts/stops.
    """
    stop_event, consumer_thread = start_consumer_thread()
    yield
    stop_event.set()
    consumer_thread.join()


app = FastAPI(lifespan=lifespan, docs_url="/docs/", openapi_url="/openapi.json")
app.include_router(api_router)
