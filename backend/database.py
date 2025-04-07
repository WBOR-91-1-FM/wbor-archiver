"""
Database configuration and connection handling.
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from utils.logging import configure_logging

logger = configure_logging(__name__)

load_dotenv()
try:
    DATABASE_URL = os.getenv("DATABASE_URL").strip()
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

__all__ = ["Base"]
