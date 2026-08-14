import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from project_dashboard.models import Document


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def list_by_project(self, project_id: uuid.UUID) -> list[Document]:
        stmt = (
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def sum_size_by_project(self, project_id: uuid.UUID) -> int:
        stmt = select(func.coalesce(func.sum(Document.size_bytes), 0)).where(
            Document.project_id == project_id
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def add(
        self,
        project_id: uuid.UUID,
        uploaded_by: uuid.UUID,
        filename: str,
        s3_key: str,
        content_type: str,
        size_bytes: int,
    ) -> Document:
        document = Document(
            project_id=project_id,
            uploaded_by=uploaded_by,
            filename=filename,
            s3_key=s3_key,
            content_type=content_type,
            size_bytes=size_bytes,
        )
        self.session.add(document)
        await self.session.flush()
        return document

    async def delete(self, document: Document) -> None:
        await self.session.delete(document)
        await self.session.flush()

    async def update_document(
        self,
        document: Document,
        filename: str | None = None,
        content_type: str | None = None,
        size_bytes: int | None = None,
    ):
        if filename is not None:
            document.filename = filename
        if content_type is not None:
            document.content_type = content_type
        if size_bytes is not None:
            document.size_bytes = size_bytes
        await self.session.flush()
        await self.session.refresh(document)
        return document
