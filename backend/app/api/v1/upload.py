"""File upload endpoints.

Supports images and documents for medical case attachments.
Files are stored locally and served via URL.
"""

import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import CurrentUser
from app.core.config import get_settings

settings = get_settings()
router = APIRouter()

# Allowed MIME types
ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}
ALLOWED_DOCUMENT_TYPES = {
    "application/pdf",
    "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_DOCUMENT_TYPES

# Size limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Upload directory (configurable via env, default /app/uploads)
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/app/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Public URL prefix for serving uploaded files
UPLOAD_URL_PREFIX = os.environ.get("UPLOAD_URL_PREFIX", "/uploads")


def _generate_filename(original_name: str, user_id: str) -> str:
    """Generate a unique filename based on timestamp, user, and original name hash."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    name_hash = hashlib.sha256(original_name.encode()).hexdigest()[:8]
    ext = Path(original_name).suffix.lower()
    safe_ext = ext if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".txt", ".doc", ".docx"} else ".bin"
    return f"{timestamp}_{user_id[:8]}_{name_hash}{safe_ext}"


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
    current_user: CurrentUser,
    file: UploadFile = File(..., description="File to upload (image or document)"),
) -> dict:
    """Upload a file (image or document).

    **Allowed types:**
    - Images: jpeg, png, gif, webp
    - Documents: pdf, txt, doc, docx

    **Max size:** 10 MB
    """
    # Check file type
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{content_type}' not allowed. Allowed: {', '.join(ALLOWED_TYPES)}",
        )

    # Read and check size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // 1024 // 1024} MB",
        )

    # Generate unique filename
    user_id = str(current_user.id)
    filename = _generate_filename(file.filename or "unknown", user_id)
    file_path = UPLOAD_DIR / filename

    # Save file
    with open(file_path, "wb") as f:
        f.write(contents)

    # Build public URL
    public_url = f"{UPLOAD_URL_PREFIX}/{filename}"

    return {
        "filename": filename,
        "original_name": file.filename,
        "url": public_url,
        "content_type": content_type,
        "size": len(contents),
    }


@router.get("/uploads/{filename}")
async def serve_uploaded_file(filename: str) -> dict:
    """Serve an uploaded file by filename.

    In production this should be served directly by Nginx,
    not through the application server.
    """
    file_path = UPLOAD_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Return file info; in production Nginx should serve the file directly
    return {
        "filename": filename,
        "path": str(file_path),
        "size": file_path.stat().st_size,
    }
