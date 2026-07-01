from app.services.llm.base import LLMProvider
from app.services.prediction_text_parser import parse_prediction_lines


class MockProvider(LLMProvider):
    provider_name = "mock"
    model_name = "mock-model"

    def structured_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        temperature: float = 0.0,
        timeout_seconds: int = 45,
    ) -> dict:
        specialist = _extract_after(user_prompt, "Especialista:") or "MOCK"
        total_races = int(_extract_after(user_prompt, "Total carreras:") or "1")
        raw_text = user_prompt.split("Texto bruto:", 1)[1] if "Texto bruto:" in user_prompt else user_prompt
        parsed_picks = parse_prediction_lines(raw_text, total_races)
        races: list[dict] = []
        for race_number in range(1, total_races + 1):
            picks = parsed_picks.get(race_number)
            races.append(
                {
                    "race_number": race_number,
                    "pick_1": picks[0] if picks else 1,
                    "pick_2": picks[1] if picks else 2,
                    "pick_3": picks[2] if picks else 3,
                    "confidence": 0.99 if picks else 0.35,
                    "notes": None if picks else "MockProvider could not parse this race.",
                }
            )
        return {
            "specialist": specialist,
            "races": races,
            "requires_human_review": any(race["confidence"] < 0.8 for race in races),
            "global_confidence": min(race["confidence"] for race in races),
        }

def _extract_after(text: str, label: str) -> str | None:
    for line in text.splitlines():
        if line.lower().startswith(label.lower()):
            return line.split(":", 1)[1].strip()
    return None
