
class UnsupportedFileType(Exception):
    """Raised when no registered loader supports a file extension."""
class UnsupportedFile(Exception):
    """Raised when a supported file format cannot be processed."""