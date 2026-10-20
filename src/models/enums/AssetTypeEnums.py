from enum import Enum

class AssetType(Enum):
    FILE = 'file'
    URL = 'url'

class AssetStatus(Enum):
    UPLOADED = 0
    CHUNKED = 1
    INDEXED = 2

