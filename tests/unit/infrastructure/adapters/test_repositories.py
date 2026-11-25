
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from application.errors import AssetAlreadyExists
from application.ports import NewAsset
from infrastructure.adapters import repositories


class FakeDatabaseError(Exception):
    def __init__(self, constraint_name):
        super().__init__("database integrity violation")
        self.diag = SimpleNamespace(
            constraint_name=constraint_name
        )


def build_asset():
    return NewAsset(
        project_id=1,
        asset_type="text/plain",
        asset_name="document.txt",
        asset_size=100,
        asset_status=0,
    )


def build_integrity_error(constraint_name):
    original_error = FakeDatabaseError(constraint_name)

    error = IntegrityError(
        "INSERT INTO assets ...",
        {},
        original_error,
    )

    return error


@pytest.mark.asyncio
async def test_create_translates_duplicate_asset_constraint(
    monkeypatch,
):
    integrity_error = build_integrity_error(
        "uq_assets_project_asset_name"
    )

    async def fake_create_asset(asset):
        raise integrity_error

    monkeypatch.setattr(
        repositories,
        "AssetDataModel",
        lambda db_client: SimpleNamespace(
            create_asset=fake_create_asset
        ),
    )

    repository = repositories.SqlAlchemyAssetRepository(
        db_client=object()
    )

    with pytest.raises(AssetAlreadyExists) as exc_info:
        await repository.create(build_asset())

    assert exc_info.value.__cause__ is integrity_error


@pytest.mark.asyncio
async def test_create_reraises_unrelated_integrity_error(
    monkeypatch,
):
    integrity_error = build_integrity_error(
        "some_other_constraint"
    )

    async def fake_create_asset(asset):
        raise integrity_error

    monkeypatch.setattr(
        repositories,
        "AssetDataModel",
        lambda db_client: SimpleNamespace(
            create_asset=fake_create_asset
        ),
    )

    repository = repositories.SqlAlchemyAssetRepository(
        db_client=object()
    )

    with pytest.raises(IntegrityError) as exc_info:
        await repository.create(build_asset())

    assert exc_info.value is integrity_error
