import logging
from typing import Union, Any, List, Optional

from openai import AsyncOpenAI

from models.enums import OpenAIEnum
from models.schemas import LLMResult
from ..LLMInterface import LLMInterface


class OpenAiProvider(LLMInterface):
    def __init__(
        self,
        api_key: str,
        api_url: str | None = None,
        default_max_char: int = 1000,
        default_output_max_tokens: int = 1000,
        default_generation_temperature: float = 0.1,            request_timeout_sec: float = (60.0,)):
        super().__init__()

        self.api_key = api_key
        self.api_url = api_url if api_url else None
        self.default_max_char = default_max_char
        self.default_max_output_tokens = default_output_max_tokens
        self.default_generation_temperature = default_generation_temperature
        self.request_timeout_sec = request_timeout_sec
        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None
        self.enum = OpenAIEnum
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.api_url)
        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def _parse_response(self, operation: str, response: Any) -> Optional[dict]:
        """OpenAI-specific response and usage token parser."""
        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
        total_tokens = getattr(usage, "total_tokens", None) if usage else None

        if operation == "generate_text":
            choices = getattr(response, "choices", None)
            if not choices or len(choices) == 0:
                return None
            message = getattr(choices[0], "message", None)
            if not message:
                return None
            content = getattr(message, "content", None)
            if content is None:
                return None
            return {
                "content": content,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            }

        elif operation == "embed_text":
            data = getattr(response, "data", None)
            if not data or len(data) == 0:
                return None
            vectors = [getattr(d, "embedding", None) for d in data]
            if not vectors or any(v is None for v in vectors):
                return None
            if self.embedding_size and any(len(v) != self.embedding_size for v in vectors):
                self.logger.error("Embedding vector dimension mismatch against configuration")
                return None
            return {
                "content": vectors,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            }

        return None

    async def generate_text(
            self,
            prompt: str,
            max_output_tokens: int | None = None,
            temperature: float | None = None,
            *args: Any,
            **kwargs: Any
    ) -> LLMResult:
        if self.client is None:
            self.logger.error("OpenAi client was not set")
            return LLMResult(
                content=None,
                provider="openai",
                model="unknown",
                operation="generate_text",
                latency_ms=0.0,
                success=False,
                error_message="OpenAI client not set",
            )
        if self.generation_model_id is None:
            self.logger.error("Generation model for OpenAi not set")
            return LLMResult(
                content=None,
                provider="openai",
                model="unspecified",
                operation="generate_text",
                latency_ms=0.0,
                success=False,
                error_message="Generation model not set",
            )

        max_output_tokens = max_output_tokens if max_output_tokens is not None else self.default_max_output_tokens
        temperature = temperature if temperature is not None else self.default_generation_temperature
        chat_history: list = list(kwargs.get("chat_history", []))
        chat_history.append(self.construct_prompt(prompt=prompt, role=self.enum.USER.value))

        async def _call():
            return await self.client.chat.completions.create(
                model=self.generation_model_id,
                messages=chat_history,
                max_tokens=max_output_tokens,
                temperature=temperature,
            )

        return await self._safe_call(
            operation="generate_text", provider_name="openai", model_id=self.generation_model_id, func=_call
        )

    async def embed_text(
            self, prompts: Union[List[str], str], document_type: str | None = None,
            *args: Any, **kwargs: Any
    ) -> LLMResult:
        """
        Embeds one or a batch of text inputs.

        - **Single Input:** Receives a single `str` and returns a single embedding vector inside `LLMResult.content`.
        - **Batch Inputs:** Receives a `List[str]` and returns a list of embedding vectors inside `LLMResult.content`.
        """
        if self.client is None:
            self.logger.error("OpenAi client was not set")
            return LLMResult(
                content=None,
                provider="openai",
                model="unknown",
                operation="embed_text",
                latency_ms=0.0,
                success=False,
                error_message="OpenAI client not set",
            )
        if self.embedding_model_id is None:
            self.logger.error("Embedding model for OpenAi not set")
            return LLMResult(
                content=None,
                provider="openai",
                model="unspecified",
                operation="embed_text",
                latency_ms=0.0,
                success=False,
                error_message="Embedding model not set",
            )

        single = isinstance(prompts, str)
        texts = [self.process_text(prompts)] if single else [self.process_text(t) for t in prompts]

        async def _call():
            return await self.client.embeddings.create(model=self.embedding_model_id,
                                                       input=texts)

        result = await self._safe_call(
            operation="embed_text", provider_name="openai",
            model_id=self.embedding_model_id, func=_call
        )

        # If a single string was passed, unwrap the first vector from the content list while keeping telemetry intact
        if result and result.success and single and isinstance(result.content,
                                                               list) and len(
                result.content) > 0:
            result.content = result.content[0]

        return result

    def construct_prompt(self, prompt: str, role: str, *args: Any, **kwargs: Any):
        return {"role": role, "content": self.process_text(prompt)}

    def process_text(self, prompt: str):
        return prompt
