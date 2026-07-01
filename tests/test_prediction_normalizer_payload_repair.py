from app.services.llm.base import LLMProvider
from app.services.prediction_normalizer import normalize_prediction


class LoosePayloadProvider(LLMProvider):
    provider_name = "loose"
    model_name = "loose-model"

    def structured_completion(self, system_prompt: str, user_prompt: str, schema: dict, temperature: float = 0.0, timeout_seconds: int = 45) -> dict:
        return {
            "especialista": "JOSÉ SOTO",
            "carreras": [
                {"carrera": 1, "picks": [2, 1, 3]},
                {"carrera": 2, "seleccion": "1-2-5"},
            ],
        }


def test_normalizer_repairs_common_non_schema_llm_payloads() -> None:
    result = normalize_prediction(
        LoosePayloadProvider(),
        "JOSÉ SOTO",
        "1 carrera\n2-1-3\n2 carrera\n1-2-5",
        2,
        {1: [1, 2, 3], 2: [1, 2, 5]},
    )

    assert result.specialist == "JOSÉ SOTO"
    assert result.races[0].pick_1 == 2
    assert result.races[1].pick_3 == 5
