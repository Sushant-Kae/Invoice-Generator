"""Health check route"""
from fastapi import APIRouter
from app.services.pdf.converter import get_pdf_status

router = APIRouter()


@router.get("/health")
async def health():
    pdf_status = get_pdf_status()
    return {
        "status": "ok",
        "service": "Shah Enterprises Invoice Generator",
        "pdf_export": pdf_status,
    }
