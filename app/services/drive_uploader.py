from dataclasses import dataclass
import base64
import json
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app.config import Settings


@dataclass(frozen=True)
class DriveUploadResult:
    file_id: str
    url: str


def upload_file_to_drive(path: Path, settings: Settings, folder_name: str) -> DriveUploadResult:
    if not settings.google_drive_folder_id or not settings.google_service_account_json_base64:
        raise RuntimeError("Google Drive is not configured")
    credentials_info = json.loads(base64.b64decode(settings.google_service_account_json_base64).decode("utf-8"))
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    folder_id = _ensure_folder(service, settings.google_drive_folder_id, folder_name)
    existing = _find_file(service, folder_id, path.name)
    media = MediaFileUpload(str(path), resumable=False)
    metadata = {"name": path.name, "parents": [folder_id]}
    if existing:
        file = service.files().update(fileId=existing["id"], media_body=media, fields="id, webViewLink").execute()
    else:
        file = service.files().create(body=metadata, media_body=media, fields="id, webViewLink").execute()
    return DriveUploadResult(file_id=file["id"], url=file.get("webViewLink", ""))


def _ensure_folder(service, parent_id: str, name: str) -> str:
    query = (
        f"'{parent_id}' in parents and "
        f"name = '{_escape_query(name)}' and "
        "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )
    response = service.files().list(q=query, fields="files(id, name)", pageSize=1).execute()
    files = response.get("files", [])
    if files:
        return files[0]["id"]
    metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def _find_file(service, parent_id: str, name: str) -> dict | None:
    query = f"'{parent_id}' in parents and name = '{_escape_query(name)}' and trashed = false"
    response = service.files().list(q=query, fields="files(id, name, webViewLink)", pageSize=1).execute()
    files = response.get("files", [])
    return files[0] if files else None


def _escape_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")
