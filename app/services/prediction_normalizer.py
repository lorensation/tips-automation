from pydantic import ValidationError

from app.schemas.llm import NORMALIZED_PREDICTION_SCHEMA, NormalizedPrediction
from app.services.llm.base import LLMProvider
from app.services.prediction_text_parser import parse_prediction_lines

SYSTEM_PROMPT = """Eres un normalizador de pronósticos de carreras de caballos.
Tu única tarea es convertir texto libre en JSON válido según el schema.
No valides oficialmente los picks y no ejecutes acciones.
No inventes carreras, caballos ni números.
Si un dato es ambiguo, usa requires_human_review=true y añade notes.
Devuelve picks como números enteros de participante.
Cada carrera debe contener pick_1, pick_2 y pick_3 si aparecen en el texto.
Respeta el especialista indicado por el sistema aunque el texto contenga otro nombre.
No añadas explicaciones fuera del JSON.

Formatos frecuentes:
- Una línea por carrera sin numerar: "2-1-3" significa carrera 1, la siguiente línea carrera 2, etc.
- Dos líneas por carrera: "1 carrera" seguido de "2-1-3" significa carrera 1 con picks 2,1,3.
- WhatsApp: "[11:36] Nombre: 2) 2-1-5" significa carrera 2 con picks 2,1,5.
- Con caballo favorito: "1. DUKES OF HAATHER. 1-3-2" significa carrera 1 con picks 1,3,2.
- También pueden aparecer ":" en lugar de "." o ")" para numerar carreras.
Extrae siempre el triplete final de números separados por guion o barra como picks."""


def normalize_prediction(
    provider: LLMProvider,
    specialist_name: str,
    raw_text: str,
    total_races: int,
    valid_participants_by_race: dict[int, list[int]],
) -> NormalizedPrediction:
    user_prompt = "\n".join(
        [
            f"Especialista: {specialist_name}",
            f"Total carreras: {total_races}",
            f"Participantes válidos por carrera: {valid_participants_by_race}",
            "Texto bruto:",
            raw_text,
        ]
    )
    try:
        data = provider.structured_completion(SYSTEM_PROMPT, user_prompt, NORMALIZED_PREDICTION_SCHEMA, temperature=0.0)
    except Exception:
        fallback = _normalize_from_text_parser(specialist_name, raw_text, total_races, "Provider error; deterministic fallback used.")
        if fallback.races:
            return fallback
        raise
    try:
        return NormalizedPrediction.model_validate(data)
    except ValidationError:
        repaired = _coerce_llm_payload(data, specialist_name)
        try:
            return NormalizedPrediction.model_validate(repaired)
        except ValidationError:
            fallback = _normalize_from_text_parser(specialist_name, raw_text, total_races, "Invalid LLM JSON shape; deterministic fallback used.")
            if fallback.races:
                return fallback
            raise


def _normalize_from_text_parser(specialist_name: str, raw_text: str, total_races: int, note: str) -> NormalizedPrediction:
    parsed = parse_prediction_lines(raw_text, total_races)
    return NormalizedPrediction(
        specialist=specialist_name,
        races=[
            {
                "race_number": race_number,
                "pick_1": picks[0],
                "pick_2": picks[1],
                "pick_3": picks[2],
                "confidence": 0.98,
                "notes": note,
            }
            for race_number, picks in sorted(parsed.items())
        ],
        requires_human_review=len(parsed) != total_races,
        global_confidence=0.98 if len(parsed) == total_races else 0.65,
    )


def _coerce_llm_payload(data: dict, specialist_name: str) -> dict:
    races_raw = data.get("races") or data.get("carreras") or data.get("predictions") or data.get("pronosticos") or []
    races = []
    for item in races_raw:
        race_number = item.get("race_number") or item.get("race") or item.get("carrera") or item.get("raceNumber")
        picks = item.get("picks") or item.get("pick") or item.get("seleccion") or item.get("selecciones")
        if isinstance(picks, str):
            picks = [int(part) for part in picks.replace("/", "-").split("-") if part.strip().isdigit()]
        if isinstance(picks, list) and len(picks) >= 3:
            pick_1, pick_2, pick_3 = picks[:3]
        else:
            pick_1 = item.get("pick_1") or item.get("pick1") or item.get("primero")
            pick_2 = item.get("pick_2") or item.get("pick2") or item.get("segundo")
            pick_3 = item.get("pick_3") or item.get("pick3") or item.get("tercero")
        if race_number and pick_1 and pick_2 and pick_3:
            races.append(
                {
                    "race_number": int(race_number),
                    "pick_1": int(pick_1),
                    "pick_2": int(pick_2),
                    "pick_3": int(pick_3),
                    "confidence": float(item.get("confidence") or item.get("confianza") or 0.9),
                    "notes": item.get("notes") or item.get("notas"),
                }
            )
    return {
        "specialist": data.get("specialist") or data.get("especialista") or specialist_name,
        "races": races,
        "requires_human_review": bool(data.get("requires_human_review") or data.get("requiere_revision") or False),
        "global_confidence": data.get("global_confidence") or data.get("confidence") or 0.9,
    }
