import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from tests.helpers.api import (
    add_as_participant,
    assert_document_payload,
    upload_document,
)
from tests.helpers.fake_models import (
    FakeDocument,
    FakeProject,
    FakeUser,
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


@pytest.mark.parametrize(
    "content_type", ("text/plain", "image/png", "application/json")
)
async def test_upload_document_returns_415_when_document_type_is_not_supported(
    client: AsyncClient,
    user_alice: FakeUser,
    alices_project: FakeProject,
    storage_service: AsyncMock,
    fake_document: FakeDocument,
    content_type: str,
):
    response = await client.post(
        f"/projects/{alices_project.id}/documents",
        files={
            "file": (
                fake_document.filename,
                fake_document.content,
                content_type,
            )
        },
        headers=user_alice.auth_headers,
    )
    assert response.status_code == 415
    storage_service.upload.assert_not_awaited()


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


async def test_get_document_url_project_owner_gets_document_url(
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
        f"/documents/{fake_document_metadata.id}/download",
        headers=user_alice.auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["url"]
    assert response.json()["expires_in"]

    storage_service.generate_presigned_url.assert_awaited_once()


async def test_get_document_url_project_participant_gets_document_url(
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
        f"/documents/{fake_document_metadata.id}/download",
        headers=user_bob.auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["url"]
    assert response.json()["expires_in"]

    storage_service.generate_presigned_url.assert_awaited_once()


async def test_get_document_url_returns_401_when_user_not_logged_in(
    client: AsyncClient,
):
    response = await client.get(f"/documents/{uuid.uuid4()}/download")
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
        f"/documents/{fake_document_metadata.id}/download",
        headers=user_bob.auth_headers,
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
    updated_file = FakeDocument(filename="updated.txt", content=b"updated content")
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
    updated_file = FakeDocument(filename="updated.txt", content=b"updated content")
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


@pytest.mark.parametrize(
    "content_type", ("text/plain", "image/png", "application/json")
)
async def test_update_document_returns_415_when_document_type_is_not_supported(
    client: AsyncClient,
    user_alice: FakeUser,
    alices_project: FakeProject,
    storage_service: AsyncMock,
    fake_document: FakeDocument,
    content_type: str,
):
    updated_file = FakeDocument(filename="updated.txt", content=b"updated content")
    fake_document_metadata = await upload_document(
        client, document=fake_document, user=user_alice, project=alices_project
    )
    storage_service.reset_mock()

    response = await client.put(
        f"/documents/{fake_document_metadata.id}",
        files={"file": (updated_file.filename, updated_file.content, content_type)},
        headers=user_alice.auth_headers,
    )
    assert response.status_code == 415
    storage_service.upload.assert_not_awaited()


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
