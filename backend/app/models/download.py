"""
Download model for the archive.
This model represents a download log entry for a recording Segment.
"""

from app.core.database import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import relationship


class DownloadLog(Base):  # pylint: disable=too-few-public-methods
    """
    Mirrors the 'download_logs' table from init.sql.
    Tracks whenever a Segment is downloaded / played back.
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
