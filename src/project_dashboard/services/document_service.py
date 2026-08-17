import mimetypes
import uuid

from project_dashboard.core.config import CONFIG
from project_dashboard.core.exceptions import (
    NotFoundError,
    PayloadTooLargeError,
)
from project_dashboard.core.interfaces.storage_interface import StorageService
from project_dashboard.models import Document
from project_dashboard.repositories.documents_repository import DocumentRepository


class DocumentService:
    def __init__(
        self,
        document_repo: DocumentRepository,
        storage_service: StorageService,
    ):
        self.document_repo = document_repo
        self.storage_service = storage_service

    async def _validate_storage_limit(
        self, project_id: uuid.UUID, new_size_bytes: int, old_size_bytes: int = 0
    ) -> None:
        current_total = await self.document_repo.sum_size_by_project(
            project_id=project_id
        )
        new_total = current_total - old_size_bytes + new_size_bytes
        if new_total > CONFIG.document.max_project_storage_bytes:
            raise PayloadTooLargeError("Project storage limit exceeded")

    async def _resolve_filename(self, filename: str | None, content_type: str):
        if filename:
            return filename
        extension = mimetypes.guess_extension(content_type) or ""
        return f"{uuid.uuid4()}{extension}"

    async def upload_document(
        self,
        project_id: uuid.UUID,
        uploaded_by: uuid.UUID,
        content: bytes,
        content_type: str,
        filename: str | None,
    ) -> Document:
        size_bytes = len(content)
        filename = await self._resolve_filename(filename, content_type)
        await self._validate_storage_limit(
            project_id=project_id, new_size_bytes=size_bytes
        )
        s3_key = f"projects/{project_id}/documents/{uuid.uuid4()}"
        await self.storage_service.upload(
            key=s3_key,
            content=content,
            content_type=content_type,
        )

        document = await self.document_repo.add(
            project_id=project_id,
            uploaded_by=uploaded_by,
            filename=filename,
            s3_key=s3_key,
            content_type=content_type,
            size_bytes=size_bytes,
        )
        return document

    async def get_download_url(
        self, document_id: uuid.UUID, expires_in: int = 300
    ) -> str:
        document = await self.document_repo.get_by_id(document_id=document_id)
        if document is None:
            raise NotFoundError("Document not found.")
        return await self.storage_service.generate_presigned_url(
            document.s3_key, expires_in
        )

    async def replace_document(
        self,
        document_id: uuid.UUID,
        content: bytes,
        content_type: str,
        filename: str | None,
    ) -> Document:
        document = await self.document_repo.get_by_id(document_id)
        if document is None:
            raise NotFoundError("Document not found.")
        size_bytes = len(content)
        filename = await self._resolve_filename(filename, content_type)
        await self._validate_storage_limit(
            project_id=document.project_id,
            new_size_bytes=size_bytes,
            old_size_bytes=document.size_bytes,
        )
        new_s3_key = f"projects/{document.project_id}/documents/{uuid.uuid4()}"
        old_s3_key = document.s3_key
        await self.storage_service.upload(
            key=new_s3_key, content=content, content_type=content_type
        )
        new_document = await self.document_repo.update_document(
            document,
            s3_key=new_s3_key,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
        )
        await self.storage_service.delete(key=old_s3_key)
        return new_document

    async def update_document_metadata(
        self, document_id: uuid.UUID, filename: str | None
    ) -> Document:
        document = await self.document_repo.get_by_id(document_id)
        if document is None:
            raise NotFoundError("Document not found.")
        return await self.document_repo.update_document(document, filename=filename)

    async def delete_document(self, document_id: uuid.UUID) -> None:
        document = await self.document_repo.get_by_id(document_id=document_id)
        if document is None:
            raise NotFoundError("Document not found.")
        await self.document_repo.delete(document)
        await self.storage_service.delete(document.s3_key)

    async def list_by_project(self, project_id: uuid.UUID) -> list[Document]:
        return await self.document_repo.list_by_project(project_id=project_id)
