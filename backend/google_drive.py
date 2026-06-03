from __future__ import annotations

import json
import logging
import os
from typing import Any

from google.auth.exceptions import GoogleAuthError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

logger = logging.getLogger("siee.google_drive")

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
FOLDER_ID_KEY = "GOOGLE_DRIVE_FOLDER_ID"
CREDENTIALS_KEY = "GOOGLE_DRIVE_CREDENTIALS_JSON"


def _get_credentials() -> service_account.Credentials | None:
    creds_json = os.getenv(CREDENTIALS_KEY)
    # Fallback: load from file path if env var points to a file
    if creds_json and creds_json.startswith("{"):
        try:
            creds_dict = json.loads(creds_json)
            return service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        except (json.JSONDecodeError, ValueError, GoogleAuthError) as e:
            logger.error("Failed to load Google Drive credentials: %s", e)
            return None
    file_path = os.getenv("GOOGLE_DRIVE_CREDENTIALS_FILE")
    if file_path and os.path.exists(file_path):
        try:
            return service_account.Credentials.from_service_account_file(file_path, scopes=SCOPES)
        except (ValueError, GoogleAuthError) as e:
            logger.error("Failed to load credentials from file %s: %s", file_path, e)
            return None
    if creds_json:
        try:
            creds_dict = json.loads(creds_json)
            return service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        except (json.JSONDecodeError, ValueError, GoogleAuthError) as e:
            logger.error("Failed to parse GOOGLE_DRIVE_CREDENTIALS_JSON: %s", e)
            return None
    logger.warning("GOOGLE_DRIVE_CREDENTIALS not configured — Google Drive upload disabled")
    return None


def upload_to_drive(
    file_bytes: bytes,
    filename: str,
    mime_type: str = "application/octet-stream",
) -> dict[str, Any]:
    creds = _get_credentials()
    if not creds:
        return {"error": "Google Drive not configured", "url": ""}

    folder_id = os.getenv(FOLDER_ID_KEY)
    if not folder_id:
        logger.warning("GOOGLE_DRIVE_FOLDER_ID not set — uploading to Drive root")

    try:
        service = build("drive", "v3", credentials=creds)

        file_metadata: dict[str, str] = {"name": filename}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        media = MediaIoBaseUpload(
            fd=__import__("io").BytesIO(file_bytes),
            mimetype=mime_type,
            resumable=True,
        )

        uploaded = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id,webViewLink,name")
            .execute()
        )

        file_id = uploaded.get("id", "")
        web_link = uploaded.get("webViewLink", "")

        if file_id and not web_link:
            web_link = f"https://drive.google.com/file/d/{file_id}/view"

        # Set permission: anyone with link can view
        try:
            service.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"},
            ).execute()
        except Exception as e:
            logger.debug("Drive permission set error (non-critical): %s", e)

        logger.info("Uploaded to Drive: %s id=%s", filename, file_id)
        return {"file_id": file_id, "url": web_link, "name": filename}

    except Exception as e:
        logger.error("Google Drive upload failed: %s", e)
        return {"error": str(e)[:200], "url": ""}
