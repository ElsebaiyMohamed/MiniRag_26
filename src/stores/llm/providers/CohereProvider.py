import logging

import cohere

from ..LLMInterface import LLMInterface
from models.enums import CohereEnum, DocumentTypeEnum



class CohereProvider(LLMInterface):
    def __init__(self, api_key: str, default_max_char: int=1000, 
                default_output_max_tokens: int=1000, default_generation_temperature: float=0.1):
        super().__init__()
        
        self.api_key = api_key
        self.default_max_char = default_max_char
        self.default_max_output_tokens = default_output_max_tokens
        self.default_generation_temperature = default_generation_temperature
        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None
        
        self.client = cohere.Client(api_key=self.api_key)
        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def generate_text(self, prompt: str, max_output_tokens: int=None, temprature: float=None, *args, **kwargs):
        if self.client is None:
            self.logger.error("Cohere client was not set")
            return None
        if self.generation_model_id is None:
            self.logger.error("Generation model for Cohere not set")
            return None
        max_output_tokens = max_output_tokens if max_output_tokens is not None else self.default_max_output_tokens
        temprature = temprature if temprature is not None else self.default_generation_temperature
        chat_history: list = kwargs.get('chat_history', [])
        
        message = self.construct_prompt(prompt=prompt, role=CohereEnum.USER.value)
        
        response = self.client.chat(
            model=self.generation_model_id,
            chat_history=chat_history,
            message=message,
            max_tokens=max_output_tokens,
            temperature=temprature
        )
        
        if response is None or response.text:
            self.logger.error('unable to get response from provider')
            return None
        return response.text

    def embed_text(self, prompt: str, document_type: str=None, *args, **kwargs):
        if self.client is None:
            self.logger.error("Cohere client was not set")
            return None
        if self.embedding_model_id is None:
            self.logger.error("Embedding model for cohere not set")
            return None
        input_type = CohereEnum.DOCUMENT.value 
        if document_type == DocumentTypeEnum.QUERY.value:
            input_type = CohereEnum.QUERY.value
        
        response = self.client.embed(
            model=self.embedding_model_id,
            texts=[self.process_text(prompt)],
            input_type=input_type,
            embedding_types=['float']
        )
        
        if response is None or response.embeddings is None or not response.embeddings.float:
            self.logger.error('unable to get embeddings from provider')
            return None
        return response.embeddings.float[0]
    
    
    def construct_prompt(self, prompt: str, role: str, *args, **kwargs):
        return {
            'role': role,
            'text': self.process_text(prompt)
        }
    def process_text(self, prompot: str):
        return prompot[:self.default_max_char].strip()
