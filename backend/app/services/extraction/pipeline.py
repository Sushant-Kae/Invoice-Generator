"""
Master Extraction Pipeline

Orchestrates multiple extraction strategies in priority order:
1. pdfplumber (digital PDFs)
2. OCR fallback (scanned PDFs and images)
3. Manual entry fallback

Always returns user-editable data.
"""
import os
from typing import Tuple, List, Dict, Optional
from app.services.extraction.pdf_extractor import extract_from_pdf
from app.services.extraction.ocr_extractor import extract_from_image, extract_from_scanned_pdf
from app.schemas.schemas import ExtractionResult, ExtractedItem


SUPPORTED_PDF_EXTENSIONS = {".pdf"}
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def run_extraction_pipeline(file_path: str) -> ExtractionResult:
    """
    Run the full extraction pipeline on an uploaded file.

    Strategy:
    1. Detect file type
    2. Try pdfplumber for PDFs
    3. If PDF yields <2 items, try OCR
    4. For images, try OCR directly
    5. Always return editable result to user

    Returns ExtractionResult with items and metadata.
    """
    ext = os.path.splitext(file_path)[1].lower()
    warnings = []
    items = []
    method = "manual"
    confidence = 0.0

    if ext in SUPPORTED_PDF_EXTENSIONS:
        # Strategy 1: pdfplumber
        items, method, pdf_warnings = extract_from_pdf(file_path)
        warnings.extend(pdf_warnings)

        if len(items) >= 1:
            confidence = _calculate_confidence(items, method)
        else:
            # Strategy 2: OCR fallback for scanned PDFs
            warnings.append("pdfplumber extracted 0 items — attempting OCR on scanned PDF")
            items, method, ocr_warnings = extract_from_scanned_pdf(file_path)
            warnings.extend(ocr_warnings)
            confidence = _calculate_confidence(items, method) * 0.75  # Lower confidence for OCR

    elif ext in SUPPORTED_IMAGE_EXTENSIONS:
        # Strategy 3: Image OCR
        items, method, img_warnings = extract_from_image(file_path)
        warnings.extend(img_warnings)
        confidence = _calculate_confidence(items, method) * 0.7

    else:
        warnings.append(f"Unsupported file type: {ext}")
        method = "unsupported"

    # Normalize items into ExtractedItem schemas
    normalized = []
    for i, item in enumerate(items):
        try:
            extracted = ExtractedItem(
                item_name=str(item.get("item_name", "")).strip(),
                hsn_code=item.get("hsn_code") or None,
                qty=float(item.get("qty", 1.0) or 1.0),
                unit=str(item.get("unit", "Nos") or "Nos"),
                purchase_rate=float(item.get("purchase_rate", 0.0) or 0.0),
                amount=float(item.get("amount", 0.0) or 0.0),
                margin_percent=0.0,
                selling_rate=float(item.get("purchase_rate", 0.0) or 0.0),
            )
            # Auto-compute amount if missing
            if extracted.amount == 0 and extracted.purchase_rate > 0:
                extracted.amount = round(extracted.purchase_rate * extracted.qty, 2)
            normalized.append(extracted)
        except Exception as e:
            warnings.append(f"Row {i+1} skipped due to error: {str(e)}")

    # Remove duplicates (same item_name + hsn + qty)
    normalized = _deduplicate(normalized)

    success = len(normalized) > 0

    if not success:
        warnings.append(
            "No items extracted automatically. "
            "Please add items manually in the review screen."
        )

    return ExtractionResult(
        success=success,
        method=method,
        items=normalized,
        warnings=warnings,
        confidence=round(confidence, 2),
    )


def _calculate_confidence(items: List[Dict], method: str) -> float:
    """Estimate extraction confidence based on data completeness"""
    if not items:
        return 0.0

    complete = 0
    for item in items:
        score = 0
        if item.get("item_name"):
            score += 1
        if item.get("hsn_code"):
            score += 1
        if item.get("qty", 0) > 0:
            score += 1
        if item.get("purchase_rate", 0) > 0:
            score += 1
        if item.get("amount", 0) > 0:
            score += 1
        complete += score / 5.0

    base_confidence = (complete / len(items)) * 100

    # Adjust by method reliability
    method_multipliers = {
        "pdfplumber_table": 1.0,
        "pdfplumber_text": 0.85,
        "paddleocr": 0.75,
        "ocr_from_scanned_pdf": 0.70,
    }
    multiplier = method_multipliers.get(method, 0.5)
    return min(base_confidence * multiplier, 99.0)


def _deduplicate(items: List[ExtractedItem]) -> List[ExtractedItem]:
    """Remove exact duplicate rows"""
    seen = set()
    unique = []
    for item in items:
        key = (item.item_name.strip().lower(), item.qty, item.purchase_rate)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique
