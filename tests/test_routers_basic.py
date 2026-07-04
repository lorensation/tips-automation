import re
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_password
from app.database import SessionLocal
from app.enums import JourneyStatus, UserRole
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.journey import Journey
from app.models.participant import Participant
from app.models.prediction import Prediction
from app.models.race import Race
from app.models.specialist import Specialist
from app.models.user import User
from app.security import login_rate_limiter
from app.utils import utcnow

ADMIN_EMAIL = "router-admin@example.com"
ADMIN_PASSWORD = "router-secret"


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        _ensure_admin()
        login_rate_limiter._failures.clear()
        yield test_client
        login_rate_limiter._failures.clear()


def _ensure_admin() -> None:
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        if user is None:
            db.add(User(email=ADMIN_EMAIL, password_hash=hash_password(ADMIN_PASSWORD), role=UserRole.ADMIN))
            db.commit()


def _csrf_token(client: TestClient, path: str = "/login") -> str:
    response = client.get(path)
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match, f"No CSRF token found in {path}"
    return match.group(1)


def _login(client: TestClient) -> None:
    token = _csrf_token(client)
    response = client.post(
        "/login",
        data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_login_without_csrf_is_rejected(client: TestClient) -> None:
    client.get("/login")  # crea sesión
    response = client.post("/login", data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, follow_redirects=False)
    assert response.status_code == 403


def test_login_with_csrf_succeeds(client: TestClient) -> None:
    _login(client)
    response = client.get("/journeys")
    assert response.status_code == 200


def test_login_rate_limit_blocks_after_max_attempts(client: TestClient) -> None:
    token = _csrf_token(client)
    for _ in range(5):
        response = client.post(
            "/login",
            data={"email": ADMIN_EMAIL, "password": "wrong", "csrf_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 400
    response = client.post(
        "/login",
        data={"email": ADMIN_EMAIL, "password": "wrong", "csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 429


def test_upload_rejects_bytes_without_pdf_magic(client: TestClient) -> None:
    _login(client)
    token = _csrf_token(client, "/journeys/new")
    response = client.post(
        "/journeys",
        data={"journey_date": "2026-07-02", "venue": "HZ_NOCTURNAS", "csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    journey_url = response.headers["Location"]

    token = _csrf_token(client, journey_url)
    response = client.post(
        f"{journey_url}/pdf",
        data={"csrf_token": token},
        files={"pdf": ("falso.pdf", b"esto no es un pdf", "application/pdf")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "error=pdf_type" in response.headers["Location"]


def _create_confirmed_journey() -> str:
    with SessionLocal() as db:
        journey = Journey(
            date=date(2026, 7, 2),
            venue="HZ_NOCTURNAS",
            theme="black",
            season_year=2026,
            status=JourneyStatus.PARTANT_CONFIRMED,
            partant_confirmed_at=utcnow(),
        )
        for race_number in (1, 2):
            race = Race(race_number=race_number)
            race.participants = [Participant(number=i, horse_name=f"CAB{race_number}{i}") for i in range(1, 9)]
            journey.races.append(race)
        db.add(journey)
        db.commit()
        return journey.id


def test_bulk_preview_and_confirm_persist_predictions(client: TestClient) -> None:
    _login(client)
    journey_id = _create_confirmed_journey()
    raw_text = "ANDER GALDONA\n1) 2-1-3\n2) 4-5-1\n"

    token = _csrf_token(client, f"/journeys/{journey_id}/predictions/bulk")
    response = client.post(
        f"/journeys/{journey_id}/predictions/bulk/preview",
        data={"raw_text": raw_text, "csrf_token": token},
    )
    assert response.status_code == 200
    assert "ANDER GALDONA" in response.text
    assert "EMILIO VILLAVERDE" in response.text  # aviso de especialista faltante

    with SessionLocal() as db:
        specialist = db.query(Specialist).filter(Specialist.name == "ANDER GALDONA").one()
        specialist_id = specialist.id

    form = {
        "csrf_token": token,
        "bulk_raw_text": raw_text,
        f"include_{specialist_id}": "1",
        f"raw_block_{specialist_id}": "1) 2-1-3\n2) 4-5-1",
        f"requires_review_{specialist_id}": "0",
        f"pick_{specialist_id}_1_1": "2",
        f"pick_{specialist_id}_1_2": "1",
        f"pick_{specialist_id}_1_3": "3",
        f"pick_{specialist_id}_2_1": "4",
        f"pick_{specialist_id}_2_2": "5",
        f"pick_{specialist_id}_2_3": "1",
    }
    response = client.post(
        f"/journeys/{journey_id}/predictions/bulk/confirm", data=form, follow_redirects=False
    )
    assert response.status_code == 303

    with SessionLocal() as db:
        prediction = (
            db.query(Prediction)
            .filter(Prediction.journey_id == journey_id, Prediction.specialist_id == specialist_id)
            .one()
        )
        assert prediction.status == "valid"
        assert prediction.raw_text == "1) 2-1-3\n2) 4-5-1"
        assert len(prediction.picks) == 2
        event = (
            db.query(AuditEvent)
            .filter(AuditEvent.journey_id == journey_id, AuditEvent.event_type == "bulk_predictions_saved")
            .one()
        )
        assert event.payload["raw_text"] == raw_text
        assert event.payload["specialists"] == ["ANDER GALDONA"]


def test_bulk_confirm_rejects_invalid_pick_deterministically(client: TestClient) -> None:
    _login(client)
    journey_id = _create_confirmed_journey()
    token = _csrf_token(client, f"/journeys/{journey_id}/predictions/bulk")
    with SessionLocal() as db:
        specialist_id = db.query(Specialist).filter(Specialist.name == "JOSÉ SOTO").one().id

    form = {
        "csrf_token": token,
        "bulk_raw_text": "JOSÉ SOTO\n1) 2-2-5\n2) 99-1-2",
        f"include_{specialist_id}": "1",
        f"raw_block_{specialist_id}": "1) 2-2-5\n2) 99-1-2",
        f"requires_review_{specialist_id}": "0",
        f"pick_{specialist_id}_1_1": "2",
        f"pick_{specialist_id}_1_2": "2",
        f"pick_{specialist_id}_1_3": "5",
        f"pick_{specialist_id}_2_1": "99",
        f"pick_{specialist_id}_2_2": "1",
        f"pick_{specialist_id}_2_3": "2",
    }
    response = client.post(
        f"/journeys/{journey_id}/predictions/bulk/confirm", data=form, follow_redirects=False
    )
    assert response.status_code == 303

    with SessionLocal() as db:
        prediction = (
            db.query(Prediction)
            .filter(Prediction.journey_id == journey_id, Prediction.specialist_id == specialist_id)
            .one()
        )
        assert prediction.status == "validation_failed"
        messages = [error["message"] for error in prediction.validation_errors]
        assert any("duplicados" in message for message in messages)
        assert any("no existe" in message for message in messages)


def test_download_output_serves_file(client: TestClient, tmp_path) -> None:
    _login(client)
    journey_id = _create_confirmed_journey()
    file_path = tmp_path / "tips_test.xlsx"
    file_path.write_bytes(b"contenido de prueba")
    from app.enums import OutputStatus, OutputType
    from app.models.generated_output import GeneratedOutput

    with SessionLocal() as db:
        output = GeneratedOutput(
            journey_id=journey_id,
            type=OutputType.TIPS_EXCEL,
            version=1,
            status=OutputStatus.GENERATED,
            local_path=str(file_path),
        )
        db.add(output)
        db.commit()
        output_id = output.id

    response = client.get(f"/journeys/{journey_id}/outputs/{output_id}/download")
    assert response.status_code == 200
    assert response.content == b"contenido de prueba"
