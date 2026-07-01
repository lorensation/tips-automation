from app.config import Settings
from app.services.llm.base import LLMProvider
from app.services.llm.groq_provider import GroqProvider
from app.services.llm.mock_provider import MockProvider
from app.services.llm.openrouter_provider import OpenRouterProvider


def build_llm_provider(settings: Settings) -> LLMProvider:
    provider = settings.llm_provider.lower()
    if provider == "mock":
        return MockProvider()
    if provider == "groq":
        return GroqProvider(settings.llm_api_key, settings.llm_base_url, settings.llm_model)
    if provider == "openrouter":
        return OpenRouterProvider(settings.llm_api_key, settings.llm_base_url, settings.llm_model)
    if settings.app_env == "local":
        return MockProvider()
    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")
