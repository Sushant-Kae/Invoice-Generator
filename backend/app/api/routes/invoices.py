"""
Invoice CRUD and Generation Routes

GET  /invoices          - List all invoices
GET  /invoice/{id}      - Get invoice details
POST /invoices          - Create invoice
PUT  /invoice/{id}      - Update invoice
DELETE /invoice/{id}    - Delete invoice
POST /generate          - Generate DOCX + PDF
GET  /history           - Invoice history with stats
GET  /dashboard         - Dashboard statistics
"""
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.models.models import Invoice, InvoiceItem, InvoiceStatus, TaxMode
from app.schemas.schemas import (
    InvoiceCreate, InvoiceUpdate, InvoiceResponse, InvoiceListItem,
    GenerateInvoiceRequest, GenerateInvoiceResponse, DashboardStats
)
from app.services.docx.generator import generate_docx_invoice
from app.services.pdf.converter import convert_docx_to_pdf
from app.services.margin_calculator import calculate_taxes
from app.core.config import settings

router = APIRouter()


def _compute_totals(invoice_data: InvoiceCreate) -> dict:
    """Compute financial totals from invoice items"""
    subtotal = sum(item.amount for item in invoice_data.items)
    total_purchase = sum(item.purchase_rate * item.qty for item in invoice_data.items)
    
    tax_mode = invoice_data.tax_mode.value if hasattr(invoice_data.tax_mode, 'value') else str(invoice_data.tax_mode)
    
    taxes = calculate_taxes(
        subtotal=subtotal,
        tax_mode=tax_mode,
        cgst_percent=invoice_data.cgst_percent,
        sgst_percent=invoice_data.sgst_percent,
        igst_percent=invoice_data.igst_percent,
    )

    return {
        "subtotal": subtotal,
        "tax_amount": taxes["tax_amount"],
        "total_amount": taxes["total_with_tax"],
        "total_purchase_value": total_purchase,
        "estimated_profit": taxes["total_with_tax"] - total_purchase,
    }


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    now = datetime.now(timezone.utc)
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_invoices = db.query(Invoice).count()
    monthly_invoices = db.query(Invoice).filter(
        Invoice.created_at >= current_month_start
    ).count()

    total_revenue = db.query(func.sum(Invoice.total_amount)).scalar() or 0.0
    monthly_revenue = db.query(func.sum(Invoice.total_amount)).filter(
        Invoice.created_at >= current_month_start
    ).scalar() or 0.0

    estimated_profit = db.query(func.sum(Invoice.estimated_profit)).scalar() or 0.0
    monthly_profit = db.query(func.sum(Invoice.estimated_profit)).filter(
        Invoice.created_at >= current_month_start
    ).scalar() or 0.0

    draft_count = db.query(Invoice).filter(Invoice.status == InvoiceStatus.DRAFT).count()
    finalized_count = db.query(Invoice).filter(
        Invoice.status == InvoiceStatus.FINALIZED
    ).count()

    return DashboardStats(
        total_invoices=total_invoices,
        monthly_invoices=monthly_invoices,
        total_revenue=float(total_revenue),
        monthly_revenue=float(monthly_revenue),
        estimated_profit=float(estimated_profit),
        monthly_profit=float(monthly_profit),
        draft_count=draft_count,
        finalized_count=finalized_count,
    )


@router.get("/history", response_model=List[InvoiceListItem])
def get_invoice_history(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get invoice history list"""
    query = db.query(Invoice)
    if status:
        query = query.filter(Invoice.status == status)
    invoices = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()
    return invoices


@router.get("/invoices", response_model=List[InvoiceListItem])
def list_invoices(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Invoice).order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/invoice/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(invoice_data: InvoiceCreate, db: Session = Depends(get_db)):
    """Create a new invoice with items"""
    # Check for duplicate invoice number
    existing = db.query(Invoice).filter(
        Invoice.invoice_number == invoice_data.invoice_number
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Invoice number {invoice_data.invoice_number} already exists",
        )

    totals = _compute_totals(invoice_data)
    
    tax_mode_str = invoice_data.tax_mode.value if hasattr(invoice_data.tax_mode, 'value') else str(invoice_data.tax_mode)

    invoice = Invoice(
        invoice_number=invoice_data.invoice_number,
        invoice_date=invoice_data.invoice_date,
        buyer_name=invoice_data.buyer_name,
        buyer_gst=invoice_data.buyer_gst,
        buyer_id=invoice_data.buyer_id,
        country_of_shipment=invoice_data.country_of_shipment,
        transport_mode=invoice_data.transport_mode,
        port_of_loading=invoice_data.port_of_loading,
        port_of_discharge=invoice_data.port_of_discharge,
        tax_mode=tax_mode_str,
        cgst_percent=invoice_data.cgst_percent,
        sgst_percent=invoice_data.sgst_percent,
        igst_percent=invoice_data.igst_percent,
        notes=invoice_data.notes,
        template_id=invoice_data.template_id,
        **totals,
    )
    db.add(invoice)
    db.flush()

    for item_data in invoice_data.items:
        item = InvoiceItem(
            invoice_id=invoice.id,
            sr_no=item_data.sr_no,
            item_name=item_data.item_name,
            hsn_code=item_data.hsn_code,
            qty=item_data.qty,
            unit=item_data.unit,
            selling_rate=item_data.selling_rate,
            amount=item_data.amount,
            purchase_rate=item_data.purchase_rate,
            margin_percent=item_data.margin_percent,
            estimated_profit=item_data.estimated_profit,
        )
        db.add(item)

    db.commit()
    db.refresh(invoice)
    return invoice


@router.put("/invoice/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: int, invoice_data: InvoiceUpdate, db: Session = Depends(get_db)
):
    """Update an existing invoice"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    for field, value in invoice_data.model_dump(exclude_unset=True, exclude={"items"}).items():
        if hasattr(invoice, field) and value is not None:
            if field == "tax_mode" and hasattr(value, 'value'):
                setattr(invoice, field, value.value)
            elif field == "status" and hasattr(value, 'value'):
                setattr(invoice, field, value.value)
            else:
                setattr(invoice, field, value)

    if invoice_data.items is not None:
        # Delete existing items
        db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).delete()
        # Add new items
        for item_data in invoice_data.items:
            item = InvoiceItem(
                invoice_id=invoice.id,
                sr_no=item_data.sr_no,
                item_name=item_data.item_name,
                hsn_code=item_data.hsn_code,
                qty=item_data.qty,
                unit=item_data.unit,
                selling_rate=item_data.selling_rate,
                amount=item_data.amount,
                purchase_rate=item_data.purchase_rate,
                margin_percent=item_data.margin_percent,
                estimated_profit=item_data.estimated_profit,
            )
            db.add(item)

        # Recalculate totals
        invoice_create_temp = InvoiceCreate(
            invoice_number=invoice.invoice_number,
            invoice_date=invoice.invoice_date,
            buyer_name=invoice.buyer_name,
            tax_mode=invoice_data.tax_mode or invoice.tax_mode,
            cgst_percent=invoice_data.cgst_percent or invoice.cgst_percent,
            sgst_percent=invoice_data.sgst_percent or invoice.sgst_percent,
            igst_percent=invoice_data.igst_percent or invoice.igst_percent,
            items=invoice_data.items,
        )
        totals = _compute_totals(invoice_create_temp)
        for k, v in totals.items():
            setattr(invoice, k, v)

    db.commit()
    db.refresh(invoice)
    return invoice


@router.delete("/invoice/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    db.delete(invoice)
    db.commit()


@router.post("/generate", response_model=GenerateInvoiceResponse)
def generate_invoice(request: GenerateInvoiceRequest, db: Session = Depends(get_db)):
    """
    Generate DOCX and/or PDF for an invoice.

    CRITICAL: Generated documents NEVER contain purchase_rate, margin, or profit.
    """
    invoice = db.query(Invoice).filter(Invoice.id == request.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    file_prefix = f"INV_{invoice.invoice_number.replace('/', '_')}_{invoice.id}"
    docx_path = os.path.join(settings.GENERATED_DIR, f"{file_prefix}.docx")
    pdf_path = None

    # Build invoice data for generation
    from app.schemas.schemas import InvoiceCreate, InvoiceItemCreate, TaxMode
    items_data = [
        InvoiceItemCreate(
            sr_no=item.sr_no,
            item_name=item.item_name,
            hsn_code=item.hsn_code,
            qty=item.qty,
            unit=item.unit or "Nos",
            purchase_rate=item.purchase_rate or 0,
            margin_percent=item.margin_percent or 0,
            selling_rate=item.selling_rate,
            amount=item.amount,
            estimated_profit=item.estimated_profit or 0,
        )
        for item in sorted(invoice.items, key=lambda x: x.sr_no)
    ]

    invoice_create = InvoiceCreate(
        invoice_number=invoice.invoice_number,
        invoice_date=invoice.invoice_date,
        buyer_name=invoice.buyer_name,
        buyer_gst=invoice.buyer_gst,
        country_of_shipment=invoice.country_of_shipment,
        transport_mode=invoice.transport_mode,
        port_of_loading=invoice.port_of_loading,
        port_of_discharge=invoice.port_of_discharge,
        tax_mode=invoice.tax_mode,
        cgst_percent=invoice.cgst_percent,
        sgst_percent=invoice.sgst_percent,
        igst_percent=invoice.igst_percent,
        items=items_data,
        notes=invoice.notes,
    )

    docx_url = None
    pdf_url = None
    warnings = []

    # Generate DOCX
    if request.format in ("docx", "both"):
        try:
            generate_docx_invoice(invoice_create, docx_path)
            invoice.docx_filename = os.path.basename(docx_path)
            docx_url = f"/generated/{invoice.docx_filename}"
        except Exception as e:
            warnings.append(f"DOCX generation failed: {str(e)}")

    # Generate PDF
    if request.format in ("pdf", "both") and os.path.exists(docx_path):
        try:
            pdf_result = convert_docx_to_pdf(docx_path, settings.GENERATED_DIR)
            if pdf_result:
                invoice.pdf_filename = os.path.basename(pdf_result)
                pdf_url = f"/generated/{invoice.pdf_filename}"
        except Exception as e:
            warnings.append(f"PDF conversion failed: {str(e)}")

    # Update invoice status
    invoice.status = InvoiceStatus.EXPORTED if (docx_url or pdf_url) else invoice.status
    db.commit()

    success = bool(docx_url or pdf_url)
    message = "Invoice generated successfully" if success else "Generation failed: " + "; ".join(warnings)

    return GenerateInvoiceResponse(
        invoice_id=invoice.id,
        docx_url=docx_url,
        pdf_url=pdf_url,
        success=success,
        message=message,
    )


@router.get("/invoice/{invoice_id}/download/{file_type}")
def download_invoice(invoice_id: int, file_type: str, db: Session = Depends(get_db)):
    """Download generated DOCX or PDF"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if file_type == "docx":
        filename = invoice.docx_filename
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif file_type == "pdf":
        filename = invoice.pdf_filename
        media_type = "application/pdf"
    else:
        raise HTTPException(status_code=400, detail="file_type must be 'docx' or 'pdf'")

    if not filename:
        raise HTTPException(status_code=404, detail=f"{file_type.upper()} not generated yet")

    file_path = os.path.join(settings.GENERATED_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
    )
