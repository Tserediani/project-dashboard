import uuid
from datetime import datetime

from pydantic import BaseModel
from pydantic.config import ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    uploaded_by: uuid.UUID | None
    filename: str
    s3_key: str
    content_type: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime


class DocumentUpdate(BaseModel):
    filename: str | None = None


class DocumentDownloadUrl(BaseModel):
    url: str
    expires_in: int
