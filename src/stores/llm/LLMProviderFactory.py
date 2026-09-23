from models.enums import LLMEnum
from .providers import OpenAiProvider, CohereProvider




class LLMProviderFactory:
    def __init__(self, config: dict):
        self.config = config
    def create(self, provider: str):
        if provider == LLMEnum.OPENAI.value:
            return OpenAiProvider(
                api_key=self.config.OPENAI_API_KEY,
                api_url=self.config.OPENAI_API_URL,
                default_max_char=self.config.INPUT_DEFAULT_MAX_CHAR,
                default_output_max_tokens=self.config.DEAFAULT_MAX_OUTPUT_TOKENS,
                default_generation_temperature=self.config.GENERATION_DEFAULT_TEMPERATURE
            )
        elif provider == LLMEnum.COHERE.value:
            return CohereProvider(
                api_key=self.config.COHERE_API_KEY,
                default_max_char=self.config.INPUT_DEFAULT_MAX_CHAR,
                default_output_max_tokens=self.config.DEAFAULT_MAX_OUTPUT_TOKENS,
                default_generation_temperature=self.config.GENERATION_DEFAULT_TEMPERATURE
            )
        else:
            return None
