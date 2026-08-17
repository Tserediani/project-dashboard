import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from project_dashboard.api.deps import (
    get_current_user,
    get_project_access,
    get_project_service,
    require_owner,
)
from project_dashboard.db.session import get_session
from project_dashboard.models import ProjectAccess, User
from project_dashboard.schemas.project import (
    InviteRequest,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
)
from project_dashboard.services.project_service import ProjectService

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)


@router.post(
    "",
    status_code=201,
    response_model=ProjectRead,
    summary="Create a project",
)
async def create_project(
    payload: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ProjectService, Depends(get_project_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Create a new project owned by the authenticated user."""
    project = await service.create_project(
        name=payload.name, description=payload.description, owner=current_user
    )
    await session.commit()
    return project


@router.get("", response_model=list[ProjectRead], summary="List projects")
async def list_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ProjectService, Depends(get_project_service)],
):
    """List projects accessible to the authenticated user."""
    projects = await service.list_projects_for_user(user_id=current_user.id)
    return projects


@router.get(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Get a project",
    responses={
        404: {"description": "Project not found"},
    },
)
async def get_project(access: Annotated[ProjectAccess, Depends(get_project_access)]):
    """Retrive a project accessible to the authenticated user."""
    return access.project


@router.put(
    "/{project_id}",
    response_model=ProjectRead,
    dependencies=[Depends(require_owner)],
    summary="Update a project",
    responses={
        404: {"description": "Project not found"},
    },
)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    service: Annotated[ProjectService, Depends(get_project_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Update a project owned by the authenticated user."""
    project = await service.update_project(
        project_id=project_id, name=payload.name, description=payload.description
    )
    await session.commit()
    return project


@router.delete(
    "/{project_id}",
    status_code=204,
    dependencies=[Depends(require_owner)],
    summary="Delete a project",
    responses={
        404: {"description": "Project not found"},
    },
)
async def delete_project(
    project_id: uuid.UUID,
    service: Annotated[ProjectService, Depends(get_project_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Delete a project owned by the authenticated user."""
    await service.delete_project(project_id=project_id)
    await session.commit()


@router.post(
    "/{project_id}/invite",
    summary="Invite a user to a project",
    responses={
        404: {"description": "Project not found"},
        409: {"description": "The user already has access to the project"},
    },
)
async def invite_user(
    project_id: uuid.UUID,
    query: InviteRequest,
    access: Annotated[ProjectAccess, Depends(require_owner)],
    service: Annotated[ProjectService, Depends(get_project_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Grant project access to the user by email."""
    await service.invite_user(
        project_id=project_id, target_email=query.email, inviter_id=access.user_id
    )
    await session.commit()
    return {"detail": "Access Granted."}
