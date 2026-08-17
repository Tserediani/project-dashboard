import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from tests.helpers import (
    AuthUserFactory,
    FakeDocument,
    FakeDocumentMetadata,
    FakeProject,
    FakeUser,
)


def assert_document_payload(
    document: dict,
    *,
    project_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    content_type: str,
    size_bytes: int,
    filename: str,
) -> None:
    assert uuid.UUID(document["id"])
    assert uuid.UUID(document["project_id"]) == project_id
    assert uuid.UUID(document["uploaded_by"]) == uploaded_by
    assert document["filename"] == filename
    assert document["content_type"] == content_type
    assert document["size_bytes"] == size_bytes
    assert f"projects/{project_id}/documents/" in document["s3_key"]


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


async def upload_document(
    client: AsyncClient, *, document: FakeDocument, user: FakeUser, project: FakeProject
) -> FakeDocumentMetadata:
    response = await client.post(
        f"/projects/{project.id}/documents",
        headers=user.auth_headers,
        files={
            "file": (
                document.filename,
                document.content,
                document.content_type,
            )
        },
    )
    document_metadata = response.json()

    assert_document_payload(
        response.json(),
        project_id=project.id,
        uploaded_by=user.id,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        filename=document.filename,
    )
    return FakeDocumentMetadata(**document_metadata)


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
        filename="test_file.txt", content=b"file content", content_type="text/plain"
    )


async def test_upload_document_project_owner_uploads_document(
    client: AsyncClient,
    user_alice: FakeUser,
    alices_project: FakeProject,
    storage_service: AsyncMock,
    fake_document: FakeDocument,
):

    response = await client.post(
        f"/projects/{alices_project.id}/documents",
        headers=user_alice.auth_headers,
        files={
            "file": (
                fake_document.filename,
                fake_document.content,
                fake_document.content_type,
            )
        },
    )

    assert response.status_code == 201

    document_metadata = response.json()
    assert_document_payload(
        document_metadata,
        project_id=alices_project.id,
        uploaded_by=user_alice.id,
        content_type=fake_document.content_type,
        size_bytes=fake_document.size_bytes,
        filename=fake_document.filename,
    )
    storage_service.upload.assert_awaited_once()


async def test_upload_document_project_participant_uploads_document(
    client: AsyncClient,
    user_alice: FakeUser,
    user_bob: FakeUser,
    alices_project: FakeProject,
    storage_service: AsyncMock,
    fake_document: FakeDocument,
):
    await add_as_participant(
        client, target_email=user_bob.email, owner=user_alice, project=alices_project
    )

    response = await client.post(
        f"/projects/{alices_project.id}/documents",
        headers=user_bob.auth_headers,
        files={
            "file": (
                fake_document.filename,
                fake_document.content,
                fake_document.content_type,
            )
        },
    )

    assert response.status_code == 201

    document_metadata = response.json()
    assert_document_payload(
        document_metadata,
        project_id=alices_project.id,
        uploaded_by=user_bob.id,
        content_type=fake_document.content_type,
        size_bytes=fake_document.size_bytes,
        filename=fake_document.filename,
    )
    storage_service.upload.assert_awaited_once()


async def test_upload_document_returns_401_when_user_not_logged_in(
    client: AsyncClient, storage_service: AsyncMock, fake_document: FakeDocument
):
    response = await client.post(
        f"/projects/{uuid.uuid4()}/documents",
        files={
            "file": (
                fake_document.filename,
                fake_document.content,
                fake_document.content_type,
            )
        },
    )
    assert response.status_code == 401
    storage_service.upload.assert_not_awaited()


async def test_upload_document_returns_404_when_user_has_no_access(
    client: AsyncClient,
    user_bob: FakeUser,
    alices_project: FakeProject,
    storage_service: AsyncMock,
    fake_document: FakeDocument,
):
    response = await client.post(
        f"/projects/{alices_project.id}/documents",
        headers=user_bob.auth_headers,
        files={
            "file": (
                fake_document.filename,
                fake_document.content,
                fake_document.content_type,
            )
        },
    )

    assert response.status_code == 404

    storage_service.upload.assert_not_awaited()


async def test_get_documents_project_owner_gets_list_of_document_metadata(
    client: AsyncClient,
    user_alice: FakeUser,
    alices_project: FakeProject,
    fake_document: FakeDocument,
):
    await upload_document(
        client, document=fake_document, user=user_alice, project=alices_project
    )

    response = await client.get(
        f"/projects/{alices_project.id}/documents",
        headers=user_alice.auth_headers,
    )
    assert response.status_code == 200

    documents = response.json()
    assert isinstance(documents, list)
    assert len(documents) == 1

    assert_document_payload(
        document=documents[0],
        project_id=alices_project.id,
        uploaded_by=user_alice.id,
        content_type=fake_document.content_type,
        size_bytes=fake_document.size_bytes,
        filename=fake_document.filename,
    )


async def test_get_documents_project_participant_gets_list_of_document_metadata(
    client: AsyncClient,
    user_alice: FakeUser,
    user_bob: FakeUser,
    alices_project: FakeProject,
    fake_document: FakeDocument,
):
    await add_as_participant(
        client, target_email=user_bob.email, owner=user_alice, project=alices_project
    )
    await upload_document(
        client, document=fake_document, user=user_bob, project=alices_project
    )

    response = await client.get(
        f"/projects/{alices_project.id}/documents",
        headers=user_alice.auth_headers,
    )
    assert response.status_code == 200

    documents = response.json()
    assert isinstance(documents, list)
    assert len(documents) == 1

    assert_document_payload(
        document=documents[0],
        project_id=alices_project.id,
        uploaded_by=user_bob.id,
        content_type=fake_document.content_type,
        size_bytes=fake_document.size_bytes,
        filename=fake_document.filename,
    )


async def test_get_documents_returns_401_when_user_not_logged_in(client: AsyncClient):
    response = await client.get(f"/projects/{uuid.uuid4()}/documents")
    assert response.status_code == 401


async def test_get_documents_returns_404_when_user_has_no_accesss(
    client: AsyncClient,
    user_bob: FakeUser,
    alices_project: FakeProject,
):
    response = await client.get(
        f"/projects/{alices_project.id}/documents",
        headers=user_bob.auth_headers,
    )

    assert response.status_code == 404


async def test_get_document_project_owner_gets_document_metadata(
    client: AsyncClient,
    user_alice: FakeUser,
    user_bob: FakeUser,
    alices_project: FakeProject,
    storage_service: AsyncMock,
    fake_document: FakeDocument,
):
    fake_document_metadata = await upload_document(
        client, document=fake_document, user=user_alice, project=alices_project
    )

    response = await client.get(
        f"/documents/{fake_document_metadata.id}", headers=user_alice.auth_headers
    )

    assert response.status_code == 200
    assert response.json()["url"]
    assert response.json()["expires_in"]

    storage_service.generate_presigned_url.assert_awaited_once()


async def test_get_document_url_project_participant_gets_document_metadata(
    client: AsyncClient,
    user_alice: FakeUser,
    user_bob: FakeUser,
    alices_project: FakeProject,
    storage_service: AsyncMock,
    fake_document: FakeDocument,
):
    await add_as_participant(
        client, target_email=user_bob.email, owner=user_alice, project=alices_project
    )
    fake_document_metadata = await upload_document(
        client, document=fake_document, user=user_alice, project=alices_project
    )

    response = await client.get(
        f"/documents/{fake_document_metadata.id}", headers=user_bob.auth_headers
    )

    assert response.status_code == 200
    assert response.json()["url"]
    assert response.json()["expires_in"]

    storage_service.generate_presigned_url.assert_awaited_once()


async def test_get_document_url_returns_401_when_user_not_logged_in(
    client: AsyncClient,
):
    response = await client.get(f"/documents/{uuid.uuid4()}")
    assert response.status_code == 401


async def test_get_document_url_returns_404_when_user_has_no_access(
    client: AsyncClient,
    user_alice: FakeUser,
    user_bob: FakeUser,
    alices_project: FakeProject,
    fake_document: FakeDocument,
):
    fake_document_metadata = await upload_document(
        client, document=fake_document, user=user_alice, project=alices_project
    )
    response = await client.get(
        f"/documents/{fake_document_metadata.id}", headers=user_bob.auth_headers
    )

    assert response.status_code == 404


async def test_update_document_metadata_project_owner_updates_document_metadata(
    client: AsyncClient,
    user_alice: FakeUser,
    alices_project: FakeProject,
    fake_document: FakeDocument,
):
    fake_document_metadata = await upload_document(
        client, document=fake_document, user=user_alice, project=alices_project
    )
    response = await client.patch(
        f"/documents/{fake_document_metadata.id}",
        json={"filename": "updated.txt"},
        headers=user_alice.auth_headers,
    )
    assert_document_payload(
        response.json(),
        project_id=alices_project.id,
        uploaded_by=user_alice.id,
        content_type=fake_document.content_type,
        size_bytes=fake_document.size_bytes,
        filename="updated.txt",
    )


async def test_update_document_metadata_project_participant_updated_document_metadata(
    client: AsyncClient,
    user_alice: FakeUser,
    user_bob: FakeUser,
    alices_project: FakeProject,
    fake_document: FakeDocument,
):
    await add_as_participant(
        client, target_email=user_bob.email, owner=user_alice, project=alices_project
    )
    fake_document_metadata = await upload_document(
        client, document=fake_document, user=user_alice, project=alices_project
    )
    response = await client.patch(
        f"/documents/{fake_document_metadata.id}",
        json={"filename": "updated.txt"},
        headers=user_bob.auth_headers,
    )
    assert_document_payload(
        response.json(),
        project_id=alices_project.id,
        uploaded_by=user_alice.id,
        content_type=fake_document.content_type,
        size_bytes=fake_document.size_bytes,
        filename="updated.txt",
    )


async def test_update_document_metadata_returns_401_when_user_not_logged_in(
    client: AsyncClient,
):
    response = await client.patch(
        f"/documents/{uuid.uuid4()}", json={"filename": "test.txt"}
    )
    assert response.status_code == 401


async def test_update_document_metadata_returns_404_when_user_has_no_access(
    client: AsyncClient,
    user_bob: FakeUser,
    user_alice: FakeUser,
    alices_project: FakeProject,
    fake_document: FakeDocument,
):
    fake_document_metadata = await upload_document(
        client, document=fake_document, user=user_alice, project=alices_project
    )
    response = await client.patch(
        f"/documents/{fake_document_metadata.id}",
        json={"filename": "test.txt"},
        headers=user_bob.auth_headers,
    )

    assert response.status_code == 404


async def test_update_document_project_owner_updates_document(
    client: AsyncClient,
    user_alice: FakeUser,
    alices_project: FakeProject,
    fake_document: FakeDocument,
    storage_service: AsyncMock,
):
    updated_file = FakeDocument(
        filename="updated.txt", content=b"updated content", content_type="text/plain"
    )
    fake_document_metadata = await upload_document(
        client, document=fake_document, user=user_alice, project=alices_project
    )
    storage_service.reset_mock()

    response = await client.put(
        f"/documents/{fake_document_metadata.id}",
        headers=user_alice.auth_headers,
        files={
            "file": (
                updated_file.filename,
                updated_file.content,
                updated_file.content_type,
            )
        },
    )

    assert response.status_code == 200
    assert_document_payload(
        response.json(),
        project_id=alices_project.id,
        uploaded_by=user_alice.id,
        content_type=updated_file.content_type,
        size_bytes=updated_file.size_bytes,
        filename=updated_file.filename,
    )
    storage_service.upload.assert_awaited_once()
    storage_service.delete.assert_awaited_once()


async def test_update_document_project_participant_updates_document(
    client: AsyncClient,
    user_alice: FakeUser,
    user_bob: FakeUser,
    alices_project: FakeProject,
    fake_document: FakeDocument,
    storage_service: AsyncMock,
):
    await add_as_participant(
        client, target_email=user_bob.email, owner=user_alice, project=alices_project
    )
    updated_file = FakeDocument(
        filename="updated.txt", content=b"updated content", content_type="text/plain"
    )
    fake_document_metadata = await upload_document(
        client, document=fake_document, user=user_alice, project=alices_project
    )
    storage_service.reset_mock()

    response = await client.put(
        f"/documents/{fake_document_metadata.id}",
        headers=user_bob.auth_headers,
        files={
            "file": (
                updated_file.filename,
                updated_file.content,
                updated_file.content_type,
            )
        },
    )

    assert response.status_code == 200
    assert_document_payload(
        response.json(),
        project_id=alices_project.id,
        uploaded_by=user_alice.id,
        content_type=updated_file.content_type,
        size_bytes=updated_file.size_bytes,
        filename=updated_file.filename,
    )
    storage_service.upload.assert_awaited_once()
    storage_service.delete.assert_awaited_once()


async def test_update_document_returns_401_when_user_not_logged_in(
    client: AsyncClient, fake_document: FakeDocument
):
    response = await client.put(
        f"/documents/{uuid.uuid4()}",
        files={
            "file": (
                fake_document.filename,
                fake_document.content,
                fake_document.content_type,
            )
        },
    )
    assert response.status_code == 401


async def test_update_document_returns_404_when_user_has_no_access(
    client: AsyncClient,
    user_alice: FakeUser,
    user_bob: FakeUser,
    alices_project: FakeProject,
    fake_document: FakeDocument,
):
    fake_document_metadata = await upload_document(
        client, document=fake_document, user=user_alice, project=alices_project
    )
    response = await client.put(
        f"/documents/{fake_document_metadata.id}",
        files={
            "file": (
                fake_document.filename,
                fake_document.content,
                fake_document.content_type,
            )
        },
        headers=user_bob.auth_headers,
    )
    assert response.status_code == 404


async def test_delete_document_project_owner_deletes_document(
    client: AsyncClient,
    user_alice: FakeUser,
    alices_project: FakeProject,
    fake_document: FakeDocument,
    storage_service: AsyncMock,
):
    fake_document_metadata = await upload_document(
        client, document=fake_document, user=user_alice, project=alices_project
    )

    response = await client.delete(
        f"/documents/{fake_document_metadata.id}", headers=user_alice.auth_headers
    )

    assert response.status_code == 204

    storage_service.delete.assert_awaited_once()


async def test_delete_document_project_participant_deletes_document(
    client: AsyncClient,
    user_alice: FakeUser,
    user_bob: FakeUser,
    alices_project: FakeProject,
    fake_document: FakeDocument,
    storage_service: AsyncMock,
):
    await add_as_participant(
        client, target_email=user_bob.email, owner=user_alice, project=alices_project
    )

    fake_document_metadata = await upload_document(
        client, document=fake_document, user=user_alice, project=alices_project
    )

    response = await client.delete(
        f"/documents/{fake_document_metadata.id}", headers=user_bob.auth_headers
    )
    assert response.status_code == 204
    storage_service.delete.assert_awaited_once()


async def test_delete_document_returns_401_when_user_not_logged_in(
    client: AsyncClient, storage_service: AsyncMock
):
    response = await client.delete(
        f"/documents/{uuid.uuid4()}",
    )
    assert response.status_code == 401
    storage_service.delete.assert_not_called()


async def test_delete_document_returns_404_when_user_has_no_access(
    client: AsyncClient,
    user_alice: FakeUser,
    user_bob: FakeUser,
    alices_project: FakeProject,
    fake_document: FakeDocument,
    storage_service: AsyncMock,
):
    fake_document_metadata = await upload_document(
        client, document=fake_document, user=user_alice, project=alices_project
    )

    response = await client.delete(
        f"/documents/{fake_document_metadata.id}", headers=user_bob.auth_headers
    )
    assert response.status_code == 404
    storage_service.delete.assert_not_called()
