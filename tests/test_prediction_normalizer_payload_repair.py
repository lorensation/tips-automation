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


class ListPayloadProvider(LLMProvider):
    provider_name = "list"
    model_name = "list-model"

    def structured_completion(self, system_prompt: str, user_prompt: str, schema: dict, temperature: float = 0.0, timeout_seconds: int = 45):
        return [
            {"carrera": 1, "picks": [5, 3, 2]},
            {"carrera": 2, "picks": [2, 5, 4]},
        ]


def test_normalizer_repairs_list_payloads_without_attribute_error() -> None:
    result = normalize_prediction(
        ListPayloadProvider(),
        "ESTEBAN ROMERA",
        "1) 5-3-2\n2) 2-5-4",
        2,
        {1: list(range(1, 8)), 2: list(range(1, 8))},
    )

    assert [(race.pick_1, race.pick_2, race.pick_3) for race in result.races] == [(5, 3, 2), (2, 5, 4)]


class BadStringProvider(LLMProvider):
    provider_name = "bad-string"
    model_name = "bad-string-model"

    def structured_completion(self, system_prompt: str, user_prompt: str, schema: dict, temperature: float = 0.0, timeout_seconds: int = 45):
        return "not json"


def test_normalizer_falls_back_to_text_parser_for_bad_string_payload() -> None:
    result = normalize_prediction(
        BadStringProvider(),
        "ESTEBAN ROMERA",
        "[10:25, 7/3/2026] Esteban Romera: 1) 5-3-2\n[10:25, 7/3/2026] Esteban Romera: 2) 2-5-4",
        2,
        {1: list(range(1, 8)), 2: list(range(1, 8))},
    )

    assert [(race.pick_1, race.pick_2, race.pick_3) for race in result.races] == [(5, 3, 2), (2, 5, 4)]
