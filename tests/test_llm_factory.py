from app.config import Settings
from app.services.llm.factory import build_llm_provider


def test_grokai_alias_uses_groq_provider() -> None:
    provider = build_llm_provider(
        Settings(
            llm_provider="grokai",
            llm_base_url="https://api.groq.com/openai/v1",
            llm_api_key="dummy",
            llm_model="openai/gpt-oss-20b",
        )
    )

    assert provider.provider_name == "groq"
