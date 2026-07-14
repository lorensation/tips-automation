import pytest

from app.services.llm.base import LLMProvider
from app.services.prediction_normalizer import REPAIR_SYSTEM_PROMPT, normalize_prediction


class ScriptedProvider(LLMProvider):
    provider_name = "scripted"
    model_name = "scripted-model"

    def __init__(self, responses: list) -> None:
        self.responses = list(responses)
        self.calls: list[str] = []

    def structured_completion(self, system_prompt: str, user_prompt: str, schema: dict, temperature: float = 0.0, timeout_seconds: int = 45):
        self.calls.append(system_prompt)
        if not self.responses:
            raise AssertionError("No quedan respuestas programadas")
        return self.responses.pop(0)


VALID_PAYLOAD = {
    "specialist": "HIPOTOUR",
    "races": [
        {"race_number": 1, "pick_1": 2, "pick_2": 1, "pick_3": 3, "confidence": 0.95, "notes": None},
        {"race_number": 2, "pick_1": 4, "pick_2": 5, "pick_3": 1, "confidence": 0.95, "notes": None},
    ],
    "requires_human_review": False,
    "global_confidence": 0.95,
}

GARBAGE = {"foo": "bar"}

EMPTY_RACES_PAYLOAD = {
    "specialist": "HIPOTOUR",
    "races": [],
    "requires_human_review": True,
    "global_confidence": 0.0,
}


def test_repair_retry_recovers_and_flags_review() -> None:
    provider = ScriptedProvider([GARBAGE, VALID_PAYLOAD])

    result = normalize_prediction(provider, "HIPOTOUR", "1) 2-1-3\n2) 4-5-1", 2, {1: [1, 2, 3], 2: [1, 4, 5]})

    assert len(provider.calls) == 2
    assert provider.calls[1] == REPAIR_SYSTEM_PROMPT
    assert [(race.pick_1, race.pick_2, race.pick_3) for race in result.races] == [(2, 1, 3), (4, 5, 1)]
    # Toda salida reparada exige revisión humana.
    assert result.requires_human_review is True


def test_double_failure_falls_back_to_text_parser_with_review() -> None:
    provider = ScriptedProvider([GARBAGE, GARBAGE])

    result = normalize_prediction(provider, "HIPOTOUR", "1) 2-1-3\n2) 4-5-1", 2, {1: [1, 2, 3], 2: [1, 4, 5]})

    assert len(provider.calls) == 2  # normalización + 1 reintento, no más
    assert [(race.pick_1, race.pick_2, race.pick_3) for race in result.races] == [(2, 1, 3), (4, 5, 1)]
    assert result.requires_human_review is True


def test_empty_races_payload_falls_back_to_text_parser() -> None:
    # groq falla y el reintento devuelve un payload válido pero SIN carreras:
    # no debe devolverse vacío, sino recuperar los picks con el parser determinista.
    provider = ScriptedProvider([GARBAGE, EMPTY_RACES_PAYLOAD])

    result = normalize_prediction(provider, "HIPOTOUR", "1) 2-1-3\n2) 4-5-1", 2, {1: [1, 2, 3], 2: [1, 4, 5]})

    assert [(race.pick_1, race.pick_2, race.pick_3) for race in result.races] == [(2, 1, 3), (4, 5, 1)]
    assert result.requires_human_review is True


def test_unusable_llm_and_unparseable_text_raises() -> None:
    provider = ScriptedProvider([GARBAGE, GARBAGE])

    with pytest.raises(ValueError):
        normalize_prediction(provider, "HIPOTOUR", "sin picks aquí", 2, {1: [1, 2, 3], 2: [1, 4, 5]})


def test_valid_first_response_needs_no_repair_and_no_review() -> None:
    provider = ScriptedProvider([VALID_PAYLOAD])

    result = normalize_prediction(provider, "HIPOTOUR", "1) 2-1-3\n2) 4-5-1", 2, {1: [1, 2, 3], 2: [1, 4, 5]})

    assert len(provider.calls) == 1
    assert result.requires_human_review is False
