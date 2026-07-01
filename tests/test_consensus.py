from app.services.consensus import PickRow, calculate_consensus


def test_consensus_uses_weighted_picks_and_first_vote_tiebreak() -> None:
    picks = [
        PickRow(race_number=1, pick_1=2, pick_2=1, pick_3=3),
        PickRow(race_number=1, pick_1=1, pick_2=2, pick_3=3),
        PickRow(race_number=1, pick_1=2, pick_2=3, pick_3=1),
    ]

    assert calculate_consensus(picks)[1] == [2, 1, 3]
