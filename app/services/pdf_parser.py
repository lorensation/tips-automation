import re
from pathlib import Path

from app.schemas.partant import ParsedParticipant, ParsedPartant, ParsedRace


def parse_participants_pdf(path: Path) -> ParsedPartant:
    text = _extract_text(path)
    races = _parse_text_partant(text)
    return ParsedPartant(races=races)


def _extract_text(path: Path) -> str:
    try:
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        import fitz

        with fitz.open(path) as doc:
            return "\n".join(page.get_text() for page in doc)


def _parse_text_partant(text: str) -> list[ParsedRace]:
    races: list[ParsedRace] = []
    current: ParsedRace | None = None
    race_re = re.compile(r"(?P<num>\d+)\s*(?:ª|a|\.|-)?\s*CARRERA(?P<name>.*)", re.IGNORECASE)
    participant_re = re.compile(r"^\s*(?P<num>\d{1,2})\s+[-.)]?\s*(?P<name>[A-ZÁÉÍÓÚÜÑ0-9' .-]{2,})")
    distance_re = re.compile(r"(?P<distance>\d{3,4})\s*(?:m|metros)", re.IGNORECASE)
    time_re = re.compile(r"(?P<time>\d{1,2}:\d{2})")

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        race_match = race_re.search(line)
        if race_match:
            if current:
                races.append(current)
            current = ParsedRace(
                race_number=int(race_match.group("num")),
                name=(race_match.group("name") or "").strip(" -") or None,
                participants=[],
            )
            time_match = time_re.search(line)
            distance_match = distance_re.search(line)
            current.scheduled_time = time_match.group("time") if time_match else None
            current.distance_meters = int(distance_match.group("distance")) if distance_match else None
            continue
        if current:
            distance_match = distance_re.search(line)
            time_match = time_re.search(line)
            if distance_match and current.distance_meters is None:
                current.distance_meters = int(distance_match.group("distance"))
            if time_match and current.scheduled_time is None:
                current.scheduled_time = time_match.group("time")
            participant_match = participant_re.match(line)
            if participant_match:
                name = " ".join(participant_match.group("name").split())
                current.participants.append(
                    ParsedParticipant(number=int(participant_match.group("num")), horse_name=name, raw_name=name)
                )
    if current:
        races.append(current)
    return races
