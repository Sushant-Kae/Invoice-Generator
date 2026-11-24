from datetime import datetime
from types import SimpleNamespace

from app.schemas.schemas import InvoiceListItem


def test_invoice_list_item_includes_generated_file_metadata():
    invoice = SimpleNamespace(
        id=1,
        invoice_number="INV-TEST-1",
        invoice_date="2026-11-23",
        buyer_name="Test Buyer",
        total_amount=100.0,
        estimated_profit=10.0,
        status="exported",
        created_at=datetime(2026, 11, 23),
        docx_filename="invoice.docx",
        pdf_filename="invoice.pdf",
    )

    response = InvoiceListItem.model_validate(invoice)

    assert response.docx_filename == "invoice.docx"
    assert response.pdf_filename == "invoice.pdf"
