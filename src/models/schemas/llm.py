from typing import Any, Optional

from pydantic import BaseModel, Field


class LLMResult(BaseModel):
    content: Any = Field(..., description="The generated text, embedding vector(s), or None if failed")
    provider: str = Field(..., description="The provider name, e.g., 'cohere'")
    model: str = Field(..., description="The exact model ID used")
    operation: str = Field(..., description="The operation performed: 'generate_text' or 'embed_text'")
    latency_ms: float = Field(..., description="Request latency in milliseconds")
    prompt_tokens: Optional[int] = Field(None, description="Number of input/prompt tokens consumed")
    completion_tokens: Optional[int] = Field(None, description="Number of output/completion tokens generated")
    total_tokens: Optional[int] = Field(None, description="Total tokens used")
    success: bool = Field(..., description="Boolean flag indicating if the operation succeeded")
    error_message: Optional[str] = Field(None, description="Detailed error message if the call failed")