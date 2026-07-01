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
        picks_match = re.search(r"(?<!\d)(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{1,2})(?!\d)\s*$", line_without_whatsapp)
        if picks_match:
            prefix = line_without_whatsapp[: picks_match.start()]
            explicit_race = _extract_explicit_race_number(prefix)
            race_number = explicit_race or pending_race or sequential_race
            if 1 <= race_number <= total_races:
                parsed[race_number] = tuple(int(picks_match.group(index)) for index in range(1, 4))
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
