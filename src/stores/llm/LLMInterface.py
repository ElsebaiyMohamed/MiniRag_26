from abc import ABC, abstractmethod



class LLMInterface(ABC):
    
    @abstractmethod()
    def set_generation_model(self, model_id: str):
        raise NotImplementedError
    
    @abstractmethod()
    def set_embedding_model(self, model_id: str):
        raise NotImplementedError
    
    @abstractmethod()
    def generate_text(self, prompt: str, max_output_tokins: int, temprature: float=None, *args, **kwargs):
        raise NotImplementedError
    
    @abstractmethod()
    def embed_text(self, prompt: str, document_type: str, *args, **kwargs):
        raise NotImplementedError
    
    @abstractmethod()
    def construct_prompt(self, prompt: str, role: str, *args, **kwargs):
        raise NotImplementedError
    
