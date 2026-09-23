import logging

from openai import OpenAI


from ..LLMInterface import LLMInterface
from models.enums import OpenAIEnum



class OpenAiProvider(LLMInterface):
    def __init__(self, api_key: str, api_url: str= None, default_max_char: int=1000, 
                default_output_max_tokens: int=1000, default_generation_temperature: float=0.1):
        super().__init__()
        
        self.api_key = api_key
        self.api_url = api_url
        self.default_max_char = default_max_char
        self.default_max_output_tokens = default_output_max_tokens
        self.default_generation_temperature = default_generation_temperature
        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None
        self.client = OpenAI(api_key=self.api_key, base_url=self.api_url)
        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def generate_text(self, prompt: str, max_output_tokens: int=None, temprature: float=None, *args, **kwargs):
        if self.client is None:
            self.logger.error("OpenAi client was not set")
            return None
        if self.generation_model_id is None:
            self.logger.error("Generation model for OpenAi not set")
            return None
        max_output_tokens = max_output_tokens if max_output_tokens is not None else self.default_max_output_tokens
        temprature = temprature if temprature is not None else self.default_generation_temperature
        chat_history: list = kwargs.get('chat_history', [])
        chat_history.append(self.construct_prompt(prompt=prompt, role=OpenAIEnum.USER.value))
        
        response = self.client.chat.completions.create(
            model=self.generation_model_id,
            messages=chat_history,
            max_tokens=max_output_tokens,
            temperature=temprature
        )
        
        if response is None or response.choices is None or len(response.choices) == 0 or response.choices[0].message is None:
            self.logger.error('unable to get response from provider')
            return None
        return response.choices[0].message['content']

    def embed_text(self, prompt: str, document_type: str=None, *args, **kwargs):
        if self.client is None:
            self.logger.error("OpenAi client was not set")
            return None
        if self.embedding_model_id is None:
            self.logger.error("Embedding model for OpenAi not set")
            return None
        response = self.client.embeddings.create(model=self.embedding_model_id, input=prompt)
        
        if response is None or response.data is None or len(response.data) == 0 or response.data[0].embedding is None:
            self.logger.error('unable to get embeddings from provider')
            return None
        return response.data[0].embedding 
    
    
    def construct_prompt(self, prompt: str, role: str, *args, **kwargs):
        return {
            'role': role,
            'content': self.process_text(prompt)
        }
    def process_text(self, prompot: str):
        return prompot[:self.default_max_char].strip()
