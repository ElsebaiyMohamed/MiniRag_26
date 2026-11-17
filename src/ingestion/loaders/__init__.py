from .base import DocumentLoader, LoadedDocument
from .pdf import PdfLoader
from .registry import LoaderRegistry
from .txt import TxtLoader


def create_default_loader_registry() -> LoaderRegistry:
    registry = LoaderRegistry()
    registry.register(TxtLoader())
    registry.register(PdfLoader())

    return registry


__all__ = [
    "DocumentLoader",
    "LoadedDocument",
    "LoaderRegistry",
    "TxtLoader",
    "PdfLoader",
    "create_default_loader_registry",
]