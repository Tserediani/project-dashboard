import uuid  # noqa: I001
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from project_dashboard.core.exceptions import (
    NotFoundError,
    PayloadTooLargeError,
    UnsupportedDocumentTypeError,
)
from project_dashboard.services.document_service import DocumentService
from project_dashboard.core.config import CONFIG


@pytest.mark.parametrize(
    "content_type",
    (
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
)
async def test_upload_document_uploads_document_and_metadata(
    document_service: DocumentService,
    document_repo: AsyncMock,
    storage_service: AsyncMock,
    fake_document: MagicMock,
    project_repo: AsyncMock,
    content_type: str,
):
    mock_document = AsyncMock(id=fake_document.id, s3_key=fake_document.s3_key)
    fake_document.content_type = content_type
    project_repo.get_for_update.return_value = AsyncMock()

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
        project_repo.get_for_update.assert_awaited_once_with(fake_document.project_id)

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
    "content_type", ("text/plain", "image/png", "application/json")
)
async def test_upload_document_raises_unsupported_content_type_when_documents_type_is_not_in_allowed_list(
    document_service: DocumentService,
    document_repo: AsyncMock,
    storage_service: AsyncMock,
    project_repo: AsyncMock,
    content_type: str,
):
    with pytest.raises(UnsupportedDocumentTypeError):
        await document_service.upload_document(
            project_id=uuid.uuid4(),
            uploaded_by=uuid.uuid4(),
            content=b"content",
            content_type=content_type,
            filename="invalid.txt",
        )
    project_repo.get_for_update.assert_not_called()
    document_repo.sum_size_by_project.assert_not_called()
    storage_service.upload.assert_not_called()
    document_repo.add.assert_not_called()


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


@pytest.mark.parametrize(
    "content_type",
    (
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
)
async def test_replace_document_replaces_document_and_document_metadata(
    document_repo: AsyncMock,
    storage_service: AsyncMock,
    document_service: DocumentService,
    fake_document: MagicMock,
    content_type: str,
):
    document_repo.get_by_id.return_value = fake_document
    document_repo.sum_size_by_project.return_value = fake_document.size_bytes
    document_repo.update_document.return_value = AsyncMock(filename="new-filename.txt")
    new_uuid = uuid.uuid4()
    new_s3_key = f"projects/{fake_document.project_id}/documents/{new_uuid}"
    with patch("project_dashboard.services.document_service.uuid.uuid4") as mock_uuid:
        mock_uuid.return_value = new_uuid

        document = await document_service.replace_document(
            fake_document.id,
            b"new-content",
            content_type,
            "new-filename.txt",
        )

        assert document.filename == "new-filename.txt"

        document_repo.get_by_id.assert_awaited_once_with(fake_document.id)
        document_repo.sum_size_by_project.assert_awaited_once_with(
            project_id=fake_document.project_id
        )
        storage_service.upload.assert_awaited_once_with(
            key=new_s3_key,
            content=b"new-content",
            content_type=content_type,
        )
        document_repo.update_document.assert_awaited_once_with(
            fake_document,
            s3_key=new_s3_key,
            filename="new-filename.txt",
            content_type=content_type,
            size_bytes=len(b"new-content"),
        )
        storage_service.delete.assert_awaited_once_with(
            key=fake_document.s3_key,
        )


@pytest.mark.parametrize(
    "content_type", ("text/plain", "image/png", "application/json")
)
async def test_replace_document_raises_unsupported_content_type_when_documents_type_is_not_in_allowed_list(
    document_service: DocumentService,
    document_repo: AsyncMock,
    storage_service: AsyncMock,
    project_repo: AsyncMock,
    content_type: str,
):
    with pytest.raises(UnsupportedDocumentTypeError):
        await document_service.replace_document(
            document_id=uuid.uuid4(),
            content=b"content",
            content_type=content_type,
            filename="invalid.txt",
        )
    project_repo.get_for_update.assert_not_called()
    document_repo.sum_size_by_project.assert_not_called()
    storage_service.upload.assert_not_called()
    document_repo.add.assert_not_called()


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
