from datetime import date

from app.enums import PredictionStatus
from app.models.journey import Journey
from app.models.participant import Participant
from app.models.prediction import Prediction, PredictionPick
from app.models.race import Race
from app.models.specialist import Specialist
from app.services.validation_engine import validate_partant, validate_prediction


def test_partant_detects_duplicate_participant_numbers() -> None:
    journey = Journey(date=date(2026, 7, 2), venue="HZ_NOCTURNAS", theme="black", season_year=2026)
    race = Race(race_number=1)
    race.participants = [
        Participant(number=1, horse_name="SKY HAWK"),
        Participant(number=1, horse_name="AÑOVER"),
    ]
    journey.races = [race]

    result = validate_partant(journey)

    assert not result.ok
    assert any("duplicado" in error.message for error in result.errors)


def test_prediction_rejects_missing_pick_number() -> None:
    journey = Journey(date=date(2026, 7, 2), venue="HZ_NOCTURNAS", theme="black", season_year=2026)
    race = Race(id="race-1", race_number=1)
    race.participants = [Participant(number=1, horse_name="UNO"), Participant(number=2, horse_name="DOS"), Participant(number=3, horse_name="TRES")]
    journey.races = [race]
    specialist = Specialist(name="HIPOTOUR", display_order=8)
    prediction = Prediction(specialist=specialist, status=PredictionStatus.NORMALIZED)
    prediction.picks = [PredictionPick(race_id="race-1", race_number=1, pick_1=1, pick_2=2, pick_3=9)]

    result = validate_prediction(journey, prediction)

    assert not result.ok
    assert any("no existe" in error.message for error in result.errors)
