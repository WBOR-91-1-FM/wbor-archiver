"""
Schemas for the Segment and DownloadLog models.

These schemas are used for data validation and serialization/
deserialization of the models when interacting with the API.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

# Segment Schemas --------------------------------------------------


class SegmentBase(BaseModel):
    filename: str
    archived_path: str
    start_ts: datetime
    end_ts: Optional[datetime] = None
    is_published: bool = True
    sha256_hash: Optional[str] = None
    bit_rate: Optional[str] = None
    sample_rate: Optional[str] = None
    icy_br: Optional[str] = None
    icy_genre: Optional[str] = None
    icy_name: Optional[str] = None
    icy_url: Optional[str] = None
    encoder: Optional[str] = None

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "filename": "WBOR-2025-02-14T00:35:01Z.mp3",
                "archived_path": "/archive/2025/02/14/WBOR-2025-02-14T00:35:01Z.mp3",
                "start_ts": "2025-02-14T00:35:01Z",
                "end_ts": "2025-02-14T00:40:01Z",
                "is_published": True,
                "sha256_hash": "abcdef1234567890",
                "bit_rate": "128k",
                "sample_rate": "44100",
                "icy_br": "128",
                "icy_genre": "News",
                "icy_name": "WBOR News",
                "icy_url": "https://wbor.org",
                "encoder": "LAME",
            }
        }


class SegmentCreate(SegmentBase):
    pass


class SegmentUpdate(BaseModel):
    filename: Optional[str] = None
    archived_path: Optional[str] = None
    start_ts: Optional[datetime] = None
    end_ts: Optional[datetime] = None
    is_published: Optional[bool] = None
    sha256_hash: Optional[str] = None
    bit_rate: Optional[str] = None
    sample_rate: Optional[str] = None
    icy_br: Optional[str] = None
    icy_genre: Optional[str] = None
    icy_name: Optional[str] = None
    icy_url: Optional[str] = None
    encoder: Optional[str] = None

    class Config:
        orm_mode = True


class SegmentPublic(SegmentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class SegmentsPublic(BaseModel):
    data: List[SegmentPublic]
    count: int

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "data": [
                    {
                        "id": 1,
                        "filename": "WBOR-2025-02-14T00:35:01Z.mp3",
                        "archived_path": "/archive/2025/02/14/WBOR-2025-02-14T00:35:01Z.mp3",
                        "start_ts": "2025-02-14T00:35:01Z",
                        "end_ts": "2025-02-14T00:40:01Z",
                        "is_published": True,
                        "sha256_hash": "abcdef1234567890",
                        "bit_rate": "128k",
                        "sample_rate": "44100",
                        "icy_br": "128",
                        "icy_genre": "News",
                        "icy_name": "WBOR News",
                        "icy_url": "https://wbor.org",
                        "encoder": "LAME",
                        "created_at": "2025-02-14T00:40:01Z",
                        "updated_at": "2025-02-14T00:40:01Z",
                    }
                ],
                "count": 1,
            }
        }


# DownloadLog Schemas ----------------------------------------------


class DownloadLogBase(BaseModel):
    segment_id: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "segment_id": 1,
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0",
            }
        }


class DownloadLogCreate(DownloadLogBase):
    pass


class DownloadLogPublic(DownloadLogBase):
    id: int
    downloaded_at: datetime

    class Config:
        orm_mode = True


class DownloadLogsPublic(BaseModel):
    data: List[DownloadLogPublic]
    count: int

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "data": [
                    {
                        "id": 1,
                        "segment_id": 1,
                        "downloaded_at": "2025-02-14T00:45:01Z",
                        "ip_address": "192.168.1.1",
                        "user_agent": "Mozilla/5.0",
                    }
                ],
                "count": 1,
            }
        }
