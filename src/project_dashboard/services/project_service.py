import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from project_dashboard.core.exceptions import ConflictError, NotFoundError
from project_dashboard.models import Project, ProjectRole, User
from project_dashboard.repositories.project_access_repository import (
    ProjectAccessRepository,
)
from project_dashboard.repositories.project_repository import ProjectRepository
from project_dashboard.repositories.user_repository import UserRepository


class ProjectService:
    def __init__(
        self,
        project_repo: ProjectRepository,
        user_repo: UserRepository,
        project_access_repo: ProjectAccessRepository,
        session: AsyncSession,
    ):
        self.project_repo = project_repo
        self.user_repo = user_repo
        self.project_access_repo = project_access_repo
        self.session = session

    async def create_project(
        self, name: str, description: str | None, owner: User
    ) -> Project:
        project = await self.project_repo.create(
            name=name, description=description, owner_id=owner.id
        )
        await self.project_access_repo.create(
            project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
        )
        await self.session.commit()
        return project

    async def list_projects_for_user(self, user_id: uuid.UUID) -> list[Project]:
        entries = await self.project_access_repo.list_project_for_user(user_id=user_id)
        return [entry.project for entry in entries]

    async def update_project(
        self, project_id: uuid.UUID, name: str | None, description: str | None
    ) -> Project:
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project Not found")
        project = await self.project_repo.update(
            project=project, name=name, description=description
        )
        await self.session.commit()
        return project

    async def delete_project(self, project_id: uuid.UUID) -> None:
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project Not found")
        await self.project_repo.delete(project)
        await self.session.commit()

    async def invite_user(
        self, project_id: uuid.UUID, target_email: str, inviter_id: uuid.UUID
    ) -> None:
        target_user = await self.user_repo.get_by_email(target_email)
        if target_user is None:
            raise NotFoundError("User with this email not found")
        if target_user.id == inviter_id:
            raise ConflictError("Cannot invite yourself")

        existing = await self.project_access_repo.get(
            project_id=project_id, user_id=target_user.id
        )
        if existing is not None:
            return

        await self.project_access_repo.create(
            project_id=project_id, user_id=target_user.id, role=ProjectRole.PARTICIPANT
        )
        await self.session.commit()
