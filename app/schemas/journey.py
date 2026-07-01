from datetime import date

from pydantic import BaseModel


class JourneyCreate(BaseModel):
    date: date
    venue: str


class JourneySummary(BaseModel):
    id: str
    date: date
    venue: str
    status: str
