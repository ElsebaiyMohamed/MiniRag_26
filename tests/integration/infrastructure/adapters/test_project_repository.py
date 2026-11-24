
import pytest
from sqlalchemy import func, select

from infrastructure.adapters.repositories import SqlAlchemyProjectRepository
from models.db_schemas import Project


@pytest.mark.asyncio
async def test_get_or_create_returns_existing_project(pgvector_session_factory):
    async with pgvector_session_factory() as session:
        existing_project = Project(project_id=42)
        session.add(existing_project)
        await session.commit()
        original_uuid = existing_project.project_uuid

    repository = SqlAlchemyProjectRepository(pgvector_session_factory)

    project_id = await repository.get_or_create(42)

    assert project_id == 42

    async with pgvector_session_factory() as session:
        persisted_project = await session.get(Project, 42)

        count = await session.scalar(
            select(func.count()).select_from(Project).where(
                Project.project_id == 42
            )
        )

    assert persisted_project is not None
    assert persisted_project.project_uuid == original_uuid
    assert count == 1


@pytest.mark.asyncio
async def test_get_or_create_creates_missing_project(pgvector_session_factory):
    repository = SqlAlchemyProjectRepository(pgvector_session_factory)

    first_project_id = await repository.get_or_create(43)

    assert first_project_id == 43

    async with pgvector_session_factory() as session:
        created_project = await session.get(Project, 43)

    assert created_project is not None
    assert created_project.project_id == 43
    assert created_project.project_uuid is not None

    original_uuid = created_project.project_uuid

    # Calling get_or_create again must return the existing project.
    second_project_id = await repository.get_or_create(43)

    assert second_project_id == 43

    async with pgvector_session_factory() as session:
        persisted_project = await session.get(Project, 43)

        count = await session.scalar(
            select(func.count()).select_from(Project).where(
                Project.project_id == 43
            )
        )

    assert persisted_project is not None
    assert persisted_project.project_uuid == original_uuid
    assert count == 1
