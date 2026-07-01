from app.enums import OutputStatus
from app.models.journey import Journey
from app.schemas.validation import ValidationErrorItem, ValidationResult
from app.services.validation_engine import can_generate_outputs


def can_review_outputs(journey: Journey) -> ValidationResult:
    if not journey.outputs:
        return ValidationResult(ok=False, errors=[ValidationErrorItem(scope="outputs", message="No hay archivos generados.")])
    return ValidationResult(ok=True)


def can_run_final_action(journey: Journey) -> ValidationResult:
    reviewed = [output for output in journey.outputs if output.status in {OutputStatus.REVIEWED, OutputStatus.UPLOADED, OutputStatus.SENT}]
    if len(reviewed) < 3:
        return ValidationResult(ok=False, errors=[ValidationErrorItem(scope="outputs", message="Los archivos deben estar revisados antes de acciones finales.")])
    return ValidationResult(ok=True)


def generation_blockers(journey: Journey) -> list[str]:
    return [error.message for error in can_generate_outputs(journey).errors]
