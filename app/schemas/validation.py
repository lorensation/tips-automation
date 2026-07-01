from pydantic import BaseModel


class ValidationErrorItem(BaseModel):
    scope: str
    message: str
    race_number: int | None = None
    specialist: str | None = None
    field: str | None = None


class ValidationResult(BaseModel):
    ok: bool
    errors: list[ValidationErrorItem] = []
