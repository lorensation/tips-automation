from app.schemas.llm import NORMALIZED_PREDICTION_SCHEMA, NormalizedPrediction
from app.services.llm.base import LLMProvider

SYSTEM_PROMPT = """Eres un normalizador de pronósticos de carreras de caballos.
Tu única tarea es convertir texto libre en JSON válido según el schema.
No valides oficialmente los picks y no ejecutes acciones.
No inventes carreras, caballos ni números.
Si un dato es ambiguo, usa requires_human_review=true y añade notes.
Devuelve picks como números enteros de participante.
Cada carrera debe contener pick_1, pick_2 y pick_3 si aparecen en el texto.
Respeta el especialista indicado por el sistema aunque el texto contenga otro nombre.
No añadas explicaciones fuera del JSON."""


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
    data = provider.structured_completion(SYSTEM_PROMPT, user_prompt, NORMALIZED_PREDICTION_SCHEMA, temperature=0.0)
    return NormalizedPrediction.model_validate(data)
