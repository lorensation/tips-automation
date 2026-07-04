"""Cuadro visual de pronósticos (HTML → PNG/PDF).

Replica la estructura y la gama de color de la hoja del cuadro oficial
(PRONOS 2026.xlsx): título "PRONÓSTICOS  ESPECIALISTAS", cabeceras
"1ª CARRERA"… de dos columnas, bloques de 3 filas por especialista (caballo
del pick_1 como "CABALLO (N)" + los 3 picks en vertical), bandas alternas
blanco/claro y fila de consenso "a-b-c" sin etiqueta.
"""

import base64
import logging
import zipfile
from html import escape
from pathlib import Path

from app.config import Settings
from app.enums import THEME_PALETTES
from app.models.journey import Journey
from app.services.consensus import PickRow, calculate_consensus

logger = logging.getLogger(__name__)

TITLE = "PRONÓSTICOS  ESPECIALISTAS"
ORDER_LABELS = {0: "1º", 1: "2º", 2: "3º"}
TEMPLATE_IMAGE_ENTRY = "xl/media/image1.jpeg"

_COL_ORDER_PX = 44
_COL_NAME_PX = 230
_COL_HORSE_PX = 180
_COL_PICK_PX = 48
_PRINTABLE_PX = 1060  # ancho útil aproximado de A4 apaisado a 96 dpi


def render_board_html(journey: Journey, settings: Settings) -> str:
    races = sorted(journey.races, key=lambda race: race.race_number)
    predictions = sorted(
        journey.predictions,
        key=lambda prediction: prediction.specialist.display_order if prediction.specialist else 99,
    )
    participants_by_race = {
        race.race_number: {participant.number: participant.horse_name for participant in race.participants}
        for race in races
    }
    consensus = calculate_consensus(
        [
            PickRow(pick.race_number, pick.pick_1, pick.pick_2, pick.pick_3)
            for prediction in predictions
            for pick in prediction.picks
        ],
        settings.consensus_pick_1_points,
        settings.consensus_pick_2_points,
        settings.consensus_pick_3_points,
    )
    palette = THEME_PALETTES.get(journey.theme, THEME_PALETTES["blue"])
    dark = f"#{palette['dark']}"
    light = f"#{palette['light']}"
    total_columns = 2 + 2 * len(races)
    table_width = _COL_ORDER_PX + _COL_NAME_PX + len(races) * (_COL_HORSE_PX + _COL_PICK_PX)
    print_zoom = min(1.0, _PRINTABLE_PX / table_width)

    colgroup = [f'<col style="width:{_COL_ORDER_PX}px"><col style="width:{_COL_NAME_PX}px">']
    for _ in races:
        colgroup.append(f'<col style="width:{_COL_HORSE_PX}px"><col style="width:{_COL_PICK_PX}px">')

    header_cells = ['<td class="head" colspan="2">ESPECIALISTAS</td>']
    for index in range(1, len(races) + 1):
        header_cells.append(f'<td class="head" colspan="2">{index}ª CARRERA</td>')

    body_rows: list[str] = []
    for spec_index, prediction in enumerate(predictions):
        band = "#FFFFFF" if spec_index % 2 == 0 else light
        pick_map = {pick.race_number: pick for pick in prediction.picks}
        specialist_name = escape(prediction.specialist.name) if prediction.specialist else "—"
        order_label = ORDER_LABELS.get(spec_index, "")
        order_style = (
            f"background:{dark};color:#fff;font-weight:700;" if order_label else f"background:{band};"
        )
        first_cells = [
            f'<td rowspan="3" class="order" style="{order_style}">{order_label}</td>',
            f'<td rowspan="3" class="name" style="background:{band};">{specialist_name}</td>',
        ]
        second_cells: list[str] = []
        third_cells: list[str] = []
        for race in races:
            pick = pick_map.get(race.race_number)
            if pick is None:
                horse_text, p1, p2, p3 = "—", "—", "—", "—"
            else:
                horse_name = participants_by_race[race.race_number].get(pick.pick_1)
                horse_text = f"{escape(horse_name)} ({pick.pick_1})" if horse_name else f"Nº {pick.pick_1}"
                p1, p2, p3 = pick.pick_1, pick.pick_2, pick.pick_3
            first_cells.append(f'<td rowspan="3" class="horse" style="background:{band};">{horse_text}</td>')
            first_cells.append(f'<td class="pick" style="background:{band};">{p1}</td>')
            second_cells.append(f'<td class="pick" style="background:{band};">{p2}</td>')
            third_cells.append(f'<td class="pick" style="background:{band};">{p3}</td>')
        body_rows.append(f"<tr>{''.join(first_cells)}</tr>")
        body_rows.append(f"<tr>{''.join(second_cells)}</tr>")
        body_rows.append(f"<tr>{''.join(third_cells)}</tr>")

    consensus_cells = ['<td colspan="2" class="blank"></td>']
    for race in races:
        top = consensus.get(race.race_number, [])
        consensus_cells.append(f'<td colspan="2" class="consensus">{"-".join(str(n) for n in top[:3])}</td>')

    logo = _logo_data_uri(settings)
    logo_html = f'<img class="logo" src="{logo}" alt="">' if logo else ""

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: Calibri, Arial, sans-serif; margin: 24px; color: #111; background: #fff; }}
    .logo {{ display: block; margin: 0 auto 14px; max-height: 110px; }}
    table {{ border-collapse: collapse; table-layout: fixed; width: {table_width}px; margin: 0 auto; }}
    td, th {{ border: 1px solid #b7bcc4; padding: 4px 6px; text-align: center; vertical-align: middle; font-size: 14px; overflow: hidden; }}
    .title {{ background: {dark}; color: #fff; font-weight: 700; font-size: 22px; letter-spacing: 1px; padding: 16px 8px; border: 1px solid {dark}; }}
    .subtitle {{ text-align: left; font-size: 12px; color: #555; border-left: none; border-right: none; background: #fff; }}
    .head {{ background: {dark}; color: #fff; font-weight: 700; padding: 8px 6px; border: 1px solid {dark}; }}
    .name {{ font-weight: 700; }}
    .horse {{ font-size: 13px; }}
    .blank {{ border: none; background: #fff; }}
    .consensus {{ background: {dark}; color: #fff; font-weight: 700; border: 1px solid {dark}; }}
    @media print {{ body {{ zoom: {print_zoom:.3f}; margin: 8px; }} }}
  </style>
</head>
<body>
  {logo_html}
  <table>
    <colgroup>{''.join(colgroup)}</colgroup>
    <tbody>
      <tr><td class="title" colspan="{total_columns}">{TITLE}</td></tr>
      <tr><td class="subtitle" colspan="{total_columns}">{escape(journey.venue)} · {journey.date}</td></tr>
      <tr>{''.join(header_cells)}</tr>
      {''.join(body_rows)}
      <tr>{''.join(consensus_cells)}</tr>
    </tbody>
  </table>
</body>
</html>"""


def _logo_data_uri(settings: Settings) -> str | None:
    template_path = settings.templates_excel_dir / settings.cuadro_template_filename
    try:
        with zipfile.ZipFile(template_path) as archive:
            data = archive.read(TEMPLATE_IMAGE_ENTRY)
        return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
    except Exception:
        logger.warning("No se pudo incrustar el logo en el cuadro visual (%s).", template_path)
        return None


def write_board_html(journey: Journey, settings: Settings, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_board_html(journey, settings), encoding="utf-8")
    return output_path


async def export_board_png_pdf(html_path: Path, png_path: Path, pdf_path: Path) -> tuple[Path, Path]:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1500, "height": 900}, device_scale_factor=2)
        await page.goto(html_path.resolve().as_uri())
        await page.screenshot(path=str(png_path), full_page=True)
        await page.pdf(path=str(pdf_path), format="A4", landscape=True, print_background=True)
        await browser.close()
    return png_path, pdf_path
