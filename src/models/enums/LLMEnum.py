from enum import Enum

class LLMEnum(Enum):
    OPENAI = 'OPENAI'
    COHERE = 'COHERE'

class OpenAIEnum(Enum):
    SYSTEM = 'system'
    USER = 'user'
    ASSISTANT = 'assitant'

class CohereEnum(Enum):
    SYSTEM = 'SYSTEM'
    USER = 'USER'
    ASSISTANT = 'CHATBOT'

    DOCUMENT = 'search_document'
    QUERY = 'serach_query'
class DocumentTypeEnum(Enum):
    DOCUMENT = 'document'
    QUERY = 'query'
