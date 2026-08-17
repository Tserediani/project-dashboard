import uuid

from httpx import AsyncClient

from tests.helpers.fake_models import (
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
        f"/projects/{project.id}/invite", headers=owner.auth_headers, json=payload
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
