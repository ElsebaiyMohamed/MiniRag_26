
class IngestFileError(Exception):
    """Base exception for file ingestion failures."""


class UnsupportedUploadType(IngestFileError):
    """The extension or MIME type is not supported."""


class UploadTooLarge(IngestFileError):
    """The uploaded file exceeds the configured size limit."""


class FileStorageError(IngestFileError):
    """The uploaded file could not be stored."""
