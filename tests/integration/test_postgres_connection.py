
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.asyncio
async def test_postgres_connection():
    database_url = os.getenv("PGVECTOR_TEST_DATABASE_URL")

    assert database_url, (
        "PGVECTOR_TEST_DATABASE_URL is not configured. "
        "Set it before running PostgreSQL integration tests."
    )

    engine = create_async_engine(database_url)

    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            assert result.scalar_one() == 1

            extension = await connection.execute(
                text(
                    "SELECT EXISTS "
                    "(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                )
            )
            assert extension.scalar_one(), (
                "PostgreSQL is reachable, but the vector extension is not installed."
            )
    finally:
        await engine.dispose()
