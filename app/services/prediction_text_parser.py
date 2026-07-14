import re


def parse_prediction_lines(raw_text: str, total_races: int) -> dict[int, tuple[int, int, int]]:
    parsed: dict[int, tuple[int, int, int]] = {}
    sequential_race = 1
    pending_race: int | None = None
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line_without_whatsapp = _strip_whatsapp_prefix(line)

        picks: tuple[int, int, int] | None = None
        explicit_race: int | None = None

        picks_match = re.search(r"(?<!\d)(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{1,2})(?!\d)\s*$", line_without_whatsapp)
        if picks_match:
            explicit_race = _extract_explicit_race_number(line_without_whatsapp[: picks_match.start()])
            picks = tuple(int(picks_match.group(index)) for index in range(1, 4))
        else:
            explicit_race, content = _split_race_prefix(line_without_whatsapp)
            picks = _extract_interleaved_picks(content)

        if picks is not None:
            race_number = explicit_race or pending_race or sequential_race
            if 1 <= race_number <= total_races:
                parsed[race_number] = picks
            if explicit_race is None and pending_race is None:
                sequential_race += 1
            pending_race = None
            continue

        pending_race = _extract_standalone_race_number(line_without_whatsapp)
    return parsed


def _strip_whatsapp_prefix(line: str) -> str:
    match = re.match(r"^\[[^\]]+]\s*[^:]+:\s*(.+)$", line)
    return match.group(1).strip() if match else line


def _extract_explicit_race_number(prefix: str) -> int | None:
    simple_match = re.match(r"^\s*(\d{1,2})\s*[\).:-]", prefix)
    if simple_match:
        return int(simple_match.group(1))
    carrera_match = re.search(r"(?:carrera|c)\s*(\d{1,2})\b", prefix, flags=re.IGNORECASE)
    if carrera_match:
        return int(carrera_match.group(1))
    return None


def _extract_standalone_race_number(line: str) -> int | None:
    match = re.match(r"^\s*(\d{1,2})\s*(?:carrera|ª|a)?\s*$", line, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _split_race_prefix(line: str) -> tuple[int | None, str]:
    """Separa una etiqueta de carrera inicial ("1 carrera:", "carrera 1", "1)") del resto.

    Devuelve (número_de_carrera, resto). Solo devuelve número cuando la etiqueta es
    inequívoca (palabra "carrera" o separador), para no confundir el primer pick con
    el número de carrera en formatos con dorsal intercalado.
    """
    match = re.match(r"^\s*(\d{1,2})\s*(?:ª|º|a)?\s*carrera\b\.?\s*[)\].:\-]?\s*", line, flags=re.IGNORECASE)
    if match:
        return int(match.group(1)), line[match.end():]
    match = re.match(r"^\s*carrera\s*(\d{1,2})\b\s*[)\].:\-]?\s*", line, flags=re.IGNORECASE)
    if match:
        return int(match.group(1)), line[match.end():]
    match = re.match(r"^\s*(\d{1,2})\s*[)\].:\-]\s+", line)
    if match:
        return int(match.group(1)), line[match.end():]
    return None, line


def _extract_interleaved_picks(content: str) -> tuple[int, int, int] | None:
    """Extrae picks del formato "1 Mauro 2 flaming glass 3 machu pichu".

    Cada pick es un dorsal (número) seguido del nombre del caballo; se toman los tres
    primeros números que preceden a un nombre.
    """
    numbers = re.findall(r"(?<!\d)(\d{1,2})\s+[^\W\d_]", content)
    if len(numbers) >= 3:
        return (int(numbers[0]), int(numbers[1]), int(numbers[2]))
    return None
