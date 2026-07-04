from app.services.pdf_parser import _clean_participant_name, _deduplicate_races, _parse_text_partant
from app.schemas.partant import ParsedParticipant, ParsedRace


def test_clean_participant_name_removes_country_codes_right_numbers_and_age() -> None:
    assert _clean_participant_name("SMOOTH TRANSITION (IRE) (5) 5 años") == "SMOOTH TRANSITION"
    assert _clean_participant_name("CHIQUITIN (IRE) (5)(8) 5 años") == "CHIQUITIN"
    assert _clean_participant_name("RAPTOR MAXIMUS (IRE) 5(8) 4 años") == "RAPTOR MAXIMUS"
    assert _clean_participant_name("BIG BAD WOLF (IRE) (4)(6)(8) 6 años") == "BIG BAD WOLF"


def test_parse_partant_keeps_left_number_and_clean_name_only() -> None:
    parsed = _parse_text_partant(
        """
        1ª CARRERA Premio Test
        Nº CABALLO EDAD
        1 SMOOTH TRANSITION (IRE) (5) 5 años
        2 CHIQUITIN (IRE) (5)(8) 5 años
        """
    )

    assert parsed[0].participants[0].number == 1
    assert parsed[0].participants[0].horse_name == "SMOOTH TRANSITION"
    assert parsed[0].participants[0].jockey is None
    assert parsed[0].participants[0].trainer is None
    assert parsed[0].participants[1].number == 2
    assert parsed[0].participants[1].horse_name == "CHIQUITIN"


def test_parse_partant_supports_masculine_ordinal_race_headers() -> None:
    parsed = _parse_text_partant(
        """
        1º CARRERA PREMIO TEST
        1 CATCH THE SUN (FR) 2 58 M. FOREST C. ESPECTÁCULO H. PEREIRA 4 Debutante
        2 KATXORRO (IRE) (8) 2 58 J. ZAMBUDIO (57) C. MARTUL M. ALONSO R. 2 Debutante
        """
    )

    assert parsed[0].race_number == 1
    assert parsed[0].name == "PREMIO TEST"
    assert parsed[0].participants[0].horse_name == "CATCH THE SUN"
    assert parsed[0].participants[1].horse_name == "KATXORRO"


def test_parse_partant_supports_thousands_separator_in_distance() -> None:
    parsed = _parse_text_partant(
        """
        1º CARRERA PREMIO TEST
        10.500 Euros a repartir Distancia: 1.300 metros. Hora: 17:30
        1 CATCH THE SUN (FR) 2 58 M. FOREST C. ESPECTÁCULO H. PEREIRA 4 Debutante
        """
    )

    assert parsed[0].distance_meters == 1300
    assert parsed[0].scheduled_time == "17:30"


def test_parse_partant_does_not_create_duplicate_races_from_false_headings() -> None:
    parsed = _parse_text_partant(
        """
        5 CARRERA PREMIO REAL
        1 CABALLO UNO (IRE) 5 años
        5 CARRERA .
        5 CARRERA .
        """
    )

    assert [race.race_number for race in parsed] == [5]
    assert parsed[0].name == "PREMIO REAL"
    assert parsed[0].participants[0].horse_name == "CABALLO UNO"


def test_deduplicate_races_keeps_best_race_and_merges_participants() -> None:
    races = [
        ParsedRace(race_number=5, name="PREMIO REAL", participants=[ParsedParticipant(number=1, horse_name="UNO")]),
        ParsedRace(race_number=5, name=".", participants=[]),
        ParsedRace(race_number=5, name="PREMIO REAL", participants=[ParsedParticipant(number=2, horse_name="DOS")]),
    ]

    deduped = _deduplicate_races(races)

    assert len(deduped) == 1
    assert deduped[0].name == "PREMIO REAL"
    assert [participant.number for participant in deduped[0].participants] == [1, 2]
