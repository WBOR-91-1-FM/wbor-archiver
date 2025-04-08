"""
App-wide settings.
"""

import os
from pathlib import Path

import pytz
from dotenv import load_dotenv

load_dotenv()


class Settings:  # pylint: disable=too-few-public-methods
    """
    Application settings loaded from environment variables.
    """

    TZ = pytz.UTC
    STATION_ID = os.getenv("STATION_ID").strip()
    STREAM_URL = os.getenv("STREAM_URL").strip()
    ARCHIVE_DIR = os.getenv("ARCHIVE_DIR").strip()
    ARCHIVE_BASE = Path(ARCHIVE_DIR)
    UNMATCHED_DIR = os.getenv("UNMATCHED_DIR").strip()
    SEGMENT_DURATION_SECONDS = int(os.getenv("SEGMENT_DURATION_SECONDS").strip())

    BACKEND_APP_PASS = os.getenv("BACKEND_APP_PASS").strip()

    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST").strip()
    RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE").strip()
    RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE").strip()

    POSTGRES_HOST = os.getenv("POSTGRES_HOST").strip()
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT").strip())
    POSTGRES_DB = os.getenv("POSTGRES_DB").strip()
    POSTGRES_USER = os.getenv("POSTGRES_USER").strip()
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD").strip()

    DATABASE_URL = (
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )


settings = Settings()
