from pathlib import Path

from .base import DocumentLoader
from ..exceptions import UnsupportedFileType


class LoaderRegistry:
    def __init__(self):
        self._loaders: dict[str, DocumentLoader] = {}

    def register(self, loader: DocumentLoader) -> None:
        for extension in loader.extensions:
            normalized_extension = extension.lower()

            if not normalized_extension.startswith("."):
                raise ValueError(
                    f"Loader extensions must start with '.': {extension}"
                )

            if normalized_extension in self._loaders:
                raise ValueError(
                    f"A loader is already registered for "
                    f"{normalized_extension}"
                )

            self._loaders[normalized_extension] = loader

    def for_path(self, path: Path) -> DocumentLoader:
        extension = path.suffix.lower()
        loader = self._loaders.get(extension)

        if loader is None:
            raise UnsupportedFileType(
                f"No loader registered for extension: {extension}"
            )

        return loader

    def supported_extensions(self) -> set[str]:
        return set(self._loaders.keys())

    def supported_mime_types(self) -> set[str]:
        return {
            mime_type.lower()
            for loader in self._loaders.values()
            for mime_type in loader.mime_types
        }