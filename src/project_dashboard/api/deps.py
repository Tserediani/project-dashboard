import uuid
from typing import Annotated

import aioboto3
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from project_dashboard.core.config import CONFIG
from project_dashboard.core.exceptions import (
    InvalidTokenError,
    NotFoundError,
    PermissionDeniedError,
)
from project_dashboard.core.interfaces.storage_interface import StorageService
from project_dashboard.core.security import decode_access_token
from project_dashboard.db.session import get_session
from project_dashboard.models import ProjectAccess, ProjectRole, User
from project_dashboard.repositories.documents_repository import DocumentRepository
from project_dashboard.repositories.project_access_repository import (
    ProjectAccessRepository,
)
from project_dashboard.repositories.project_repository import ProjectRepository
from project_dashboard.repositories.user_repository import UserRepository
from project_dashboard.services.document_service import DocumentService
from project_dashboard.services.project_service import ProjectService
from project_dashboard.services.s3_storage_service import S3StorageService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    user_id = decode_access_token(token)
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise InvalidTokenError()
    return user


async def get_project_access(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectAccess:
    access_repo = ProjectAccessRepository(session)
    access = await access_repo.get(project_id=project_id, user_id=current_user.id)
    if access is None:
        raise NotFoundError("Project not found")
    return access


async def get_document_access(
    document_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectAccess:
    document_repo = DocumentRepository(session=session)

    document = await document_repo.get_by_id(document_id)
    if document is None:
        raise NotFoundError("Document not found")

    access_repo = ProjectAccessRepository(session=session)
    access = await access_repo.get(
        project_id=document.project_id, user_id=current_user.id
    )
    if access is None:
        raise NotFoundError("Document not found")
    return access


async def require_owner(
    access: Annotated[ProjectAccess, Depends(get_project_access)],
) -> ProjectAccess:
    if access.role != ProjectRole.OWNER:
        raise PermissionDeniedError("Only the project owner can perform this action")
    return access


def get_project_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectService:
    return ProjectService(
        user_repo=UserRepository(session),
        project_repo=ProjectRepository(session),
        project_access_repo=ProjectAccessRepository(session),
    )


def get_storage_service() -> StorageService:
    return S3StorageService(
        bucket_name=CONFIG.aws.s3_bucket,
        region_name=CONFIG.aws.region,
        session=aioboto3.Session(
            aws_access_key_id=CONFIG.aws.access_key_id,
            aws_secret_access_key=CONFIG.aws.secret_access_key,
        ),
    )


def get_document_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
) -> DocumentService:
    return DocumentService(
        document_repo=DocumentRepository(session=session),
        storage_service=storage_service,
    )
