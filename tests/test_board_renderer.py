from datetime import date

from app.config import Settings
from app.enums import SPECIALIST_NAMES
from app.models.journey import Journey
from app.models.participant import Participant
from app.models.prediction import Prediction, PredictionPick
from app.models.race import Race
from app.models.specialist import Specialist
from app.services.board_renderer import render_board_html


def make_journey(n_races: int = 2) -> Journey:
    journey = Journey(date=date(2026, 7, 5), venue="SAN_SEBASTIAN", theme="green", season_year=2026)
    for race_number in range(1, n_races + 1):
        race = Race(race_number=race_number)
        race.participants = [Participant(number=i, horse_name=f"HORSE{i}") for i in range(1, 13)]
        journey.races.append(race)
    for index, name in enumerate(SPECIALIST_NAMES):
        prediction = Prediction()
        prediction.specialist = Specialist(name=name, display_order=index + 1)
        prediction.picks = [
            PredictionPick(race_number=race_number, pick_1=5, pick_2=3, pick_3=2)
            for race_number in range(1, n_races + 1)
        ]
        journey.predictions.append(prediction)
    return journey


def test_board_replicates_template_structure() -> None:
    html = render_board_html(make_journey(), Settings())

    assert "PRONÓSTICOS  ESPECIALISTAS" in html
    assert "ESPECIALISTAS" in html
    assert "1ª CARRERA" in html and "2ª CARRERA" in html
    # Nada de headers planos C1/C2 ni etiqueta "Consenso".
    assert ">C1<" not in html and ">C2<" not in html
    assert "Consenso" not in html


def test_board_uses_three_rows_per_specialist_with_official_horse_name() -> None:
    journey = make_journey(n_races=2)
    html = render_board_html(journey, Settings())

    # pick_1 como "CABALLO (N)" resuelto del partant, merged sobre las 3 filas.
    assert "HORSE5 (5)" in html
    # rowspan=3 en: orden + nombre + 1 celda de caballo por carrera, por especialista.
    assert html.count('rowspan="3"') == len(SPECIALIST_NAMES) * (2 + len(journey.races))
    # Etiquetas de orden solo para los tres primeros.
    assert ">1º<" in html and ">2º<" in html and ">3º<" in html
    assert ">4º<" not in html


def test_board_consensus_only_in_final_row() -> None:
    journey = make_journey(n_races=2)
    html = render_board_html(journey, Settings())

    # Todos pican 5-3-2 → consenso "5-3-2" una vez por carrera, y SOLO ahí:
    # las filas de especialista llevan los picks en celdas verticales separadas.
    assert html.count("5-3-2") == len(journey.races)
    assert 'class="consensus">5-3-2' in html


def test_board_uses_venue_palette() -> None:
    html = render_board_html(make_journey(), Settings())
    assert "#548235" in html  # verde SAN_SEBASTIAN
    assert "#E2EFDA" in html  # banda clara verde
