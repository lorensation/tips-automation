from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_secret_key: str = "change_me"
    app_base_url: str = "http://localhost:8080"
    database_url: str = "sqlite:///./dev.db"

    admin_email: str = "admin@example.com"
    admin_password_hash: str = ""

    llm_provider: str = "mock"
    llm_model: str = "mock-model"
    llm_base_url: str = ""
    llm_api_key: str = ""
    secondary_llm_provider: str = ""
    secondary_llm_model: str = ""
    secondary_llm_base_url: str = ""
    secondary_llm_api_key: str = ""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "administracion@hipodromos.org"
    email_recipients: str = ""

    google_drive_folder_id: str = ""
    google_service_account_json_base64: str = ""
    output_storage_mode: str = "local"

    consensus_pick_1_points: int = Field(default=3, ge=0)
    consensus_pick_2_points: int = Field(default=2, ge=0)
    consensus_pick_3_points: int = Field(default=1, ge=0)

    upload_dir: Path = Path("uploads")
    generated_dir: Path = Path("generated")
    templates_excel_dir: Path = Path("templates_excel")
    max_pdf_bytes: int = 15 * 1024 * 1024

    tips_template_filename: str = "Tips _Ejemplo.xlsx"
    cuadro_template_filename: str = "Cuadro_Pronosticos_Ejemplo.xlsx"
    pronos_file_path: Path = Path("data/PRONOS 2026.xlsx")
    pronos_backup_dir: Path = Path("data/backups")
    cuadro_sheet_name_pattern: str = "PRO_{dd}_{mm}"

    login_max_attempts: int = Field(default=5, ge=1)
    login_window_seconds: int = Field(default=300, ge=1)

    @property
    def email_recipient_list(self) -> list[str]:
        return [item.strip() for item in self.email_recipients.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
