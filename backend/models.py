"""
Define the database models for the application.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    text,
)
from sqlalchemy.orm import relationship
from database import Base


class Segment(Base):
    """
    Represents a recording segment (file) in the archive.
    """

    __tablename__ = "segments"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(
        String, unique=True, nullable=False
    )  # e.g. "WBOR-2025-02-14T00:35:01Z.mp3"
    archived_path = Column(
        Text, nullable=False
    )  # Full path to where the file is stored
    start_ts = Column(DateTime(timezone=True), nullable=False)  # When recording started
    end_ts = Column(DateTime(timezone=True))  # When recording ended (if known)
    is_published = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )

    # Additional metadata fields (SHA-256, ffprobe output, etc.)
    sha256_hash = Column(String, nullable=True)
    bit_rate = Column(String, nullable=True)
    sample_rate = Column(String, nullable=True)
    icy_br = Column(String, nullable=True)
    icy_genre = Column(String, nullable=True)
    icy_name = Column(String, nullable=True)
    icy_url = Column(String, nullable=True)
    encoder = Column(String, nullable=True)

    # Relationship to logs
    download_logs = relationship("DownloadLog", back_populates="segment")


class DownloadLog(Base):
    """
    Mirrors the 'download_logs' table from init.sql.
    Tracks whenever a segment is downloaded / played back.
    """

    __tablename__ = "download_logs"

    id = Column(Integer, primary_key=True, index=True)
    segment_id = Column(Integer, ForeignKey("segments.id"), nullable=False)
    downloaded_at = Column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    # Relationship back to Segment
    segment = relationship("Segment", back_populates="download_logs")
