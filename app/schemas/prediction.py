from pydantic import BaseModel


class ManualRacePick(BaseModel):
    race_number: int
    pick_1: int
    pick_2: int
    pick_3: int


class ManualPredictionInput(BaseModel):
    picks: list[ManualRacePick]
