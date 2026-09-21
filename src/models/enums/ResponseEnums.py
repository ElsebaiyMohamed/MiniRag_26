from enum import Enum

class ResponseSignal(Enum):
    FILE_VALIDATED_SUCCESS = 'file validated successed'
    FILE_TYPE_NOT_SUPPORTED = 'file type not supported'
    FILE_SIZE_EXCEEDED = 'file size exceeded'
    FILE_UPLOAD_FIALED = 'file upload failed'
    FILE_UPLOAD_SUCCESS = 'file upload successed'
    PROCESSING_FIALD = 'file chuncking failed'
    PROCESSING_SUCCESS = 'file chuncking success'
    NO_FILES_ERROR = 'project is empty'
