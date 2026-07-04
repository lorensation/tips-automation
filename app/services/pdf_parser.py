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
    race_re = re.compile(r"^\s*(?P<num>\d+)\s*(?:ª|º|a|o|\.|-)?\s*CARRERA\b(?P<name>.*)$", re.IGNORECASE)
    participant_re = re.compile(r"^\s*(?P<num>\d{1,2})\s+[-.)]?\s*(?P<name>.+?)\s*$")
    distance_re = re.compile(r"(?P<distance>\d{1,2}(?:\.\d{3})|\d{3,4})\s*(?:m|metros)", re.IGNORECASE)
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
            current.distance_meters = _parse_distance(distance_match.group("distance")) if distance_match else None
            continue
        if current:
            distance_match = distance_re.search(line)
            time_match = time_re.search(line)
            if distance_match and current.distance_meters is None:
                current.distance_meters = _parse_distance(distance_match.group("distance"))
            if time_match and current.scheduled_time is None:
                current.scheduled_time = time_match.group("time")
            participant_match = participant_re.match(line)
            if participant_match:
                raw_name = participant_match.group("name")
                name = _clean_participant_name(raw_name)
                if name:
                    current.participants.append(
                        ParsedParticipant(
                            number=int(participant_match.group("num")),
                            horse_name=name,
                            raw_name=raw_name,
                        )
                    )
    if current:
        races.append(current)
    return _deduplicate_races(races)


def _clean_participant_name(raw_name: str) -> str:
    name = " ".join(raw_name.split())
    name = re.sub(r"\s+\d{1,2}\s+\d{2}(?:,\d+)?\b.*$", "", name)
    name = re.sub(r"\b\d+\s*a\S?os\b.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\([^)]*\)", " ", name)
    name = re.sub(r"\s+\d+(?:\s*[-/]\s*\d+)*\s*$", "", name)
    name = re.sub(r"\s+", " ", name).strip(" -.,;:")
    if not any(char.isalpha() for char in name):
        return ""
    if name.upper() in {"CABALLO", "EDAD", "PESO", "JOCKEY", "ENTRENADOR"}:
        return ""
    return name


def _parse_distance(raw_distance: str) -> int:
    return int(raw_distance.replace(".", ""))


def _deduplicate_races(races: list[ParsedRace]) -> list[ParsedRace]:
    by_number: dict[int, ParsedRace] = {}
    for race in races:
        existing = by_number.get(race.race_number)
        if existing is None:
            by_number[race.race_number] = race
            continue
        if _race_quality(race) > _race_quality(existing):
            by_number[race.race_number] = race
            existing, race = race, existing
        existing_numbers = {participant.number for participant in existing.participants}
        for participant in race.participants:
            if participant.number not in existing_numbers:
                existing.participants.append(participant)
                existing_numbers.add(participant.number)
    return [by_number[number] for number in sorted(by_number)]


def _race_quality(race: ParsedRace) -> tuple[int, int]:
    useful_name = 0 if not race.name or race.name.strip(" .-") == "" else 1
    return (len(race.participants), useful_name)
