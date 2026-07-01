from abc import ABC, abstractmethod


class LLMProvider(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    def structured_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        temperature: float = 0.0,
        timeout_seconds: int = 45,
    ) -> dict:
        raise NotImplementedError
