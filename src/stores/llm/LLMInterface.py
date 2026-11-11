from abc import ABC, abstractmethod
from typing import Any, Optional, Union, List


class LLMInterface(ABC):

    @abstractmethod
    def set_generation_model(self, model_id: str):
        raise NotImplementedError

    @abstractmethod
    def set_embedding_model(self, model_id: str, embedding_size: int):
        raise NotImplementedError

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        max_output_tokens: Optional[int | None] = None,
        temperature: Optional[float | None] = None,
        *args: Any,
        **kwargs: Any
    ):
        raise NotImplementedError

    @abstractmethod
    async def embed_text(
            self, prompts: Union[List, str],
            document_type: str | None = None,
            *args: Any,
            **kwargs: Any
    ):
        raise NotImplementedError

    @abstractmethod
    def construct_prompt(self, prompt: str, role: str, *args: Any, **kwargs: Any):
        raise NotImplementedError
