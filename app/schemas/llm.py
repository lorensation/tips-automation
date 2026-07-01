from pydantic import BaseModel, Field


class NormalizedRacePick(BaseModel):
    race_number: int
    pick_1: int
    pick_2: int
    pick_3: int
    confidence: float = Field(ge=0, le=1)
    notes: str | None = None


class NormalizedPrediction(BaseModel):
    specialist: str
    races: list[NormalizedRacePick]
    requires_human_review: bool = False
    global_confidence: float | None = Field(default=None, ge=0, le=1)


NORMALIZED_PREDICTION_SCHEMA = {
    "type": "object",
    "required": ["specialist", "races", "requires_human_review"],
    "properties": {
        "specialist": {"type": "string"},
        "requires_human_review": {"type": "boolean"},
        "global_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "races": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["race_number", "pick_1", "pick_2", "pick_3", "confidence"],
                "properties": {
                    "race_number": {"type": "integer"},
                    "pick_1": {"type": "integer"},
                    "pick_2": {"type": "integer"},
                    "pick_3": {"type": "integer"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "notes": {"type": ["string", "null"]},
                },
            },
        },
    },
}
