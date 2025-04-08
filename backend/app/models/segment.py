"""
Segment model for the archive.
This model represents a recording segment (file) in the archive.
"""

from app.core.database import Base
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, text
from sqlalchemy.orm import relationship


class Segment(Base):  # pylint: disable=too-few-public-methods
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
