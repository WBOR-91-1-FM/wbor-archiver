"""
Database configuration and connection handling.
"""

import os
import sys

from app.core.logging import configure_logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

logger = configure_logging(__name__)

load_dotenv()
try:
    POSTGRES_HOST = os.getenv("POSTGRES_HOST").strip()
    POSTGRES_PORT = os.getenv("POSTGRES_PORT").strip()
    POSTGRES_DB = os.getenv("POSTGRES_DB").strip()
    POSTGRES_USER = os.getenv("POSTGRES_USER").strip()
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD").strip()

    DATABASE_URL = (
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
except (ValueError, AttributeError, TypeError) as e:
    logger.error("Failed to load environment variables: `%s`", e)
    sys.exit(1)

# Base for models
Base = declarative_base()

engine = create_engine(
    DATABASE_URL,
    # `pool_pre_ping` checks that the DB connection is alive before using
    pool_pre_ping=True,
    # `echo=True` logs SQL to stdout (optional, but handy for debugging)
    echo=False,
)

# Create the session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency to get a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = ["Base"]
