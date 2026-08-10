import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from project_dashboard.models import ProjectAccess, ProjectRole


class ProjectAccessRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, project_id: uuid.UUID, user_id: uuid.UUID, role: ProjectRole
    ) -> ProjectAccess:
        access = ProjectAccess(project_id=project_id, user_id=user_id, role=role)
        self.session.add(access)
        await self.session.flush()
        return access

    async def get(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> ProjectAccess | None:
        result = await self.session.execute(
            select(ProjectAccess)
            .options(selectinload(ProjectAccess.project))
            .where(
                ProjectAccess.project_id == project_id,
                ProjectAccess.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_project_for_user(self, user_id: uuid.UUID) -> list[ProjectAccess]:
        result = await self.session.execute(
            select(ProjectAccess)
            .where(ProjectAccess.user_id == user_id)
            .options(selectinload(ProjectAccess.project))
        )
        return list(result.scalars().all())
