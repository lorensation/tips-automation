from pydantic import BaseModel


class ParsedParticipant(BaseModel):
    number: int
    horse_name: str
    raw_name: str | None = None
    jockey: str | None = None
    trainer: str | None = None
    stall: int | None = None


class ParsedRace(BaseModel):
    race_number: int
    name: str | None = None
    scheduled_time: str | None = None
    distance_meters: int | None = None
    surface: str | None = None
    participants: list[ParsedParticipant]


class ParsedPartant(BaseModel):
    races: list[ParsedRace]
