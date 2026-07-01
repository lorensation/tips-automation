from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class PickRow:
    race_number: int
    pick_1: int
    pick_2: int
    pick_3: int


def calculate_consensus(
    picks: list[PickRow],
    pick_1_points: int = 3,
    pick_2_points: int = 2,
    pick_3_points: int = 1,
) -> dict[int, list[int]]:
    scores: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    first_votes: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for pick in picks:
        scores[pick.race_number][pick.pick_1] += pick_1_points
        scores[pick.race_number][pick.pick_2] += pick_2_points
        scores[pick.race_number][pick.pick_3] += pick_3_points
        first_votes[pick.race_number][pick.pick_1] += 1
    result: dict[int, list[int]] = {}
    for race_number, race_scores in scores.items():
        ordered = sorted(
            race_scores,
            key=lambda horse_number: (-race_scores[horse_number], -first_votes[race_number][horse_number], horse_number),
        )
        result[race_number] = ordered[:3]
    return result
