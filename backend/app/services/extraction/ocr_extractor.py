"""
OCR Extraction Pipeline

Fallback extraction for scanned PDFs and image-based invoices.
Uses Pillow for image preprocessing.
Attempts PaddleOCR if available, falls back to basic heuristics.
"""
import re
import os
from typing import List, Dict, Tuple, Optional
from PIL import Image
import io

from app.services.extraction.normalizer import clean_numeric, is_hsn_code


def extract_from_image(file_path: str) -> Tuple[List[Dict], str, List[str]]:
    """
    Extract invoice items from an image file (JPG, PNG, WEBP).

    Tries PaddleOCR first, then falls back to placeholder.
    """
    warnings = []

    # Try PaddleOCR
    try:
        return _extract_with_paddleocr(file_path, warnings)
    except ImportError:
        warnings.append("PaddleOCR not installed. Install with: pip install paddleocr paddlepaddle")
    except Exception as e:
        warnings.append(f"OCR error: {str(e)}")

    # Return empty - user will fill manually
    return [], "ocr_failed", warnings


def extract_from_scanned_pdf(file_path: str) -> Tuple[List[Dict], str, List[str]]:
    """
    Extract items from a scanned PDF by converting pages to images first.
    """
    warnings = []
    all_text = ""

    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                # Get page as image
                img = page.to_image(resolution=300)
                img_path = f"/tmp/page_{page.page_number}.png"
                img.save(img_path)

                items, method, page_warnings = extract_from_image(img_path)
                warnings.extend(page_warnings)
                if items:
                    return items, "ocr_from_scanned_pdf", warnings

                # Cleanup
                try:
                    os.remove(img_path)
                except Exception:
                    pass

    except Exception as e:
        warnings.append(f"Scanned PDF processing error: {str(e)}")

    return [], "ocr_failed", warnings


def _extract_with_paddleocr(file_path: str, warnings: List[str]) -> Tuple[List[Dict], str, List[str]]:
    """Extract text using PaddleOCR and parse into invoice items"""
    from paddleocr import PaddleOCR

    ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    result = ocr.ocr(file_path, cls=True)

    if not result:
        return [], "ocr_empty", warnings

    # Reconstruct lines from OCR output
    lines = []
    for page_result in result:
        if not page_result:
            continue
        # Sort by Y coordinate (top to bottom)
        sorted_boxes = sorted(page_result, key=lambda x: x[0][0][1])
        for box in sorted_boxes:
            text = box[1][0].strip()
            if text:
                lines.append(text)

    full_text = "\n".join(lines)
    items = _parse_ocr_lines(lines, warnings)
    return items, "paddleocr", warnings


def _parse_ocr_lines(lines: List[str], warnings: List[str]) -> List[Dict]:
    """
    Parse OCR output lines into structured invoice items.
    Uses heuristics to detect table rows.
    """
    items = []

    # Pattern: line containing HSN code + numbers
    hsn_pattern = re.compile(r"\b(\d{4,8})\b")
    number_pattern = re.compile(r"\b(\d+\.?\d*)\b")

    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue

        # Skip header and footer lines
        lower = line.lower()
        if any(kw in lower for kw in [
            "total", "grand total", "subtotal", "cgst", "sgst", "igst",
            "invoice", "date", "gst", "bank", "terms", "signature", "buyer"
        ]):
            continue

        # Check if line has HSN code
        hsn_match = hsn_pattern.search(line)
        numbers = number_pattern.findall(line)

        if hsn_match and len(numbers) >= 2:
            hsn = hsn_match.group(1)
            numeric_values = [float(n) for n in numbers if float(n) > 0]

            # Heuristic: last large number is amount, second last is rate
            if len(numeric_values) >= 2:
                amount = numeric_values[-1]
                rate = numeric_values[-2]
                qty = numeric_values[-3] if len(numeric_values) >= 3 else 1.0

                # Remove HSN and numbers to get item name
                item_name = line
                item_name = hsn_pattern.sub("", item_name)
                for n in numbers:
                    item_name = item_name.replace(n, "")
                item_name = re.sub(r"\s+", " ", item_name).strip()

                if item_name and len(item_name) > 2:
                    items.append({
                        "item_name": item_name,
                        "hsn_code": hsn,
                        "qty": qty,
                        "unit": "Nos",
                        "purchase_rate": rate,
                        "amount": amount,
                    })

    return items
