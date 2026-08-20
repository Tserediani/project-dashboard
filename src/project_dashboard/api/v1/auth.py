from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from project_dashboard.api.deps import get_auth_service
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
    payload: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    user = await auth_service.register(payload.email, payload.password)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in",
)
async def login(
    payload: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    token = await auth_service.authenticate(payload.username, payload.password)
    return TokenResponse(access_token=token, token_type="bearer")
