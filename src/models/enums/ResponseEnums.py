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
    PROJECT_NOT_FOUND = 'project not found'
    INSERT_INTO_VECTORDB_ERROR = 'failed to insert into vector database'
    INSERT_INTO_VECTOR_DATABASE_SUCCESS= 'insert into vector database success'
    VECTORDB_COLLECTION_INFO_RETRIVED = 'collection information retrived successfly'
    VECTORDB_SEARCH_ERROR = 'vectordb search error'
    VECTORDB_SEARCH_SUCCESS = 'vectordb search success'
    RAG_ANSWER_SUCCESS = 'rag answer success'
    RAG_ANSWER_ERROR = 'rag answer error'
