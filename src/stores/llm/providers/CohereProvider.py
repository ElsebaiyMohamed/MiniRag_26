import logging
from typing import Any, Union, List, Optional

import cohere

from models.enums import CohereEnum, DocumentTypeEnum
from models.schemas import LLMResult
from ..LLMInterface import LLMInterface


class CohereProvider(LLMInterface):
    def __init__(
        self,
        api_key: str,
        default_max_char: int = 1000,
        default_output_max_tokens: int = 1000,
        default_generation_temperature: float = 0.1,
            request_timeout_sec: float = 60.0,
    ):
        super().__init__()

        self.api_key = api_key
        self.default_max_char = default_max_char
        self.default_max_output_tokens = default_output_max_tokens
        self.default_generation_temperature = default_generation_temperature
        self.request_timeout_sec = request_timeout_sec
        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None
        self.enum = CohereEnum
        self.client: cohere.AsyncClientV2 | None = cohere.AsyncClientV2(
            api_key=self.api_key)
        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def _parse_response(self, operation: str, response: Any) -> Optional[dict]:
        """Cohere-specific response and usage token parser."""
        usage = getattr(response, "usage", None)
        tokens_obj = getattr(usage, "tokens", None) if usage else None

        prompt_tokens = getattr(tokens_obj, "input_tokens",
                                None) if tokens_obj else None
        completion_tokens = getattr(tokens_obj, "output_tokens",
                                    None) if tokens_obj else None

        if prompt_tokens is None and usage:
            billed = getattr(usage, "billed_units", None)
            prompt_tokens = getattr(billed, "input_tokens", None) if billed else None
            completion_tokens = getattr(billed, "output_tokens",
                                        None) if billed else None

        total_tokens = (
            (prompt_tokens + completion_tokens)
            if (prompt_tokens is not None and completion_tokens is not None)
            else None
        )

        if operation == "generate_text":
            message = getattr(response, "message", None)
            if not message:
                return None
            content_list = getattr(message, "content", None)
            if not content_list:
                return None
            first_content = content_list[0]
            text_content = (
                first_content.get("text") if isinstance(first_content,
                                                        dict) else getattr(
                    first_content, "text", None)
            )
            if text_content is None:
                return None
            return {
                "content": text_content,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            }

        elif operation == "embed_text":
            embeddings = getattr(response, "embeddings", None)
            if embeddings is None:
                return None
            vectors = getattr(embeddings, "float", None)
            if not vectors:
                return None
            if self.embedding_size and any(
                    len(v) != self.embedding_size for v in vectors):
                self.logger.error(
                    f"Embedding vector dimension {len(vectors)} mismatch against "
                    f"configuration {self.embedding_size}")

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
            self.logger.error("Cohere client was not set")
            return LLMResult(
                content=None,
                provider="cohere",
                model="unknown",
                operation="generate_text",
                latency_ms=0.0,
                success=False,
                error_message="Cohere client not set",
            )
        if self.generation_model_id is None:
            self.logger.error("Generation model for Cohere not set")
            return LLMResult(
                content=None,
                provider="cohere",
                model="unspecified",
                operation="generate_text",
                latency_ms=0.0,
                success=False,
                error_message="Generation model not set",
            )

        max_output_tokens = max_output_tokens if max_output_tokens is not None else self.default_max_output_tokens
        temperature = temperature if temperature is not None else self.default_generation_temperature
        chat_history: list = kwargs.get("chat_history", [])

        messages = chat_history.copy() if chat_history else []
        messages.append(self.construct_prompt(prompt=prompt, role=self.enum.USER.value))

        async def _call():
            return await self.client.chat(
                model=self.generation_model_id, messages=messages,
                max_tokens=max_output_tokens, temperature=temperature
            )

        return await self._safe_call(
            operation="generate_text", provider_name="cohere",
            model_id=self.generation_model_id, func=_call
        )

    async def embed_text(
            self, prompts: Union[List, str], document_type: str | None = None,
            *args: Any, **kwargs: Any
    ) -> LLMResult:
        if self.client is None:
            self.logger.error("Cohere client was not set")
            return LLMResult(
                content=None,
                provider="cohere",
                model="unknown",
                operation="embed_text",
                latency_ms=0.0,
                success=False,
                error_message="Cohere client not set",
            )
        if self.embedding_model_id is None:
            self.logger.error("Embedding model for cohere not set")
            return LLMResult(
                content=None,
                provider="cohere",
                model="unspecified",
                operation="embed_text",
                latency_ms=0.0,
                success=False,
                error_message="Embedding model not set",
            )

        input_type = CohereEnum.DOCUMENT.value
        if document_type == DocumentTypeEnum.QUERY.value:
            input_type = CohereEnum.QUERY.value

        single = isinstance(prompts, str)
        texts = [self.process_text(prompts)] if single else [self.process_text(t) for t in prompts]

        async def _call():
            return await self.client.embed(
                model=self.embedding_model_id,
                texts=texts,
                input_type=input_type,
                output_dimension = self.embedding_size,
                embedding_types=["float"],
            )

        result = await self._safe_call(
            operation="embed_text", provider_name="cohere",
            model_id=self.embedding_model_id, func=_call
        )

        # If a single string was passed, unwrap the first item from the vectors list content
        if result and result.success and single and isinstance(result.content,
                                                               list) and len(
                result.content) > 0:
            result.content = result.content[0]

        return result

    def construct_prompt(self, prompt: str, role: str, *args: Any, **kwargs: Any):
        return {"role": role, "content": self.process_text(prompt)}

    def process_text(self, prompt: str):
        return prompt
