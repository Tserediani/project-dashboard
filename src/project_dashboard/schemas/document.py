import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl
from pydantic.config import ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    uploaded_by: uuid.UUID | None
    filename: Annotated[str, Field(min_length=1, max_length=255)]
    s3_key: str
    content_type: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime


class DocumentUpdate(BaseModel):
    filename: Annotated[str | None, Field(min_length=1, max_length=255)] = None


class DocumentDownloadUrl(BaseModel):
    url: HttpUrl
    expires_in: Annotated[int, Field(gt=0)]
