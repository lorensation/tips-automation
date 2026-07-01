from app.config import Settings


def test_email_recipient_list_strips_empty_values() -> None:
    settings = Settings(email_recipients="a@example.com, b@example.com,")
    assert settings.email_recipient_list == ["a@example.com", "b@example.com"]
