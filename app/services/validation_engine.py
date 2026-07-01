from collections import Counter

from app.enums import PredictionStatus, SPECIALIST_NAMES
from app.models.journey import Journey
from app.models.prediction import Prediction
from app.schemas.validation import ValidationErrorItem, ValidationResult


def validate_partant(journey: Journey) -> ValidationResult:
    errors: list[ValidationErrorItem] = []
    if not journey.races:
        errors.append(ValidationErrorItem(scope="journey", message="La jornada debe tener al menos una carrera."))
    race_numbers = [race.race_number for race in journey.races]
    for duplicate in _duplicates(race_numbers):
        errors.append(ValidationErrorItem(scope="journey", message=f"La carrera {duplicate} está duplicada.", race_number=duplicate))
    for race in journey.races:
        if not race.participants:
            errors.append(ValidationErrorItem(scope="race", race_number=race.race_number, message="La carrera no tiene participantes."))
        participant_numbers = [participant.number for participant in race.participants]
        for duplicate in _duplicates(participant_numbers):
            errors.append(ValidationErrorItem(scope="race", race_number=race.race_number, message=f"El participante nº {duplicate} está duplicado."))
        for participant in race.participants:
            if not participant.horse_name.strip():
                errors.append(ValidationErrorItem(scope="participant", race_number=race.race_number, message=f"El participante nº {participant.number} no tiene nombre."))
    return ValidationResult(ok=not errors, errors=errors)


def validate_prediction(journey: Journey, prediction: Prediction) -> ValidationResult:
    errors: list[ValidationErrorItem] = []
    specialist_name = prediction.specialist.name if prediction.specialist else None
    if specialist_name not in SPECIALIST_NAMES:
        errors.append(ValidationErrorItem(scope="specialist", specialist=specialist_name, message="Especialista no válido."))

    races_by_number = {race.race_number: race for race in journey.races}
    picks_by_race = {pick.race_number: pick for pick in prediction.picks}

    for race_number, race in races_by_number.items():
        pick = picks_by_race.get(race_number)
        if pick is None:
            errors.append(_prediction_error(specialist_name, race_number, "Faltan picks para esta carrera."))
            continue
        values = [pick.pick_1, pick.pick_2, pick.pick_3]
        if len(set(values)) != 3:
            errors.append(_prediction_error(specialist_name, race_number, "Hay picks duplicados en la misma carrera."))
        valid_numbers = {participant.number for participant in race.participants if participant.is_active}
        for field, value in zip(["pick_1", "pick_2", "pick_3"], values, strict=True):
            if value not in valid_numbers:
                valid = ", ".join(str(number) for number in sorted(valid_numbers))
                errors.append(
                    ValidationErrorItem(
                        scope="pick",
                        specialist=specialist_name,
                        race_number=race_number,
                        field=field,
                        message=f"{specialist_name} - Carrera {race_number}: el caballo nº {value} no existe. Participantes válidos: {valid}.",
                    )
                )

    extra_races = set(picks_by_race) - set(races_by_number)
    for race_number in sorted(extra_races):
        errors.append(_prediction_error(specialist_name, race_number, "La carrera no existe en el partant oficial."))

    return ValidationResult(ok=not errors, errors=errors)


def can_generate_outputs(journey: Journey, active_specialists_count: int = 8) -> ValidationResult:
    errors: list[ValidationErrorItem] = []
    partant = validate_partant(journey)
    errors.extend(partant.errors)
    if journey.partant_confirmed_at is None:
        errors.append(ValidationErrorItem(scope="journey", message="El partant debe estar confirmado."))
    valid_predictions = [prediction for prediction in journey.predictions if prediction.status == PredictionStatus.VALID]
    if len(valid_predictions) != active_specialists_count:
        errors.append(ValidationErrorItem(scope="journey", message=f"Faltan especialistas válidos: {len(valid_predictions)}/{active_specialists_count}."))
    return ValidationResult(ok=not errors, errors=errors)


def _duplicates(values: list[int]) -> list[int]:
    counts = Counter(values)
    return [value for value, count in counts.items() if count > 1]


def _prediction_error(specialist: str | None, race_number: int, message: str) -> ValidationErrorItem:
    return ValidationErrorItem(scope="prediction", specialist=specialist, race_number=race_number, message=message)
