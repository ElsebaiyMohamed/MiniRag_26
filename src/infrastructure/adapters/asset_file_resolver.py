from pathlib import Path


class LocalAssetFileResolver:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)

    def resolve(self, project_id: int, asset_name: str) -> Path:
        if (
            not asset_name
            or asset_name in {".", ".."}
            or "/" in asset_name
            or "\\" in asset_name
        ):
            raise ValueError("Invalid asset name")

        project_dir = (
            self.base_dir / "assets" / "files" / str(project_id)
        ).resolve()

        file_path = (project_dir / asset_name).resolve()

        try:
            file_path.relative_to(project_dir)
        except ValueError:
            raise ValueError("Asset path escapes project directory")

        return file_path
