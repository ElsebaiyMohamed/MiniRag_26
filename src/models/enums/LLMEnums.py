from enum import Enum

class LLMEnum(Enum):
    OPENAI = 'OPENAI'
    COHERE = 'COHERE'

class OpenAIEnum(Enum):
    SYSTEM = 'system'
    USER = 'user'
    ASSISTANT = 'assitant'

class CohereEnum(Enum):
    SYSTEM = 'system'
    USER = 'user'
    ASSISTANT = 'assistant'

    DOCUMENT = 'search_document'
    QUERY = 'search_query'
class DocumentTypeEnum(Enum):
    DOCUMENT = 'document'
    QUERY = 'query'
