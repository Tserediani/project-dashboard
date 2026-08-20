import pytest
from httpx import AsyncClient

from tests.helpers.api import create_user_project
from tests.helpers.fake_models import (
    AuthUserFactory,
    FakeDocument,
    FakeProject,
    FakeUser,
)


@pytest.fixture
async def user_alice(auth_user_factory: AuthUserFactory) -> FakeUser:
    return await auth_user_factory("alice@example.com")


@pytest.fixture
async def user_bob(auth_user_factory: AuthUserFactory) -> FakeUser:
    return await auth_user_factory("bob@example.com")


@pytest.fixture
async def user_charlie(auth_user_factory: AuthUserFactory) -> FakeUser:
    return await auth_user_factory("charlie@example.com")


@pytest.fixture
async def alices_project(client: AsyncClient, user_alice: FakeUser) -> FakeProject:
    return await create_user_project(
        client,
        user=user_alice,
        name="Alice's Project",
        description="Alice's Project's Description",
    )


@pytest.fixture
async def bobs_project(client: AsyncClient, user_bob: FakeUser) -> FakeProject:
    return await create_user_project(
        client,
        user=user_bob,
        name="Bob's Project",
        description="Bob's Project's Description",
    )


@pytest.fixture
def fake_document() -> FakeDocument:
    return FakeDocument(
        filename="test_file.txt",
        content=b"file content",
    )
