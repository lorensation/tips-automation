from app.services.llm.mock_provider import MockProvider
from app.services.prediction_normalizer import normalize_prediction


def test_mock_provider_normalizes_simple_race_lines() -> None:
    result = normalize_prediction(
        MockProvider(),
        "HIPOTOUR",
        "1 carrera: 2-1-3\n2 carrera: 1-3-2",
        2,
        {1: [1, 2, 3], 2: [1, 2, 3]},
    )

    assert result.specialist == "HIPOTOUR"
    assert result.races[0].pick_1 == 2
    assert result.races[1].pick_3 == 2
