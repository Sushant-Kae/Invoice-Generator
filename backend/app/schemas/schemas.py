"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum


class TaxMode(str, Enum):
    CGST_SGST = "cgst_sgst"
    IGST = "igst"
    NONE = "none"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    EXPORTED = "exported"


# ─────────────────────────────────────────────
# Extracted Item (raw from OCR/PDF)
# ─────────────────────────────────────────────

class ExtractedItem(BaseModel):
    item_name: str = ""
    hsn_code: Optional[str] = None
    qty: float = 0.0
    unit: Optional[str] = "Nos"
    purchase_rate: float = 0.0
    amount: float = 0.0
    # UI fields (added during review)
    margin_percent: float = 0.0
    selling_rate: float = 0.0


class ExtractionResult(BaseModel):
    success: bool
    method: str  # "pdfplumber", "camelot", "ocr", "manual"
    items: List[ExtractedItem] = []
    raw_text: Optional[str] = None
    warnings: List[str] = []
    confidence: float = 0.0


# ─────────────────────────────────────────────
# Invoice Items
# ─────────────────────────────────────────────

class InvoiceItemCreate(BaseModel):
    sr_no: int
    item_name: str
    hsn_code: Optional[str] = None
    qty: float
    unit: Optional[str] = "Nos"
    purchase_rate: float = 0.0
    margin_percent: float = 0.0
    selling_rate: float = 0.0
    amount: float = 0.0
    estimated_profit: float = 0.0


class InvoiceItemResponse(BaseModel):
    id: int
    sr_no: int
    item_name: str
    hsn_code: Optional[str]
    qty: float
    unit: Optional[str]
    selling_rate: float
    amount: float
    # Internal fields
    purchase_rate: Optional[float]
    margin_percent: Optional[float]
    estimated_profit: Optional[float]

    class Config:
        from_attributes = True


class InvoiceItemPublic(BaseModel):
    """Customer-facing invoice item - NO internal fields"""
    sr_no: int
    item_name: str
    hsn_code: Optional[str]
    qty: float
    unit: Optional[str]
    selling_rate: float
    amount: float

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Invoice
# ─────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    invoice_number: str
    invoice_date: str
    buyer_name: str
    buyer_gst: Optional[str] = None
    buyer_id: Optional[int] = None
    country_of_shipment: Optional[str] = None
    transport_mode: Optional[str] = None
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    tax_mode: TaxMode = TaxMode.IGST
    cgst_percent: float = 0.0
    sgst_percent: float = 0.0
    igst_percent: float = 18.0
    items: List[InvoiceItemCreate] = []
    notes: Optional[str] = None
    template_id: Optional[int] = None


class InvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_gst: Optional[str] = None
    country_of_shipment: Optional[str] = None
    transport_mode: Optional[str] = None
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    tax_mode: Optional[TaxMode] = None
    cgst_percent: Optional[float] = None
    sgst_percent: Optional[float] = None
    igst_percent: Optional[float] = None
    items: Optional[List[InvoiceItemCreate]] = None
    notes: Optional[str] = None
    status: Optional[InvoiceStatus] = None


class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    invoice_date: str
    buyer_name: str
    buyer_gst: Optional[str]
    buyer_id: Optional[int]
    country_of_shipment: Optional[str]
    transport_mode: Optional[str]
    port_of_loading: Optional[str]
    port_of_discharge: Optional[str]
    tax_mode: str
    cgst_percent: float
    sgst_percent: float
    igst_percent: float
    subtotal: float
    tax_amount: float
    total_amount: float
    total_purchase_value: float
    estimated_profit: float
    status: str
    source_filename: Optional[str]
    docx_filename: Optional[str]
    pdf_filename: Optional[str]
    notes: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    items: List[InvoiceItemResponse] = []

    class Config:
        from_attributes = True


class InvoiceListItem(BaseModel):
    id: int
    invoice_number: str
    invoice_date: str
    buyer_name: str
    total_amount: float
    estimated_profit: float
    status: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Margin Application
# ─────────────────────────────────────────────

class ApplyMarginRequest(BaseModel):
    items: List[ExtractedItem]
    global_margin_percent: float = 0.0
    round_values: bool = True


class ApplyMarginResponse(BaseModel):
    items: List[ExtractedItem]
    total_purchase_value: float
    total_selling_value: float
    estimated_profit: float


# ─────────────────────────────────────────────
# Generate Invoice
# ─────────────────────────────────────────────

class GenerateInvoiceRequest(BaseModel):
    invoice_id: int
    format: str = "both"  # "docx", "pdf", "both"


class GenerateInvoiceResponse(BaseModel):
    invoice_id: int
    docx_url: Optional[str] = None
    pdf_url: Optional[str] = None
    success: bool
    message: str


# ─────────────────────────────────────────────
# Buyer
# ─────────────────────────────────────────────

class BuyerCreate(BaseModel):
    name: str
    gst_number: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class BuyerResponse(BaseModel):
    id: int
    name: str
    gst_number: Optional[str]
    address: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    is_active: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_invoices: int
    monthly_invoices: int
    total_revenue: float
    monthly_revenue: float
    estimated_profit: float
    monthly_profit: float
    draft_count: int
    finalized_count: int
