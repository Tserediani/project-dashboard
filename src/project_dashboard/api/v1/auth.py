from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from project_dashboard.db.session import get_session
from project_dashboard.repositories.user_repository import UserRepository
from project_dashboard.schemas.token import TokenResponse
from project_dashboard.schemas.user import RegisterRequest, UserRead
from project_dashboard.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=201,
    response_model=UserRead,
    summary="Register a new user",
)
async def register(
    payload: RegisterRequest, session: Annotated[AsyncSession, Depends(get_session)]
):
    """Create a new user account with the provided email and password."""
    service = AuthService(UserRepository(session))
    user = await service.register(payload.email, payload.password)
    await session.commit()
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in",
)
async def login(
    payload: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Authenticate a user using their email and password and return an access token."""
    service = AuthService(UserRepository(session))
    token = await service.authenticate(payload.username, payload.password)
    return TokenResponse(access_token=token, token_type="bearer")
