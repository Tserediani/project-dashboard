from pydantic import EmailStr

from project_dashboard.core.exceptions import ConflictError, PermissionDeniedError
from project_dashboard.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from project_dashboard.models import User
from project_dashboard.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def register(self, email: EmailStr, password: str) -> User:
        existing = await self.user_repository.get_by_email(email)
        if existing:
            raise ConflictError("Email is already taken.")
        return await self.user_repository.create(email, hash_password(password))

    async def authenticate(self, email: EmailStr, password: str) -> str:
        user = await self.user_repository.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise PermissionDeniedError("Invalid credentials")
        return create_access_token(subject=str(user.id))
