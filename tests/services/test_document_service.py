import uuid  # noqa: I001
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from project_dashboard.core.exceptions import (
    NotFoundError,
    PayloadTooLargeError,
)
from project_dashboard.core.interfaces.storage_interface import StorageService
from project_dashboard.repositories.documents_repository import (
    DocumentRepository,
)
from project_dashboard.services.document_service import DocumentService
from project_dashboard.core.config import CONFIG


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


@pytest.mark.asyncio
async def test_upload_document_uploads_document_and_metadata(
    document_service: DocumentService,
    document_repo: AsyncMock,
    storage_service: AsyncMock,
    fake_document: MagicMock,
):
    mock_document = AsyncMock(id=fake_document.id, s3_key=fake_document.s3_key)

    document_repo.sum_size_by_project.return_value = 0

    document_repo.add.return_value = mock_document

    with patch("project_dashboard.services.document_service.uuid.uuid4") as mock_uuid:
        mock_uuid.return_value = fake_document.id

        result = await document_service.upload_document(
            project_id=fake_document.project_id,
            uploaded_by=fake_document.uploaded_by,
            content=fake_document.content,
            content_type=fake_document.content_type,
            filename=fake_document.filename,
        )

        document_repo.sum_size_by_project.assert_awaited_once_with(
            project_id=fake_document.project_id
        )

        storage_service.upload.assert_awaited_once_with(
            key=fake_document.s3_key,
            content=fake_document.content,
            content_type=fake_document.content_type,
        )

        document_repo.add.assert_awaited_once_with(
            project_id=fake_document.project_id,
            uploaded_by=fake_document.uploaded_by,
            filename=fake_document.filename,
            s3_key=fake_document.s3_key,
            content_type=fake_document.content_type,
            size_bytes=fake_document.size_bytes,
        )

        assert result == mock_document


@pytest.mark.parametrize(
    "project_storage_bytes",
    (
        CONFIG.document.max_project_storage_bytes + 1,
        CONFIG.document.max_project_storage_bytes + 1000,
    ),
)
async def test_upload_document_raises_payload_too_large_error_when_file_exceeds_total_size(
    document_service: DocumentService,
    document_repo: AsyncMock,
    storage_service: AsyncMock,
    fake_document: MagicMock,
    project_storage_bytes: int,
):
    document_repo.sum_size_by_project.return_value = project_storage_bytes

    with pytest.raises(PayloadTooLargeError):
        await document_service.upload_document(
            project_id=fake_document.project_id,
            uploaded_by=fake_document.uploaded_by,
            content=fake_document.content,
            content_type=fake_document.content_type,
            filename=fake_document.filename,
        )
    storage_service.upload.assert_not_awaited()
    document_repo.add.assert_not_awaited()


async def test_get_download_url_return_valid_url(
    document_repo: AsyncMock,
    storage_service: AsyncMock,
    document_service: DocumentService,
    fake_document: MagicMock,
):
    document_repo.get_by_id.return_value = AsyncMock(
        id=fake_document.id, s3_key=fake_document.s3_key
    )
    storage_service.generate_presigned_url.return_value = "fake_url"
    url = await document_service.get_download_url(
        document_id=fake_document.id, expires_in=300
    )

    document_repo.get_by_id.assert_awaited_once_with(document_id=fake_document.id)
    storage_service.generate_presigned_url.assert_awaited_once_with(
        fake_document.s3_key, 300
    )
    assert url == "fake_url"


async def test_get_download_url_raises_not_found_error_when_document_not_exists(
    document_repo: AsyncMock,
    storage_service: AsyncMock,
    document_service: DocumentService,
    fake_document: MagicMock,
):
    document_repo.get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        await document_service.get_download_url(
            document_id=fake_document.id, expires_in=300
        )
    storage_service.generate_presigned_url.assert_not_awaited()


async def test_replace_document_replaces_document_and_document_metadata(
    document_repo: AsyncMock,
    storage_service: AsyncMock,
    document_service: DocumentService,
    fake_document: MagicMock,
):
    document_repo.get_by_id.return_value = fake_document
    document_repo.sum_size_by_project.return_value = fake_document.size_bytes
    document_repo.update_document.return_value = AsyncMock(filename="new-filename.txt")

    document = await document_service.replace_document(
        fake_document.id,
        b"new-content",
        fake_document.content_type,
        "new-filename.txt",
    )

    assert document.filename == "new-filename.txt"

    document_repo.get_by_id.assert_awaited_once_with(fake_document.id)
    document_repo.sum_size_by_project.assert_awaited_once_with(
        project_id=fake_document.project_id
    )
    storage_service.upload.assert_awaited_once_with(
        key=fake_document.s3_key,
        content=b"new-content",
        content_type=fake_document.content_type,
    )
    document_repo.update_document.assert_awaited_once_with(
        fake_document,
        filename="new-filename.txt",
        content_type=fake_document.content_type,
        size_bytes=len(b"new-content"),
    )


async def test_replace_document_raises_not_found_error_when_document_not_exists(
    document_repo: AsyncMock,
    storage_service: AsyncMock,
    document_service: DocumentService,
    fake_document: MagicMock,
):
    document_repo.get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        await document_service.replace_document(
            document_id=fake_document.id,
            content=fake_document.content,
            content_type=fake_document.content_type,
            filename=fake_document.filename,
        )
    storage_service.upload.assert_not_awaited()
    document_repo.add.assert_not_awaited()


@pytest.mark.parametrize(
    "project_storage_bytes",
    (
        CONFIG.document.max_project_storage_bytes + 1,
        CONFIG.document.max_project_storage_bytes + 1000,
    ),
)
async def test_replace_document_raises_payload_too_large_error_when_file_exceeds_total_size(
    document_repo: AsyncMock,
    storage_service: AsyncMock,
    document_service: DocumentService,
    fake_document: MagicMock,
    project_storage_bytes: int,
):
    document_repo.get_by_id.return_value = fake_document
    document_repo.sum_size_by_project.return_value = project_storage_bytes

    with pytest.raises(PayloadTooLargeError):
        await document_service.replace_document(
            document_id=fake_document.id,
            content=fake_document.content,
            content_type=fake_document.content_type,
            filename=fake_document.filename,
        )
    storage_service.upload.assert_not_awaited()
    document_repo.add.assert_not_awaited()


async def test_update_document_metadata_updates_document_metadata(
    document_repo: AsyncMock,
    document_service: DocumentService,
    fake_document: MagicMock,
):
    document_repo.get_by_id.return_value = fake_document
    document_repo.update_document.return_value = AsyncMock(filename="new-filename.txt")

    document = await document_service.update_document_metadata(
        document_id=fake_document.id, filename="new-filename.txt"
    )

    assert document.filename == "new-filename.txt"

    document_repo.get_by_id.assert_awaited_once_with(fake_document.id)
    document_repo.update_document.assert_awaited_once_with(
        fake_document, filename="new-filename.txt"
    )


async def test_update_document_metadata_raises_not_found_error_when_document_not_exists(
    document_repo: AsyncMock,
    document_service: DocumentService,
    fake_document: MagicMock,
):
    document_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await document_service.update_document_metadata(
            document_id=fake_document.id, filename="fail.txt"
        )

    document_repo.update_document.assert_not_called()


async def test_delete_document_deletes_document_and_document_metadata(
    document_repo: AsyncMock,
    document_service: DocumentService,
    storage_service: AsyncMock,
    fake_document: MagicMock,
):
    document_repo.get_by_id.return_value = fake_document

    await document_service.delete_document(document_id=fake_document.id)

    document_repo.get_by_id.assert_awaited_once_with(document_id=fake_document.id)
    storage_service.delete.assert_awaited_once_with(fake_document.s3_key)
    document_repo.delete.assert_awaited_once_with(fake_document)


async def test_delete_document_raises_not_found_error_when_document_not_exists(
    document_repo: AsyncMock,
    document_service: DocumentService,
    storage_service: AsyncMock,
    fake_document: MagicMock,
):
    document_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await document_service.delete_document(document_id=fake_document.id)

    document_repo.get_by_id.assert_awaited_once_with(document_id=fake_document.id)
    storage_service.delete.assert_not_awaited()
    document_repo.delete.assert_not_awaited()


@pytest.mark.parametrize(
    "fake_documents", ([], [MagicMock(id=uuid.uuid4()), MagicMock(id=uuid.uuid4())])
)
async def test_list_by_project_returns_list_of_projects(
    document_repo: AsyncMock,
    document_service: DocumentService,
    fake_documents: MagicMock,
):
    document_repo.list_by_project.return_value = fake_documents

    documents = await document_service.list_by_project(uuid.uuid4())

    assert documents == fake_documents
