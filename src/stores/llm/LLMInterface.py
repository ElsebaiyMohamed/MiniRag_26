import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine, Optional, Union, List

from models.schemas import LLMResult


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
            **kwargs: Any,
    ) -> LLMResult:
        raise NotImplementedError

    @abstractmethod
    async def embed_text(
            self, prompts: Union[List[str], str], document_type: str | None = None,
            *args: Any, **kwargs: Any
    ) -> LLMResult:
        raise NotImplementedError

    @abstractmethod
    def construct_prompt(self, prompt: str, role: str, *args: Any, **kwargs: Any):
        raise NotImplementedError

    @abstractmethod
    def _parse_response(self, operation: str, response: Any) -> Optional[dict]:
        """
        Provider-level parser to extract content, prompt_tokens, completion_tokens,
        and total_tokens based on the provider's specific SDK response schema.
        Must return a dict: {"content": ..., "prompt_tokens": ..., "completion_tokens": ..., "total_tokens": ...}
        or raise/return validation failures.
        """
        raise NotImplementedError


    async def _safe_call(
        self,
        operation: str,
        provider_name: str,
        model_id: Optional[str],
        func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> LLMResult:
        logger = getattr(self, "logger", logging.getLogger(self.__class__.__name__))
        timeout_sec = getattr(self, "request_timeout_sec", 60.0)
        resolved_model = model_id or "unknown"

        start_time = time.perf_counter()
        try:
            raw_response = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_sec)
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            if raw_response is None:
                logger.error(
                    "Received null response from provider API",
                    extra={
                        "provider": provider_name,
                        "model": resolved_model,
                        "operation": operation,
                        "error_type": "NullResponse",
                        "latency_ms": round(latency_ms, 2),
                    },
                )
                return LLMResult(
                    content=None,
                    provider=provider_name,
                    model=resolved_model,
                    operation=operation,
                    latency_ms=round(latency_ms, 2),
                    success=False,
                    error_message="Received null response from provider API",
                )

            # Delegate parsing and usage extraction entirely to the provider level
            parsed_data = self._parse_response(operation, raw_response)
            if parsed_data is None or parsed_data.get("content") is None:
                logger.error(
                    "Failed to parse or validate response shape from provider",
                    extra={
                        "provider": provider_name,
                        "model": resolved_model,
                        "operation": operation,
                        "error_type": "InvalidResponseShape",
                        "latency_ms": round(latency_ms, 2),
                    },
                )
                return LLMResult(
                    content=None,
                    provider=provider_name,
                    model=resolved_model,
                    operation=operation,
                    latency_ms=round(latency_ms, 2),
                    success=False,
                    error_message="Invalid response shape or parsing failed",
                )

            prompt_tokens = parsed_data.get("prompt_tokens")
            completion_tokens = parsed_data.get("completion_tokens")
            total_tokens = parsed_data.get("total_tokens") or (
                (prompt_tokens + completion_tokens)
                if (prompt_tokens is not None and completion_tokens is not None)
                else None
            )

            logger.info(
                "LLM provider call succeeded",
                extra={
                    "provider": provider_name,
                    "model": resolved_model,
                    "operation": operation,
                    "latency_ms": round(latency_ms, 2),
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                },
            )

            return LLMResult(
                content=parsed_data["content"],
                provider=provider_name,
                model=resolved_model,
                operation=operation,
                latency_ms=round(latency_ms, 2),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                success=True,
            )

        except asyncio.TimeoutError:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                "LLM provider request timed out",
                extra={
                    "provider": provider_name,
                    "model": resolved_model,
                    "operation": operation,
                    "error_type": "APITimeoutError",
                    "latency_ms": round(latency_ms, 2),
                },
                exc_info=True,
            )
            return LLMResult(
                content=None,
                provider=provider_name,
                model=resolved_model,
                operation=operation,
                latency_ms=round(latency_ms, 2),
                success=False,
                error_message="Provider Request timed out",
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            error_type = e.__class__.__name__
            logger.error(
                f"LLM provider call failed with exception: {error_type}",
                extra={
                    "provider": provider_name,
                    "model": resolved_model,
                    "operation": operation,
                    "error_type": error_type,
                    "latency_ms": round(latency_ms, 2),
                },
                exc_info=True,
            )
            return LLMResult(
                content=None,
                provider=provider_name,
                model=resolved_model,
                operation=operation,
                latency_ms=round(latency_ms, 2),
                success=False,
                error_message=f"{error_type}",
            )
