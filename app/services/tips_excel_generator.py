from collections import Counter
from pathlib import Path

from openpyxl import Workbook, load_workbook

from app.models.journey import Journey


def generate_tips_excel(journey: Journey, output_path: Path, template_path: Path | None = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if template_path and template_path.exists():
        wb = load_workbook(template_path)
        ws = wb.active
        ws.delete_rows(1, ws.max_row)
    else:
        wb = Workbook()
        ws = wb.active
    ws.title = "Tips"
    ws.append(["Carrera", "Caballo", "Número", "Votos pick_1"])
    for race in journey.races:
        votes = Counter()
        for prediction in journey.predictions:
            for pick in prediction.picks:
                if pick.race_number == race.race_number:
                    votes[pick.pick_1] += 1
        participants = {participant.number: participant.horse_name for participant in race.participants}
        for horse_number, count in sorted(votes.items(), key=lambda item: (-item[1], item[0])):
            ws.append([race.race_number, participants.get(horse_number, "DESCONOCIDO"), horse_number, count])
    wb.save(output_path)
    return output_path
