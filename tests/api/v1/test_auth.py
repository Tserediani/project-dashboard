from httpx import AsyncClient

PREFIX = "/auth"


async def test_register_new_user(client: AsyncClient):
    response = await client.post(
        f"{PREFIX}/register",
        json={
            "email": "test@example.com",
            "password": "password!123",
            "repeat_password": "password!123",
        },
    )
    assert response.status_code == 201
    body = response.json()

    assert body["email"] == "test@example.com"
    assert "hashed_password" not in body


async def test_register_duplicate_email_fails(client: AsyncClient):
    payload = {
        "email": "dup@example.com",
        "password": "password!123",
        "repeat_password": "password!123",
    }

    await client.post(f"{PREFIX}/register", json=payload)

    response = await client.post(f"{PREFIX}/register", json=payload)

    assert response.status_code == 409


async def test_register_password_mismatch_fails(client: AsyncClient):
    payload = {
        "email": "test@example.com",
        "password": "password!123",
        "repeat_password": "password123",
    }

    response = await client.post(f"{PREFIX}/register", json=payload)

    assert response.status_code == 422


async def test_register_invalid_email_fails(client: AsyncClient):
    response = await client.post(
        f"{PREFIX}/register",
        json={
            "email": "not-an-email",
            "password": "password!123",
            "repeat_password": "password!123",
        },
    )

    assert response.status_code == 422


async def test_login_success(client: AsyncClient):
    payload = {
        "email": "test@example.com",
        "password": "password!123",
        "repeat_password": "password!123",
    }
    await client.post(f"{PREFIX}/register", json=payload)

    response = await client.post(
        f"{PREFIX}/login",
        data={"username": "test@example.com", "password": "password!123"},
    )
    body = response.json()

    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password_fails(client: AsyncClient):
    payload = {
        "email": "test@example.com",
        "password": "password!123",
        "repeat_password": "password!123",
    }
    await client.post(f"{PREFIX}/register", json=payload)

    response = await client.post(
        f"{PREFIX}/login",
        data={"username": "test@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 403


async def test_login_nonexistent_user_fails(client: AsyncClient):
    response = await client.post(
        f"{PREFIX}/login",
        data={"username": "test@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 403
