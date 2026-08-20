from unittest.mock import AsyncMock

import pytest

from project_dashboard.core.exceptions import ConflictError, PermissionDeniedError
from project_dashboard.core.security import hash_password
from project_dashboard.services.auth_service import AuthService


async def test_register_creates_user_when_email_not_taken(
    auth_service: AuthService, user_repo: AsyncMock
):
    user_repo.get_by_email.return_value = None
    user_repo.create.return_value = AsyncMock(id="new-id", email="test@example.com")

    user = await auth_service.register("test@example.com", "password!123")

    user_repo.create.assert_called_once()
    assert user.email == "test@example.com"


async def test_register_raises_conflict_error_when_email_taken(
    auth_service: AuthService, user_repo: AsyncMock
):
    user_repo.get_by_email.return_value = AsyncMock()

    with pytest.raises(ConflictError):
        await auth_service.register("test@example.com", "password!123")
    user_repo.create.assert_not_called()


async def test_authenticate_succeeds_with_correct_password(
    auth_service: AuthService, user_repo: AsyncMock
):
    fake_user = AsyncMock()
    fake_user.hashed_password = hash_password("password!123")

    user_repo.get_by_email.return_value = fake_user

    token = await auth_service.authenticate("test@example.com", "password!123")
    assert isinstance(token, str)


async def test_authenticate_raises_permission_denied_error_with_wrong_password(
    auth_service: AuthService, user_repo: AsyncMock
):
    fake_user = AsyncMock()
    fake_user.hashed_password = hash_password("password!123")

    user_repo.get_by_email.return_value = fake_user

    with pytest.raises(PermissionDeniedError):
        await auth_service.authenticate("test@example.com", "wrong-password")


async def test_authenticate__raises_permission_denied_error_when_user_not_found(
    auth_service: AuthService, user_repo: AsyncMock
):
    user_repo.get_by_email.return_value = None

    with pytest.raises(PermissionDeniedError):
        await auth_service.authenticate("test@example.com", "wrong-password")
