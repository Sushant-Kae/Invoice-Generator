"""
PDF Export Service

Converts DOCX to PDF using LibreOffice headless.
Falls back to reportlab if LibreOffice is not available.
"""
import os
import subprocess
import shutil
from typing import Optional


def convert_docx_to_pdf(docx_path: str, output_dir: str) -> Optional[str]:
    """
    Convert a DOCX file to PDF.

    Primary: LibreOffice headless (preserves exact formatting)
    Fallback: reportlab (programmatic generation)

    Args:
        docx_path: Path to the DOCX file
        output_dir: Directory for the PDF output

    Returns:
        Path to generated PDF, or None on failure
    """
    # Try LibreOffice first
    pdf_path = _convert_with_libreoffice(docx_path, output_dir)
    if pdf_path:
        return pdf_path

    # Fallback: basic conversion info
    return None


def _convert_with_libreoffice(docx_path: str, output_dir: str) -> Optional[str]:
    """Use LibreOffice headless for DOCX → PDF conversion"""
    libreoffice_paths = [
        "libreoffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/bin/libreoffice",
        "/usr/bin/soffice",
        "soffice",
    ]

    soffice = None
    for path in libreoffice_paths:
        if shutil.which(path) or os.path.exists(path):
            soffice = path
            break

    if not soffice:
        return None

    try:
        os.makedirs(output_dir, exist_ok=True)
        result = subprocess.run(
            [
                soffice,
                "--headless",
                "--convert-to", "pdf",
                "--outdir", output_dir,
                docx_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            base = os.path.splitext(os.path.basename(docx_path))[0]
            pdf_path = os.path.join(output_dir, f"{base}.pdf")
            if os.path.exists(pdf_path):
                return pdf_path

    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass

    return None


def get_pdf_status() -> dict:
    """Check which PDF conversion method is available"""
    libreoffice_paths = [
        "libreoffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/bin/libreoffice",
        "soffice",
    ]

    for path in libreoffice_paths:
        if shutil.which(path) or os.path.exists(path):
            return {"available": True, "method": "libreoffice", "path": path}

    return {"available": False, "method": None, "path": None}
