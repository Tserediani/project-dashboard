import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import project_dashboard.models  # noqa: F401
from project_dashboard.core.config import CONFIG
from project_dashboard.db.base import Base
from project_dashboard.db.session import get_session
from project_dashboard.main import app

TEST_DATABASE_NAME = f"{CONFIG.postgres.db.get_secret_value()}_test"


@pytest.fixture(scope="session", autouse=True)
async def create_test_database():
    admin_engine = create_async_engine(
        CONFIG.postgres.dsn_for("postgres"), isolation_level="AUTOCOMMIT"
    )
    async with admin_engine.connect() as conn:
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DATABASE_NAME}"'))
        await conn.execute(text(f'CREATE DATABASE "{TEST_DATABASE_NAME}"'))
    await admin_engine.dispose()

    yield

    admin_engine = create_async_engine(
        CONFIG.postgres.dsn_for("postgres"), isolation_level="AUTOCOMMIT"
    )
    async with admin_engine.connect() as conn:
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DATABASE_NAME}"'))
    await admin_engine.dispose()


@pytest.fixture
async def db_session(create_test_database):
    engine = create_async_engine(CONFIG.postgres.dsn_for(TEST_DATABASE_NAME))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_session] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
