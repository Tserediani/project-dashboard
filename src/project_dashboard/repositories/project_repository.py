import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from project_dashboard.models import Project


class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, name: str, description: str | None, owner_id: uuid.UUID
    ) -> Project:
        project = Project(name=name, description=description, owner_id=owner_id)
        self.session.add(project)
        await self.session.flush()
        return project

    async def get_by_id(self, project_id: uuid.UUID) -> Project | None:
        result = await self.session.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self, project: Project, name: str | None, description: str | None
    ) -> Project:
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def delete(self, project: Project) -> None:
        await self.session.delete(project)
        await self.session.flush()
