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

    ARCHIVE_DIR = os.getenv("ARCHIVE_DIR").strip()
    UNMATCHED_DIR = os.getenv("UNMATCHED_DIR").strip()
    SEGMENT_DURATION_SECONDS = int(os.getenv("SEGMENT_DURATION_SECONDS").strip())
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST").strip()
    RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE").strip()
    RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE").strip()
    TZ = pytz.UTC

    ARCHIVE_BASE = Path(ARCHIVE_DIR)


settings = Settings()
