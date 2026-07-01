import re

from app.services.llm.base import LLMProvider


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
        races: list[dict] = []
        for race_number in range(1, total_races + 1):
            pattern = rf"(?:carrera\s*)?{race_number}(?:\s*carrera)?\D+(\d+)\D+(\d+)\D+(\d+)"
            match = re.search(pattern, raw_text, flags=re.IGNORECASE)
            picks = [int(match.group(i)) for i in range(1, 4)] if match else [1, 2, 3]
            races.append(
                {
                    "race_number": race_number,
                    "pick_1": picks[0],
                    "pick_2": picks[1],
                    "pick_3": picks[2],
                    "confidence": 0.95 if match else 0.65,
                    "notes": None if match else "MockProvider used default picks.",
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
