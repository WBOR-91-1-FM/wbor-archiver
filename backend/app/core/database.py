"""
Database configuration and connection handling.
"""

from app.config import settings
from app.core.logging import configure_logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

logger = configure_logging(__name__)

# Base for models
Base = declarative_base()

engine = create_engine(
    settings.DATABASE_URL,
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
