import json
import logging

from pydantic import ValidationError

from app.schemas.llm import NORMALIZED_PREDICTION_SCHEMA, NormalizedPrediction
from app.services.llm.base import LLMProvider
from app.services.prediction_text_parser import parse_prediction_lines

logger = logging.getLogger(__name__)

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

REPAIR_SYSTEM_PROMPT = """Eres un reparador de JSON.
Tu única tarea es devolver EXCLUSIVAMENTE un JSON válido conforme al schema indicado.
No añadas texto fuera del JSON. No inventes carreras, caballos ni números:
usa solo la información presente en el payload rechazado."""

_PARSE_ERRORS = (ValidationError, AttributeError, TypeError, ValueError)


def normalize_prediction(
    provider: LLMProvider,
    specialist_name: str,
    raw_text: str,
    total_races: int,
    valid_participants_by_race: dict[int, list[int]],
    max_repair_attempts: int = 1,
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
        logger.warning("LLM provider %s failed for %s; using deterministic fallback.", provider.provider_name, specialist_name, exc_info=True)
        fallback = _normalize_from_text_parser(specialist_name, raw_text, total_races, "Provider error; deterministic fallback used.")
        if fallback.races:
            return fallback
        raise

    try:
        return NormalizedPrediction.model_validate(data)
    except _PARSE_ERRORS as first_error:
        logger.info("LLM payload for %s did not validate (%s); coercing.", specialist_name, type(first_error).__name__)

    # Reparación local: coerción de claves/formatos alternativos.
    try:
        repaired = _coerce_llm_payload(data, specialist_name)
        if repaired.get("races"):
            return _mark_repaired(NormalizedPrediction.model_validate(repaired), "Payload LLM reparado localmente.")
    except _PARSE_ERRORS:
        pass

    # Reintento con prompt de reparación (una vez por defecto).
    for attempt in range(max_repair_attempts):
        logger.info("Repair attempt %d with %s for %s", attempt + 1, provider.provider_name, specialist_name)
        repair_prompt = "\n".join(
            [
                f"Schema: {json.dumps(NORMALIZED_PREDICTION_SCHEMA, ensure_ascii=False)}",
                f"Especialista: {specialist_name}",
                f"Total carreras: {total_races}",
                "Payload rechazado:",
                json.dumps(data, ensure_ascii=False, default=str),
            ]
        )
        try:
            data = provider.structured_completion(REPAIR_SYSTEM_PROMPT, repair_prompt, NORMALIZED_PREDICTION_SCHEMA, temperature=0.0)
        except Exception:
            logger.warning("Repair call failed for %s.", specialist_name, exc_info=True)
            break
        try:
            return _mark_repaired(NormalizedPrediction.model_validate(data), "Payload LLM reparado con reintento.")
        except _PARSE_ERRORS:
            try:
                repaired = _coerce_llm_payload(data, specialist_name)
                if repaired.get("races"):
                    return _mark_repaired(NormalizedPrediction.model_validate(repaired), "Payload LLM reparado con reintento.")
            except _PARSE_ERRORS:
                continue

    fallback = _normalize_from_text_parser(specialist_name, raw_text, total_races, "Invalid LLM JSON shape; deterministic fallback used.")
    if fallback.races:
        return fallback
    raise ValueError(f"No se pudo normalizar el pronóstico de {specialist_name}: el LLM no devolvió JSON utilizable y el parser determinista no encontró picks.")


def _mark_repaired(prediction: NormalizedPrediction, note: str) -> NormalizedPrediction:
    """Todo resultado que pasó por reparación requiere revisión humana."""
    races = [race.model_copy(update={"notes": note if not race.notes else f"{race.notes} | {note}"}) for race in prediction.races]
    return prediction.model_copy(update={"requires_human_review": True, "races": races})


def _normalize_from_text_parser(specialist_name: str, raw_text: str, total_races: int, note: str) -> NormalizedPrediction:
    parsed = parse_prediction_lines(raw_text, total_races)
    # Cualquier fallback requiere revisión humana: el LLM no pudo confirmar la lectura.
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
        requires_human_review=True,
        global_confidence=0.98 if len(parsed) == total_races else 0.65,
    )


def _coerce_llm_payload(data, specialist_name: str) -> dict:
    data = _unwrap_llm_payload(data)
    if not isinstance(data, dict):
        return {
            "specialist": specialist_name,
            "races": [],
            "requires_human_review": True,
            "global_confidence": 0.0,
        }
    races_raw = data.get("races") or data.get("carreras") or data.get("predictions") or data.get("pronosticos") or []
    if isinstance(races_raw, dict):
        races_raw = races_raw.values()
    races = []
    for item in races_raw:
        if not isinstance(item, dict):
            continue
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


def _unwrap_llm_payload(data):
    if isinstance(data, str):
        data = data.strip()
        if not data:
            return {}
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {}
    if isinstance(data, list):
        return {"races": data}
    if isinstance(data, dict):
        for key in ("prediction", "pronostico", "result", "resultado", "data", "output"):
            nested = data.get(key)
            if isinstance(nested, (dict, list, str)):
                return _unwrap_llm_payload(nested)
    return data
