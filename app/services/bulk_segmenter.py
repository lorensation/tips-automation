"""Segmenta un bloque de texto con los pronósticos de varios especialistas.

Segmentación 100% determinista: una línea es cabecera de bloque si, tras
normalizar acentos/mayúsculas/puntuación, coincide con un alias conocido de un
especialista y no contiene un triplete de picks. Todo lo que sigue pertenece a
ese especialista hasta la siguiente cabecera.
"""

import re
import unicodedata
from dataclasses import dataclass, field

from app.enums import SPECIALIST_NAMES

_PICKS_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{1,2})(?!\d)")
_WHATSAPP_RE = re.compile(r"^\[[^\]]+]\s*(?P<author>[^:]+):\s*(?P<rest>.*)$")
_MAX_HEADER_LENGTH = 48

# Alias por especialista (se comparan normalizados, los más largos primero).
SPECIALIST_ALIASES: dict[str, list[str]] = {
    "EMILIO VILLAVERDE": ["EMILIO VILLAVERDE", "VILLAVERDE", "EMILIO"],
    "ESTEBAN ROMERA": ["ESTEBAN ROMERA", "ROMERA", "ESTEBAN"],
    "ANDER GALDONA": ["ANDER GALDONA", "GALDONA", "ANDER"],
    "PEDRO MERCADO": ["PEDRO MERCADO", "MERCADO"],
    "JAVIER FERNANDEZ-CUESTA": [
        "JAVIER FERNANDEZ CUESTA",
        "FERNANDEZ CUESTA",
        "FDEZ CUESTA",
        "JAVIER CUESTA",
        "CUESTA",
    ],
    "JOSÉ SOTO": ["JOSE SOTO", "SOTO"],
    "JOSE MANUEL FERNÁNDEZ": [
        "JOSE MANUEL FERNANDEZ",
        "JOSEMA FERNANDEZ",
        "JM FERNANDEZ",
        "J M FERNANDEZ",
        "JOSE MANUEL",
    ],
    "HIPOTOUR": ["HIPOTOUR", "HIPO TOUR"],
}


@dataclass
class SegmentedBlock:
    specialist_name: str  # nombre canónico de SPECIALIST_NAMES
    header_line: str
    start_line: int
    lines: list[str] = field(default_factory=list)

    @property
    def raw_block(self) -> str:
        return "\n".join(self.lines).strip()


@dataclass
class BulkSegmentation:
    blocks: list[SegmentedBlock] = field(default_factory=list)
    missing_specialists: list[str] = field(default_factory=list)
    duplicated_specialists: list[str] = field(default_factory=list)
    unassigned_preamble: str = ""


def normalize_name(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    upper = without_accents.upper()
    cleaned = re.sub(r"[^A-Z0-9 ]+", " ", upper)
    return re.sub(r"\s+", " ", cleaned).strip()


def _alias_index() -> list[tuple[str, str]]:
    """[(alias normalizado, nombre canónico)] con los alias más largos primero."""
    pairs: list[tuple[str, str]] = []
    for canonical, aliases in SPECIALIST_ALIASES.items():
        for alias in aliases:
            pairs.append((normalize_name(alias), canonical))
    pairs.sort(key=lambda pair: len(pair[0]), reverse=True)
    return pairs


_ALIAS_INDEX = _alias_index()


def _match_specialist_header(line: str) -> str | None:
    candidate = line.strip()
    whatsapp = _WHATSAPP_RE.match(candidate)
    if whatsapp:
        rest = whatsapp.group("rest").strip()
        # "[11:02] Ander Galdona: ..." — el autor identifica el bloque si el resto no es un pick.
        if not rest or not _PICKS_RE.search(rest):
            author = normalize_name(whatsapp.group("author"))
            for alias, canonical in _ALIAS_INDEX:
                if author == alias or author.startswith(alias + " ") or author.endswith(" " + alias):
                    return canonical
        candidate = rest if rest else candidate
    if len(candidate) > _MAX_HEADER_LENGTH or _PICKS_RE.search(candidate):
        return None
    normalized = normalize_name(candidate)
    if not normalized:
        return None
    for alias, canonical in _ALIAS_INDEX:
        if normalized == alias or normalized.startswith(alias + " ") or normalized.endswith(" " + alias):
            return canonical
    return None


def segment_bulk_text(raw_text: str) -> BulkSegmentation:
    segmentation = BulkSegmentation()
    blocks_by_specialist: dict[str, SegmentedBlock] = {}
    current: SegmentedBlock | None = None
    preamble: list[str] = []

    for line_number, raw_line in enumerate(raw_text.splitlines(), start=1):
        line = raw_line.rstrip()
        matched = _match_specialist_header(line) if line.strip() else None
        if matched:
            existing = blocks_by_specialist.get(matched)
            if existing is not None:
                if matched not in segmentation.duplicated_specialists:
                    segmentation.duplicated_specialists.append(matched)
                current = existing
                continue
            current = SegmentedBlock(specialist_name=matched, header_line=line.strip(), start_line=line_number)
            blocks_by_specialist[matched] = current
            segmentation.blocks.append(current)
            continue
        if current is None:
            if line.strip():
                preamble.append(line)
        else:
            current.lines.append(line)

    segmentation.unassigned_preamble = "\n".join(preamble).strip()
    found = set(blocks_by_specialist)
    segmentation.missing_specialists = [name for name in SPECIALIST_NAMES if name not in found]
    return segmentation
