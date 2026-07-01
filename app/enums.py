from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    EDITOR = "editor"


class JourneyStatus(StrEnum):
    DRAFT = "draft"
    PDF_UPLOADED = "pdf_uploaded"
    PARTANT_EXTRACTED = "partant_extracted"
    PARTANT_CONFIRMED = "partant_confirmed"
    PREDICTIONS_IN_PROGRESS = "predictions_in_progress"
    PREDICTIONS_VALID = "predictions_valid"
    OUTPUTS_GENERATED = "outputs_generated"
    OUTPUTS_REVIEWED = "outputs_reviewed"
    DRIVE_UPLOADED = "drive_uploaded"
    EMAIL_SENT = "email_sent"
    BLOCKED = "blocked"


class PredictionStatus(StrEnum):
    MISSING = "missing"
    RAW_SAVED = "raw_saved"
    NORMALIZED = "normalized"
    VALIDATION_FAILED = "validation_failed"
    REQUIRES_REVIEW = "requires_review"
    VALID = "valid"


class OutputType(StrEnum):
    TIPS_EXCEL = "tips_excel"
    PRONOSTICOS_PNG = "pronosticos_png"
    PRONOSTICOS_PDF = "pronosticos_pdf"


class OutputStatus(StrEnum):
    GENERATED = "generated"
    REVIEWED = "reviewed"
    UPLOADED = "uploaded"
    SENT = "sent"
    FAILED = "failed"


SPECIALIST_NAMES = [
    "EMILIO VILLAVERDE",
    "ESTEBAN ROMERA",
    "ANDER GALDONA",
    "PEDRO MERCADO",
    "JAVIER FERNANDEZ-CUESTA",
    "JOSÉ SOTO",
    "JOSE MANUEL FERNÁNDEZ",
    "HIPOTOUR",
]


VENUE_THEMES = {
    "HZ_MADRID": "blue",
    "HZ_NOCTURNAS": "black",
    "SAN_SEBASTIAN": "green",
    "DOS_HERMANAS": "orange",
    "SANLUCAR": "yellow",
    "PINEDA": "purple",
}
