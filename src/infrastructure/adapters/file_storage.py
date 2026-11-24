
import re
from pathlib import Path
from random import choices
from string import ascii_lowercase, digits

import aiofiles

from application.ports import UploadSource


class LocalFileStorage:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)

    async def store(
        self,
        project_id: int,
        original_filename: str,
        source: UploadSource,
        chunk_size: int,
    ) -> str:
        project_dir = self.base_dir / "assets" / "files" / str(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        stored_filename = self._generate_unique_filename(
            original_filename,
            project_dir,
        )

        file_path = project_dir / stored_filename

        async with aiofiles.open(file_path, "wb") as file:
            while content := await source.read(chunk_size):
                await file.write(content)

        return stored_filename

    @staticmethod
    def _generate_unique_filename(
        original_filename: str,
        project_dir: Path,
    ) -> str:
        clean_filename = re.sub(
            r"[^\w.]",
            "",
            original_filename.strip(),
        ).replace(" ", "_")

        length = 1

        while True:
            prefix = "".join(
                choices(ascii_lowercase + digits, k=length)
            )
            filename = f"{prefix}_{clean_filename}"

            if not (project_dir / filename).exists():
                return filename

            length += 1
