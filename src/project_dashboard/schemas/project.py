import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field
from pydantic.config import ConfigDict


class ProjectCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: Annotated[str | None, Field(max_length=1000)] = None


class ProjectUpdate(BaseModel):
    name: Annotated[str | None, Field(min_length=1, max_length=100)] = None
    description: Annotated[str | None, Field(max_length=1000)] = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class InviteRequest(BaseModel):
    email: EmailStr
