import uuid
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: Annotated[
        str,
        Field(min_length=8, description="Password must contain at least 8 characters."),
    ]
    repeat_password: Annotated[
        str,
        Field(min_length=8),
    ]

    @model_validator(mode="after")
    def password_match(self) -> RegisterRequest:
        if self.password != self.repeat_password:
            raise ValueError("Passwords do not match")
        return self


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
