from collections.abc import Awaitable
from typing import Protocol

from project_dashboard.schemas.project import ProjectRead
from project_dashboard.schemas.user import UserRead


class FakeUser(UserRead):
    password: str
    access_token: str

    @property
    def auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}


class FakeProject(ProjectRead): ...


class AuthUserFactory(Protocol):
    def __call__(
        self, email: str, password: str = "password!123"
    ) -> Awaitable[FakeUser]: ...
