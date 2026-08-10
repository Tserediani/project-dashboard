import uuid

import pytest
from httpx import AsyncClient

from tests.helpers import AuthUserFactory, FakeProject, FakeUser


def assert_project_payload(
    project: dict,
    *,
    name: str | None,
    description: str | None,
    owner_id: uuid.UUID,
) -> None:
    assert project["name"] == name
    assert project["description"] == description
    assert uuid.UUID(project["owner_id"]) == owner_id


async def create_user_project(
    client: AsyncClient,
    user: FakeUser,
    name: str,
    description: str | None = None,
) -> FakeProject:
    payload = {"name": name, "description": description}
    response = await client.post(
        "/projects",
        json=payload,
        headers=user.auth_headers,
    )
    assert response.status_code == 201, response.text
    project = response.json()
    assert_project_payload(
        project,
        name=payload["name"],
        description=payload["description"],
        owner_id=user.id,
    )
    return FakeProject(**project)


async def add_as_participant(
    client: AsyncClient,
    *,
    target_email: str,
    owner: FakeUser,
    project: FakeProject,
) -> None:
    payload = {"email": target_email}
    response = await client.post(
        f"/project/{project.id}/invite", headers=owner.auth_headers, json=payload
    )
    assert response.status_code == 200, response.text


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


async def test_create_project_auth_user_creates_project(
    client: AsyncClient, user_alice: FakeUser
):
    payload = {"name": "My Project", "description": "Project Description"}

    response = await client.post(
        "/projects",
        json=payload,
        headers=user_alice.auth_headers,
    )

    assert response.status_code == 201, response.text

    project = response.json()
    assert_project_payload(
        project,
        name=payload["name"],
        description=payload["description"],
        owner_id=user_alice.id,
    )


async def test_create_project_returns_401_when_user_not_logged(
    client: AsyncClient,
):
    payload = {"name": "My Project", "description": "Project Description"}
    response = await client.post(
        "/projects",
        json=payload,
    )

    assert response.status_code == 401, response.text


async def test_list_projects_returns_projects_user_has_access(
    client: AsyncClient,
    user_alice: FakeUser,
    alices_project: FakeProject,
    bobs_project: FakeProject,
):
    response = await client.get("/projects", headers=user_alice.auth_headers)

    assert response.status_code == 200, response.text
    projects = response.json()
    assert len(projects) == 1
    assert uuid.UUID(projects[0]["id"]) == alices_project.id
    assert_project_payload(
        projects[0],
        name=alices_project.name,
        description=alices_project.description,
        owner_id=user_alice.id,
    )


async def test_list_projects_returns_401_when_user_not_logged(
    client: AsyncClient,
):
    response = await client.get("/projects")
    assert response.status_code == 401, response.text


async def test_get_project_returns_project_user_has_access(
    client: AsyncClient, user_alice: FakeUser, alices_project: FakeProject
):

    response = await client.get(
        f"/project/{alices_project.id}/info",
        headers=user_alice.auth_headers,
    )

    assert response.status_code == 200, response.text

    responded_project = response.json()
    assert_project_payload(
        responded_project,
        name=alices_project.name,
        description=alices_project.description,
        owner_id=user_alice.id,
    )


async def test_get_project_returns_404_when_user_logged_and_project_not_exist(
    client: AsyncClient, user_alice: FakeUser
):
    response = await client.get(
        f"/project/{uuid.uuid4()}/info",
        headers=user_alice.auth_headers,
    )
    assert response.status_code == 404, response.text


async def test_get_project_returns_404_when_user_has_no_access(
    client: AsyncClient, user_alice: FakeUser, bobs_project: FakeProject
):

    response = await client.get(
        f"/project/{bobs_project.id}/info",
        headers=user_alice.auth_headers,
    )
    assert response.status_code == 404, response.text


async def test_get_project_returns_401_when_user_not_logged(client: AsyncClient):
    response = await client.get(f"/project/{uuid.uuid4()}/info")
    assert response.status_code == 401, response.text


@pytest.mark.parametrize(
    ("name", "description"),
    (
        ("Updated name", "Updated desc"),
        (
            None,
            "Updated without name description",
        ),
        (
            "Updated name without description",
            None,
        ),
        (None, None),
    ),
)
async def test_update_project_updates_project_when_user_owns(
    client: AsyncClient,
    user_alice: FakeUser,
    alices_project: FakeProject,
    name: str | None,
    description: str | None,
):
    response = await client.put(
        f"/project/{alices_project.id}/info",
        headers=user_alice.auth_headers,
        json={"name": name, "description": description},
    )

    assert response.status_code == 200, response.text

    updated_project = response.json()
    assert_project_payload(
        updated_project,
        name=name if name is not None else alices_project.name,
        description=description
        if description is not None
        else alices_project.description,
        owner_id=user_alice.id,
    )


async def test_update_project_returns_404_when_user_has_no_access(
    client: AsyncClient, user_alice: FakeUser, bobs_project: FakeProject
):
    response = await client.put(
        f"/project/{bobs_project.id}/info",
        headers=user_alice.auth_headers,
        json={"name": "name"},
    )

    assert response.status_code == 404, response.text


async def test_update_project_returns_403_when_user_is_participant(
    client: AsyncClient,
    user_alice: FakeUser,
    alices_project: FakeProject,
    user_bob: FakeUser,
):

    await add_as_participant(
        client, target_email=user_bob.email, owner=user_alice, project=alices_project
    )

    response = await client.put(
        f"/project/{alices_project.id}/info",
        headers=user_bob.auth_headers,
        json={"name": "name"},
    )
    assert response.status_code == 403, response.text


async def test_update_project_returns_401_when_user_not_logged(client: AsyncClient):
    response = await client.put(f"/project/{uuid.uuid4()}/info", json={"name": "name"})
    assert response.status_code == 401, response.text


async def test_update_project_returns_404_when_user_logged_and_project_not_exist(
    client: AsyncClient, user_alice: FakeUser
):
    response = await client.put(
        f"/project/{uuid.uuid4()}/info",
        headers=user_alice.auth_headers,
        json={"name": "name"},
    )
    assert response.status_code == 404, response.text


async def test_delete_project_deletes_project_when_user_owns(
    client: AsyncClient, user_alice: FakeUser, alices_project: FakeProject
):
    response = await client.delete(
        f"/project/{alices_project.id}",
        headers=user_alice.auth_headers,
    )
    assert response.status_code == 204, response.text


async def test_delete_project_returns_404_when_user_has_no_access(
    client: AsyncClient,
    user_bob: FakeUser,
    alices_project: FakeProject,
):
    response = await client.delete(
        f"/project/{alices_project.id}",
        headers=user_bob.auth_headers,
    )
    assert response.status_code == 404, response.text


async def test_delete_project_returns_403_when_user_is_participant(
    client: AsyncClient,
    user_alice: FakeUser,
    user_bob: FakeUser,
    alices_project: FakeProject,
):
    await add_as_participant(
        client, target_email=user_bob.email, owner=user_alice, project=alices_project
    )
    response = await client.delete(
        f"/project/{alices_project.id}",
        headers=user_bob.auth_headers,
    )
    assert response.status_code == 403, response.text


async def test_delete_project_returns_401_when_user_not_logged(client: AsyncClient):
    response = await client.delete(f"/project/{uuid.uuid4()}")
    assert response.status_code == 401, response.text


async def test_delete_project_returns_404_when_user_logged_and_project_not_exist(
    client: AsyncClient, user_alice: FakeUser
):
    response = await client.delete(
        f"/project/{uuid.uuid4()}",
        headers=user_alice.auth_headers,
    )
    assert response.status_code == 404, response.text


async def test_invite_user_owner_adds_user_as_participant(
    client: AsyncClient,
    user_alice: FakeUser,
    user_bob: FakeUser,
    alices_project: FakeProject,
):
    response = await client.post(
        f"/project/{alices_project.id}/invite",
        json={"email": user_bob.email},
        headers=user_alice.auth_headers,
    )

    assert response.status_code == 200, response.text

    invited_project = await client.get(
        f"/project/{alices_project.id}/info",
        headers=user_bob.auth_headers,
    )
    assert invited_project.status_code == 200, invited_project.text
    assert invited_project.json()["name"] == alices_project.name


async def test_invite_user_returns_403_when_user_is_participant(
    client: AsyncClient,
    user_alice: FakeUser,
    user_bob: FakeUser,
    user_charlie: FakeUser,
    alices_project: FakeProject,
):
    await add_as_participant(
        client, target_email=user_bob.email, owner=user_alice, project=alices_project
    )
    response = await client.post(
        f"/project/{alices_project.id}/invite",
        json={"email": user_charlie.email},
        headers=user_bob.auth_headers,
    )
    assert response.status_code == 403, response.text


async def test_invite_user_returns_401_when_user_not_logged(client: AsyncClient):
    response = await client.post(
        f"/project/{uuid.uuid4()}/invite",
        json={"email": "alice@example.com"},
    )
    assert response.status_code == 401, response.text


async def test_invite_user_returns_404_when_user_logged_and_project_not_exist(
    client: AsyncClient, user_alice: FakeUser, user_bob: FakeUser
):
    response = await client.post(
        f"/project/{uuid.uuid4()}/invite",
        json={"email": user_bob.email},
        headers=user_alice.auth_headers,
    )
    assert response.status_code == 404, response.text


async def test_invite_user_returns_404_when_user_logged_on_nonexistant_target_email(
    client: AsyncClient,
    user_alice: FakeUser,
    alices_project: FakeProject,
):
    response = await client.post(
        f"/project/{alices_project.id}/invite",
        json={"email": "nonexistant@exampl.com"},
        headers=user_alice.auth_headers,
    )
    assert response.status_code == 404, response.text


async def test_invite_user_returns_409_when_user_invites_self(
    client: AsyncClient, user_alice: FakeUser, alices_project: FakeProject
):
    response = await client.post(
        f"/project/{alices_project.id}/invite",
        json={"email": user_alice.email},
        headers=user_alice.auth_headers,
    )
    assert response.status_code == 409, response.text


async def test_invite_user_returns_valid_response_when_target_is_already_participant(
    client: AsyncClient,
    user_alice: FakeUser,
    user_bob: FakeUser,
    alices_project: FakeProject,
):
    await add_as_participant(
        client, target_email=user_bob.email, owner=user_alice, project=alices_project
    )

    response = await client.post(
        f"/project/{alices_project.id}/invite",
        json={"email": user_bob.email},
        headers=user_alice.auth_headers,
    )

    assert response.status_code == 200, response.text
