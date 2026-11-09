import os
import sys
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))


@pytest_asyncio.fixture
async def pgvector_session_factory():
    database_url = os.getenv("PGVECTOR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set PGVECTOR_TEST_DATABASE_URL to run PostgreSQL integration tests")

    from models.db_schemas.minirag26.schemas import SQLAlchemyBase

    schema_name = f"test_{uuid4().hex}"
    admin_engine = create_async_engine(database_url)
    engine = None

    try:
        async with admin_engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        engine = create_async_engine(
            database_url,
            connect_args={"server_settings": {"search_path": f"{schema_name},public"}},
        )
        async with engine.begin() as connection:
            await connection.run_sync(SQLAlchemyBase.metadata.create_all)

        yield async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
    finally:
        if engine is not None:
            await engine.dispose()
        async with admin_engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        await admin_engine.dispose()
