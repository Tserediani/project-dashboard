import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from project_dashboard.api.deps import (
    get_current_user,
    get_document_access,
    get_document_service,
    get_project_access,
)
from project_dashboard.db.session import get_session
from project_dashboard.models import ProjectAccess, User
from project_dashboard.schemas.document import (
    DocumentDownloadUrl,
    DocumentRead,
    DocumentUpdate,
)
from project_dashboard.services.document_service import DocumentService

router = APIRouter(tags=["documents"])


@router.post(
    "/projects/{project_id}/documents",
    status_code=201,
    response_model=DocumentRead,
)
async def upload_document(
    project_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    access: Annotated[ProjectAccess, Depends(get_project_access)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    file: UploadFile,
):
    document = await document_service.upload_document(
        project_id=project_id,
        uploaded_by=current_user.id,
        content=await file.read(),
        content_type=file.content_type or "application/octet-stream",
        filename=file.filename or str(uuid.uuid4()),
    )
    await session.commit()
    return document


@router.get("/projects/{project_id}/documents", response_model=list[DocumentRead])
async def list_documents(
    project_id: uuid.UUID,
    access: Annotated[ProjectAccess, Depends(get_project_access)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
):
    documents = await document_service.list_by_project(project_id=project_id)
    return documents


@router.get("/documents/{document_id}/download", response_model=DocumentDownloadUrl)
async def get_document_url(
    document_id: uuid.UUID,
    access: Annotated[ProjectAccess, Depends(get_document_access)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
):
    url = await document_service.get_download_url(document_id=document_id)
    return DocumentDownloadUrl(url=url, expires_in=300)


@router.patch("/documents/{document_id}", response_model=DocumentRead)
async def update_document_metadata(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    access: Annotated[ProjectAccess, Depends(get_document_access)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    document = await document_service.update_document_metadata(
        document_id=document_id, filename=payload.filename
    )
    await session.commit()
    return document


@router.put("/documents/{document_id}", response_model=DocumentRead)
async def update_document(
    document_id: uuid.UUID,
    file: UploadFile,
    access: Annotated[ProjectAccess, Depends(get_document_access)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    document = await document_service.replace_document(
        document_id,
        content=await file.read(),
        content_type=file.content_type or "application/octet-stream",
        filename=file.filename or str(uuid.uuid4()),
    )
    await session.commit()
    return document


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    access: Annotated[ProjectAccess, Depends(get_document_access)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    await document_service.delete_document(document_id)
    await session.commit()
