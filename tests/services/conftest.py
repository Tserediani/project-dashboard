import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from project_dashboard.core.interfaces.storage_interface import StorageService
from project_dashboard.models import Project, User
from project_dashboard.repositories.documents_repository import DocumentRepository
from project_dashboard.repositories.project_access_repository import (
    ProjectAccessRepository,
)
from project_dashboard.repositories.project_repository import ProjectRepository
from project_dashboard.repositories.user_repository import UserRepository
from project_dashboard.services.document_service import DocumentService
from project_dashboard.services.project_service import ProjectService


@pytest.fixture
def project_repo() -> AsyncMock:
    return AsyncMock(spec=ProjectRepository)


@pytest.fixture
def project_access_repo() -> AsyncMock:
    return AsyncMock(spec=ProjectAccessRepository)


@pytest.fixture
def user_repo() -> AsyncMock:
    return AsyncMock(spec=UserRepository)


@pytest.fixture
def project_service(
    project_repo: AsyncMock,
    project_access_repo: AsyncMock,
    user_repo: AsyncMock,
) -> ProjectService:
    return ProjectService(project_repo, user_repo, project_access_repo)


@pytest.fixture
def owner() -> MagicMock:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    return user


@pytest.fixture
def fake_project() -> MagicMock:
    project = MagicMock(spec=Project)
    project.id = uuid.uuid4()
    project.name = "My Project"
    project.description = "Some Description"
    return project


@pytest.fixture
def document_repo() -> AsyncMock:
    return AsyncMock(spec=DocumentRepository)


@pytest.fixture
def storage_service() -> AsyncMock:
    return AsyncMock(spec=StorageService)


@pytest.fixture
def document_service(
    document_repo: AsyncMock, storage_service: AsyncMock
) -> DocumentService:
    return DocumentService(document_repo=document_repo, storage_service=storage_service)


@pytest.fixture
def fake_document() -> MagicMock:
    id = uuid.uuid4()
    project_id = uuid.uuid4()
    uploaded_by = uuid.uuid4()
    content = b"test content"
    return MagicMock(
        id=id,
        project_id=project_id,
        uploaded_by=uploaded_by,
        filename="test.txt",
        content_type="test/plain",
        s3_key=f"projects/{project_id}/documents/{id}",
        content=content,
        size_bytes=len(content),
    )
