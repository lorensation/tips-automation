from pathlib import Path

from app.config import Settings
from app.models.journey import Journey
from app.services.consensus import PickRow, calculate_consensus


def render_board_html(journey: Journey, settings: Settings) -> str:
    picks = [PickRow(pick.race_number, pick.pick_1, pick.pick_2, pick.pick_3) for prediction in journey.predictions for pick in prediction.picks]
    consensus = calculate_consensus(
        picks,
        settings.consensus_pick_1_points,
        settings.consensus_pick_2_points,
        settings.consensus_pick_3_points,
    )
    headers = "".join(f"<th>C{race.race_number}</th>" for race in journey.races)
    rows = []
    for prediction in sorted(journey.predictions, key=lambda item: item.specialist.display_order):
        pick_map = {pick.race_number: pick for pick in prediction.picks}
        cells = []
        for race in journey.races:
            pick = pick_map.get(race.race_number)
            cells.append(f"<td>{pick.pick_1}-{pick.pick_2}-{pick.pick_3}</td>" if pick else "<td>-</td>")
        rows.append(f"<tr><th>{prediction.specialist.name}</th>{''.join(cells)}</tr>")
    consensus_cells = "".join(f"<td>{'-'.join(map(str, consensus.get(race.race_number, [])))}</td>" for race in journey.races)
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #111; }}
    h1 {{ font-size: 28px; margin: 0 0 16px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ccc; padding: 8px 10px; text-align: center; }}
    th {{ background: #f3f4f6; }}
    .theme {{ border-top: 8px solid {journey.theme}; padding-top: 12px; }}
    .consensus th, .consensus td {{ font-weight: 700; background: #fff7d6; }}
  </style>
</head>
<body>
  <main class="theme">
    <h1>Pronósticos - {journey.venue} - {journey.date}</h1>
    <table>
      <thead><tr><th>Especialista</th>{headers}</tr></thead>
      <tbody>{''.join(rows)}<tr class="consensus"><th>Consenso</th>{consensus_cells}</tr></tbody>
    </table>
  </main>
</body>
</html>"""


def write_board_html(journey: Journey, settings: Settings, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_board_html(journey, settings), encoding="utf-8")
    return output_path


async def export_board_png_pdf(html_path: Path, png_path: Path, pdf_path: Path) -> tuple[Path, Path]:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1400, "height": 900}, device_scale_factor=2)
        await page.goto(html_path.resolve().as_uri())
        await page.screenshot(path=str(png_path), full_page=True)
        await page.pdf(path=str(pdf_path), format="A4", landscape=True, print_background=True)
        await browser.close()
    return png_path, pdf_path
