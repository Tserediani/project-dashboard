import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from project_dashboard.models.base import Base

if TYPE_CHECKING:
    from project_dashboard.models.project import Project
    from project_dashboard.models.user import User


class ProjectRole(str, enum.Enum):
    OWNER = "owner"
    PARTICIPANT = "participant"


class ProjectAccess(Base):
    __tablename__ = "project_access"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_user_access"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[ProjectRole] = mapped_column(
        Enum(ProjectRole, name="project_role_enum"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project: Mapped[Project] = relationship(back_populates="access_entries")
    user: Mapped[User] = relationship(back_populates="project_access_entries")
