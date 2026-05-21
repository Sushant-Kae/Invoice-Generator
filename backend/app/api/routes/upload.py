"""
File Upload Route

Handles manufacturer invoice uploads with:
- File type validation
- Size limits
- Filename sanitization
- Secure storage
"""
import os
import re
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.config import settings

router = APIRouter()


def sanitize_filename(filename: str) -> str:
    """Sanitize uploaded filename"""
    # Remove path components
    filename = os.path.basename(filename)
    # Replace spaces and special chars
    filename = re.sub(r"[^\w\s\-.]", "_", filename)
    filename = re.sub(r"\s+", "_", filename)
    return filename


@router.post("/upload")
async def upload_invoice(file: UploadFile = File(...)):
    """
    Upload a manufacturer invoice file (PDF or image).

    Returns a file_id for use in the /extract endpoint.
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
    if ext not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(settings.allowed_extensions_list)}",
        )

    # Read and validate size
    contents = await file.read()
    if len(contents) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    # Check MIME type for PDFs
    if ext == "pdf" and not contents.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid PDF file")

    # Generate unique file ID
    file_id = str(uuid.uuid4())
    safe_name = sanitize_filename(file.filename)
    stored_name = f"{file_id}_{safe_name}"
    file_path = os.path.join(settings.UPLOAD_DIR, stored_name)

    # Save file
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(contents)

    return {
        "file_id": file_id,
        "filename": safe_name,
        "stored_name": stored_name,
        "size_bytes": len(contents),
        "extension": ext,
        "message": "File uploaded successfully. Call /extract to process.",
    }
