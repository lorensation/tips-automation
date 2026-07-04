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


def test_mock_provider_normalizes_plain_triplets_by_line_order() -> None:
    result = normalize_prediction(
        MockProvider(),
        "JOSE MANUEL FERNÁNDEZ",
        "2-1-3\n2-5-1\n1-4-5\n2-3-1\n6-2-9",
        5,
        {race: list(range(1, 10)) for race in range(1, 6)},
    )

    assert [(race.pick_1, race.pick_2, race.pick_3) for race in result.races] == [
        (2, 1, 3),
        (2, 5, 1),
        (1, 4, 5),
        (2, 3, 1),
        (6, 2, 9),
    ]
    assert not result.requires_human_review


def test_mock_provider_normalizes_whatsapp_numbered_messages() -> None:
    result = normalize_prediction(
        MockProvider(),
        "ESTEBAN ROMERA",
        "\n".join(
            [
                "[11:36, 7/1/2026] Esteban Romera: 1) 1-3-2",
                "[11:36, 7/1/2026] Esteban Romera: 2) 2-1-5",
                "[11:36, 7/1/2026] Esteban Romera: 3) 1-4-2",
                "[11:37, 7/1/2026] Esteban Romera: 4) 1-6-2",
                "[11:37, 7/1/2026] Esteban Romera: 5) 4-2-8",
            ]
        ),
        5,
        {race: list(range(1, 10)) for race in range(1, 6)},
    )

    assert result.races[1].race_number == 2
    assert (result.races[1].pick_1, result.races[1].pick_2, result.races[1].pick_3) == (2, 1, 5)
    assert result.races[4].pick_3 == 8


def test_mock_provider_normalizes_whatsapp_with_date_time_noise_and_extra_lines() -> None:
    result = normalize_prediction(
        MockProvider(),
        "ESTEBAN ROMERA",
        "\n".join(
            [
                "[10:25, 7/3/2026] Esteban Romera: 1) 5-3-2",
                "[10:25, 7/3/2026] Esteban Romera: 2) 2-5-4",
                "[10:39, 7/3/2026] Esteban Romera: 3) 5-1-7",
                "[10:40, 7/3/2026] Esteban Romera: 4) 3-8-1",
                "[10:40, 7/3/2026] Esteban Romera: Y",
                "[10:40, 7/3/2026] Esteban Romera: 5) 4-7-9",
                "[10:40, 7/3/2026] Esteban Romera: Saludos",
            ]
        ),
        5,
        {race: list(range(1, 15)) for race in range(1, 6)},
    )

    assert [(race.pick_1, race.pick_2, race.pick_3) for race in result.races] == [
        (5, 3, 2),
        (2, 5, 4),
        (5, 1, 7),
        (3, 8, 1),
        (4, 7, 9),
    ]


def test_mock_provider_normalizes_named_horse_lines() -> None:
    result = normalize_prediction(
        MockProvider(),
        "EMILIO VILLAVERDE",
        "\n".join(
            [
                "1. DUKES OF HAATHER. 1-3-2",
                "2. ARISTOCRATA. 1-2-5",
                "3. CHEAPER. 4-1-5",
                "4: CHIQUITIN. 2-6-8",
                "5: MISSTIFLY. 3-1-5",
            ]
        ),
        5,
        {race: list(range(1, 10)) for race in range(1, 6)},
    )

    assert [(race.pick_1, race.pick_2, race.pick_3) for race in result.races] == [
        (1, 3, 2),
        (1, 2, 5),
        (4, 1, 5),
        (2, 6, 8),
        (3, 1, 5),
    ]


def test_mock_provider_normalizes_race_label_followed_by_triplet() -> None:
    result = normalize_prediction(
        MockProvider(),
        "JOSÉ SOTO",
        "\n".join(
            [
                "1 carrera",
                "2-1-3",
                "2 carrera",
                "1-2-5",
                "3 carrera",
                "4-1-5",
                "4 carrera",
                "2-1-6",
                "5 carrera",
                "6-2-9",
            ]
        ),
        5,
        {race: list(range(1, 10)) for race in range(1, 6)},
    )

    assert [(race.pick_1, race.pick_2, race.pick_3) for race in result.races] == [
        (2, 1, 3),
        (1, 2, 5),
        (4, 1, 5),
        (2, 1, 6),
        (6, 2, 9),
    ]
