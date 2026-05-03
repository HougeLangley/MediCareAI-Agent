"""Document file parser for PDF, Word (.docx), and plain text uploads.

Extracts text content from uploaded files for ingestion into the RAG pipeline.
"""

import io
from typing import BinaryIO

from fastapi import HTTPException, UploadFile, status

# Maximum file size: 20 MB
_MAX_FILE_SIZE = 20 * 1024 * 1024

# Supported MIME types and extensions
_SUPPORTED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}

_SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def _get_file_type(upload_file: UploadFile) -> str:
    """Determine file type from MIME type or filename extension."""
    mime = upload_file.content_type or ""
    if mime in _SUPPORTED_TYPES:
        return _SUPPORTED_TYPES[mime]

    filename = upload_file.filename or ""
    lower_name = filename.lower()
    for ext, ftype in {".pdf": "pdf", ".docx": "docx", ".txt": "txt"}.items():
        if lower_name.endswith(ext):
            return ftype

    return ""


def _parse_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF parser not available: pypdf not installed",
        ) from exc

    reader = PdfReader(io.BytesIO(file_bytes))
    texts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            texts.append(page_text)
    return "\n\n".join(texts)


def _parse_docx(file_bytes: bytes) -> str:
    """Extract text from Word .docx bytes."""
    try:
        from docx import Document
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Word parser not available: python-docx not installed",
        ) from exc

    doc = Document(io.BytesIO(file_bytes))
    paragraphs: list[str] = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text.strip())
    return "\n\n".join(paragraphs)


def _parse_txt(file_bytes: bytes) -> str:
    """Extract text from plain text bytes (UTF-8 with BOM fallback)."""
    # Try UTF-8 first
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        pass
    # Try UTF-8 with BOM
    try:
        return file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    # Fallback to GBK (common for Chinese medical docs)
    try:
        return file_bytes.decode("gbk")
    except UnicodeDecodeError:
        pass
    # Last resort: latin-1 (never fails, but may mangle non-ASCII)
    return file_bytes.decode("latin-1")


async def parse_uploaded_file(upload_file: UploadFile) -> tuple[str, str]:
    """Parse an uploaded file and return (extracted_text, file_type).

    Args:
        upload_file: FastAPI UploadFile from multipart form.

    Returns:
        Tuple of (extracted_text, detected_file_type).

    Raises:
        HTTPException: If file type unsupported, too large, or parsing fails.
    """
    # Validate file type
    file_type = _get_file_type(upload_file)
    if not file_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type: {upload_file.content_type or 'unknown'}. "
                f"Supported: PDF, Word (.docx), plain text (.txt)"
            ),
        )

    # Read file content
    file_bytes = await upload_file.read()
    if len(file_bytes) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large: {len(file_bytes)} bytes (max {_MAX_FILE_SIZE} bytes = 20 MB)",
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    # Parse based on file type
    try:
        if file_type == "pdf":
            text = _parse_pdf(file_bytes)
        elif file_type == "docx":
            text = _parse_docx(file_bytes)
        elif file_type == "txt":
            text = _parse_txt(file_bytes)
        else:
            # Should never reach here due to validation above
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected file type: {file_type}",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse {file_type.upper()} file: {exc}",
        ) from exc

    # Clean up extracted text
    text = text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text content could be extracted from the uploaded file",
        )

    return text, file_type
