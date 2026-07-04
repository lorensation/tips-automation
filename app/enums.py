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
    CUADRO_EXCEL = "cuadro_excel"


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


# Sheet name in the Tips template workbook for each venue.
VENUE_TIPS_SHEETS = {
    "HZ_MADRID": "HZ",
    "HZ_NOCTURNAS": "NOCTURNAS",
    "SAN_SEBASTIAN": "SS",
    "DOS_HERMANAS": "DH",
    "SANLUCAR": "SL",
    "PINEDA": "PIN",
}


# Gama de color por tema de sede (hex RRGGBB sin alfa): "dark" para cabeceras/
# título/consenso, "light" para bandas alternas. Compartida por el Excel del
# cuadro acumulativo y el cuadro visual PNG/PDF.
THEME_PALETTES = {
    "blue": {"dark": "2E74B5", "light": "DCE6F1"},
    "black": {"dark": "262626", "light": "D9D9D9"},
    "green": {"dark": "548235", "light": "E2EFDA"},
    "orange": {"dark": "C55A11", "light": "FBE5D6"},
    "yellow": {"dark": "BF8F00", "light": "FFF2CC"},
    "purple": {"dark": "7030A0", "light": "E6DFEC"},
}
