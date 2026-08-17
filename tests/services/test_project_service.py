import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from project_dashboard.core.exceptions import ConflictError, NotFoundError
from project_dashboard.models import ProjectRole
from project_dashboard.services.project_service import ProjectService


async def test_create_project_creates_owner_access(
    project_service: ProjectService,
    project_repo: AsyncMock,
    project_access_repo: AsyncMock,
    owner: MagicMock,
    fake_project: MagicMock,
):
    project_repo.create.return_value = fake_project

    result = await project_service.create_project("My Project", "Desc", owner)

    project_repo.create.assert_called_once_with(
        name="My Project", description="Desc", owner_id=owner.id
    )

    project_access_repo.create.assert_called_once_with(
        project_id=fake_project.id, user_id=owner.id, role=ProjectRole.OWNER
    )

    assert result is fake_project


async def test_create_project_creates_project_with_no_description(
    project_service: ProjectService,
    project_repo: AsyncMock,
    project_access_repo: AsyncMock,
    owner: MagicMock,
    fake_project: MagicMock,
):
    fake_project.description = None

    project_repo.create.return_value = fake_project

    result = await project_service.create_project(
        name=fake_project.name, description=fake_project.description, owner=owner
    )

    project_repo.create.assert_awaited_once_with(
        name=fake_project.name, description=fake_project.description, owner_id=owner.id
    )

    project_access_repo.create.assert_awaited_once_with(
        project_id=fake_project.id, user_id=owner.id, role=ProjectRole.OWNER
    )

    assert result.name == fake_project.name
    assert result.description is None


async def test_list_project_for_user_returns_projects_from_access_entries(
    project_service: ProjectService, project_access_repo: AsyncMock
):
    user_id = uuid.uuid4()
    project_1 = MagicMock()
    project_2 = MagicMock()

    entry_1 = MagicMock(project=project_1)
    entry_2 = MagicMock(project=project_2)

    project_access_repo.list_project_for_user.return_value = [entry_1, entry_2]

    result = await project_service.list_projects_for_user(user_id=user_id)

    project_access_repo.list_project_for_user.assert_awaited_once_with(user_id=user_id)
    assert result == [project_1, project_2]


async def test_list_project_returns_empty_list_when_no_entries(
    project_service: ProjectService, project_access_repo: AsyncMock
):
    user_id = uuid.uuid4()

    project_access_repo.list_project_for_user.return_value = []

    result = await project_service.list_projects_for_user(user_id=user_id)

    project_access_repo.list_project_for_user.assert_awaited_once_with(user_id=user_id)
    assert result == []


async def test_update_project_updates_existing_project(
    project_service: ProjectService, project_repo: AsyncMock, fake_project: MagicMock
):
    project_repo.get_by_id.return_value = fake_project
    updated_project = MagicMock()
    project_repo.update.return_value = updated_project

    result = await project_service.update_project(
        project_id=fake_project.id,
        name="Updated Name",
        description="Updated Description",
    )

    project_repo.get_by_id.assert_awaited_once_with(fake_project.id)
    project_repo.update.assert_awaited_once_with(
        project=fake_project, name="Updated Name", description="Updated Description"
    )

    assert result is updated_project


async def test_update_project_raises_not_found_when_project_missing(
    project_service: ProjectService, project_repo: AsyncMock
):
    project_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Project Not found"):
        await project_service.update_project(uuid.uuid4(), "name", "desc")

    project_repo.update.assert_not_awaited()


async def test_delete_project_deletes_existing_project(
    project_service: ProjectService, project_repo: AsyncMock, fake_project: MagicMock
):
    project_repo.get_by_id.return_value = fake_project

    await project_service.delete_project(fake_project.id)

    project_repo.get_by_id.assert_awaited_once_with(fake_project.id)
    project_repo.delete.assert_awaited_once_with(fake_project)


async def test_delete_project_raises_not_found_when_project_missing(
    project_service: ProjectService, project_repo: AsyncMock
):
    project_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Project Not found"):
        await project_service.delete_project(uuid.uuid4())

    project_repo.delete.assert_not_awaited()


async def test_invite_user_invites_new_user_succcesfully(
    project_service: ProjectService,
    user_repo: AsyncMock,
    project_access_repo: AsyncMock,
):
    project_id = uuid.uuid4()
    inviter_id = uuid.uuid4()
    target_user = MagicMock(id=uuid.uuid4())
    target_email = "test@example.com"

    user_repo.get_by_email.return_value = target_user
    project_access_repo.get.return_value = None

    await project_service.invite_user(
        project_id=project_id, target_email=target_email, inviter_id=inviter_id
    )

    user_repo.get_by_email.assert_awaited_once_with(target_email)
    project_access_repo.get.assert_awaited_once_with(
        project_id=project_id, user_id=target_user.id
    )
    project_access_repo.create.assert_called_once_with(
        project_id=project_id, user_id=target_user.id, role=ProjectRole.PARTICIPANT
    )


async def test_invite_user_raises_not_found_when_user_missing(
    project_service: ProjectService,
    user_repo: AsyncMock,
    project_access_repo: AsyncMock,
):
    user_repo.get_by_email.return_value = None

    with pytest.raises(NotFoundError, match="User with this email not found"):
        await project_service.invite_user(
            uuid.uuid4(), "test@example.com", uuid.uuid4()
        )

    project_access_repo.get.assert_not_awaited()
    project_access_repo.create.assert_not_awaited()


async def test_invite_user_raises_conflict_when_inviting_self(
    project_service: ProjectService,
    user_repo: AsyncMock,
    project_access_repo: AsyncMock,
):
    target_user = MagicMock(id=uuid.uuid4())

    user_repo.get_by_email.return_value = target_user

    with pytest.raises(ConflictError, match="Cannot invite yourself"):
        await project_service.invite_user(
            uuid.uuid4(), "test@example.com", target_user.id
        )

    project_access_repo.get.assert_not_awaited()
    project_access_repo.create.assert_not_awaited()


async def test_invite_user_does_no_operation_when_access_already_exists(
    project_service: ProjectService,
    user_repo: AsyncMock,
    project_access_repo: AsyncMock,
):
    user_repo.get_by_email.return_value = AsyncMock()
    project_access_repo.get.return_value = AsyncMock()

    await project_service.invite_user(uuid.uuid4(), "test@example.com", uuid.uuid4())

    project_access_repo.create.assert_not_awaited()
