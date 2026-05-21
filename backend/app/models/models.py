"""
SQLAlchemy ORM models for Shah Enterprises Invoice Generator
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db.database import Base


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    EXPORTED = "exported"


class TaxMode(str, enum.Enum):
    CGST_SGST = "cgst_sgst"
    IGST = "igst"
    NONE = "none"


class Buyer(Base):
    __tablename__ = "buyers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    gst_number = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    invoices = relationship("Invoice", back_populates="buyer")


class InvoiceTemplate(Base):
    __tablename__ = "invoice_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(100), nullable=False, unique=True, index=True)
    invoice_date = Column(String(50), nullable=False)

    # Buyer reference
    buyer_id = Column(Integer, ForeignKey("buyers.id"), nullable=True)
    buyer_name = Column(String(255), nullable=False)
    buyer_gst = Column(String(50), nullable=True)

    # Shipment details
    country_of_shipment = Column(String(100), nullable=True)
    transport_mode = Column(String(100), nullable=True)
    port_of_loading = Column(String(255), nullable=True)
    port_of_discharge = Column(String(255), nullable=True)

    # Tax configuration
    tax_mode = Column(Enum(TaxMode), default=TaxMode.IGST)
    cgst_percent = Column(Float, default=0.0)
    sgst_percent = Column(Float, default=0.0)
    igst_percent = Column(Float, default=18.0)

    # Financial totals (selling values only - no purchase data)
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)

    # Internal profit tracking (NEVER exported to customer)
    total_purchase_value = Column(Float, default=0.0)
    estimated_profit = Column(Float, default=0.0)

    # Source file
    source_filename = Column(String(500), nullable=True)

    # Status
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)

    # Generated files
    docx_filename = Column(String(500), nullable=True)
    pdf_filename = Column(String(500), nullable=True)

    # Template used
    template_id = Column(Integer, ForeignKey("invoice_templates.id"), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    buyer = relationship("Buyer", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    sr_no = Column(Integer, nullable=False)

    # Public fields (exported to customer invoice)
    item_name = Column(String(500), nullable=False)
    hsn_code = Column(String(20), nullable=True)
    qty = Column(Float, nullable=False, default=0.0)
    unit = Column(String(50), nullable=True, default="Nos")
    selling_rate = Column(Float, nullable=False, default=0.0)
    amount = Column(Float, nullable=False, default=0.0)

    # Internal fields (NEVER exported to customer)
    purchase_rate = Column(Float, nullable=True, default=0.0)
    margin_percent = Column(Float, nullable=True, default=0.0)
    estimated_profit = Column(Float, nullable=True, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    invoice = relationship("Invoice", back_populates="items")
