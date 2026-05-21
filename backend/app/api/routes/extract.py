"""
Extraction and Margin Routes

POST /extract  - Run extraction pipeline on uploaded file
POST /apply-margin - Apply profit margins to extracted items
"""
import os
import glob
from fastapi import APIRouter, HTTPException
from typing import Optional

from app.core.config import settings
from app.schemas.schemas import ExtractionResult, ApplyMarginRequest, ApplyMarginResponse
from app.services.extraction.pipeline import run_extraction_pipeline
from app.services.margin_calculator import apply_margin

router = APIRouter()


@router.post("/extract", response_model=ExtractionResult)
async def extract_invoice(file_id: str):
    """
    Run the extraction pipeline on an uploaded manufacturer invoice.

    The file_id is returned from POST /upload.
    Returns structured JSON with extracted items (always editable).
    """
    # Find the uploaded file
    upload_dir = settings.UPLOAD_DIR
    pattern = os.path.join(upload_dir, f"{file_id}_*")
    matches = glob.glob(pattern)

    if not matches:
        raise HTTPException(
            status_code=404,
            detail=f"No file found for file_id: {file_id}",
        )

    file_path = matches[0]

    # Run extraction pipeline
    try:
        result = run_extraction_pipeline(file_path)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}",
        )


@router.post("/apply-margin", response_model=ApplyMarginResponse)
async def apply_margin_endpoint(request: ApplyMarginRequest):
    """
    Apply profit margins to a list of extracted invoice items.

    Internal endpoint - results must NEVER be sent to customers.
    Returns selling rates and profit summary.
    """
    try:
        result = apply_margin(
            items=request.items,
            global_margin_percent=request.global_margin_percent,
            round_values=request.round_values,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Margin calculation failed: {str(e)}",
        )
