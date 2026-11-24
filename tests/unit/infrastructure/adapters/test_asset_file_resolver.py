import pytest

from infrastructure.adapters.asset_file_resolver import (
    LocalAssetFileResolver,
)


def test_resolves_asset_using_storage_directory(tmp_path):
    resolver = LocalAssetFileResolver(tmp_path)

    project_dir = tmp_path / "assets" / "files" / "10"
    project_dir.mkdir(parents=True)

    asset_path = project_dir / "abc_document.pdf"
    asset_path.write_text("test content")

    result = resolver.resolve(
        project_id=10,
        asset_name="abc_document.pdf",
    )

    assert result == asset_path.resolve()
    assert result.is_file()


def test_resolves_missing_asset_without_creating_it(tmp_path):
    resolver = LocalAssetFileResolver(tmp_path)

    result = resolver.resolve(
        project_id=10,
        asset_name="missing.txt",
    )

    assert result == (
        tmp_path / "assets" / "files" / "10" / "missing.txt"
    ).resolve()
    assert not result.exists()


@pytest.mark.parametrize(
    "asset_name",
    [
        "",
        ".",
        "..",
        "../outside.txt",
        "folder/file.txt",
        r"folder\file.txt",
    ],
)
def test_rejects_invalid_asset_names(tmp_path, asset_name):
    resolver = LocalAssetFileResolver(tmp_path)

    with pytest.raises(ValueError):
        resolver.resolve(
            project_id=10,
            asset_name=asset_name,
        )