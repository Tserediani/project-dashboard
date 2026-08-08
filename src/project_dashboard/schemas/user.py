import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, ValidationInfo, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    repeat_password: str

    @field_validator("repeat_password")
    @classmethod
    def password_match(cls, value: str, info: ValidationInfo):
        if value != info.data["password"]:
            raise ValueError("Passwords do not match")
        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
