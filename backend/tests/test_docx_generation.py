"""
DOCX Invoice Generation Test Suite

Tests the template-driven DOCX generator by:
  1. Creating mock InvoiceCreate data
  2. Generating a DOCX to generated/test_output.docx
  3. Re-opening and validating the output

Run with:
  cd backend && ./venv/bin/python -m pytest tests/test_docx_generation.py -v
"""
import os
import sys
import re
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# pyrefly: ignore [missing-import]
from docx import Document
# pyrefly: ignore [missing-import]
from docx.oxml.ns import qn  # noqa: E402 — pyrefly: ignore [missing-import]

from app.schemas.schemas import InvoiceCreate, InvoiceItemCreate, TaxMode
from app.services.docx.generator import generate_docx_invoice


GENERATED_DIR = os.path.join(os.path.dirname(__file__), "..", "generated")
OUTPUT_PATH = os.path.join(GENERATED_DIR, "test_output.docx")


@pytest.fixture(scope="session")
def mock_invoice():
    """Create a mock invoice with 3 items for testing."""
    return InvoiceCreate(
        invoice_number="TEST-2026-001",
        invoice_date="2026-05-21",
        buyer_name="Test Buyer Corp",
        buyer_gst="27ABCDE1234F1Z5",
        tax_mode=TaxMode.IGST,
        igst_percent=18.0,
        items=[
            InvoiceItemCreate(
                sr_no=1,
                item_name="Black Seaweed Powder (25 kg x 12 bag)",
                hsn_code="12345678",
                qty=300,
                unit="Kg",
                purchase_rate=150.0,
                margin_percent=10.0,
                selling_rate=165.0,
                amount=49500.0,
                estimated_profit=4500.0,
            ),
            InvoiceItemCreate(
                sr_no=2,
                item_name="Potassium Humate Flakes 98%",
                hsn_code="38249090",
                qty=500,
                unit="Kg",
                purchase_rate=50.0,
                margin_percent=10.0,
                selling_rate=55.0,
                amount=27500.0,
                estimated_profit=2500.0,
            ),
            InvoiceItemCreate(
                sr_no=3,
                item_name="VM 3040 PVC Black",
                hsn_code=None,  # Test None HSN handling
                qty=160,
                unit="Kg",
                purchase_rate=270.0,
                margin_percent=11.1,
                selling_rate=300.0,
                amount=48000.0,
                estimated_profit=4800.0,
            ),
        ],
    )


@pytest.fixture(scope="session")
def generated_docx(mock_invoice, template_path):
    """Generate a DOCX invoice and return its path."""
    os.makedirs(GENERATED_DIR, exist_ok=True)
    result_path = generate_docx_invoice(
        invoice_data=mock_invoice,
        output_path=OUTPUT_PATH,
        template_path=template_path,
    )
    assert os.path.exists(result_path), f"Generated DOCX not found: {result_path}"
    return result_path


@pytest.fixture(scope="session")
def output_doc(generated_docx):
    """Re-open the generated DOCX for validation."""
    return Document(generated_docx)


# ═══════════════════════════════════════════════════════════
# File & Structure Tests
# ═══════════════════════════════════════════════════════════

class TestDocxStructure:
    """Verify the DOCX file structure is correct."""

    def test_file_exists(self, generated_docx):
        assert os.path.exists(generated_docx)
        assert os.path.getsize(generated_docx) > 0

    def test_has_table(self, output_doc):
        """Template should have at least one table."""
        assert len(output_doc.tables) >= 1, "No tables found in generated DOCX"

    def test_sufficient_rows(self, output_doc, mock_invoice):
        """Table should have enough rows for header + items + totals."""
        table = output_doc.tables[0]
        num_items = len(mock_invoice.items)
        # At minimum: header rows (4) + item header (1) + items (N) + totals (8+)
        assert len(table.rows) >= 4 + 1 + num_items, (
            f"Table has only {len(table.rows)} rows, expected at least "
            f"{4 + 1 + num_items} for {num_items} items"
        )


# ═══════════════════════════════════════════════════════════
# Content Validation Tests
# ═══════════════════════════════════════════════════════════

class TestDocxContent:
    """Verify the content written to the DOCX is correct."""

    def _get_all_text(self, doc):
        """Extract all text from the document for searching."""
        texts = []
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    texts.append(cell.text)
        return " ".join(texts)

    def test_invoice_number_present(self, output_doc):
        text = self._get_all_text(output_doc)
        assert "TEST-2026-001" in text, "Invoice number not found in output"

    def test_invoice_date_present(self, output_doc):
        text = self._get_all_text(output_doc)
        assert "2026-05-21" in text, "Invoice date not found in output"

    def test_buyer_name_present(self, output_doc):
        text = self._get_all_text(output_doc)
        assert "Test Buyer Corp" in text, "Buyer name not found in output"

    def test_buyer_gst_present(self, output_doc):
        text = self._get_all_text(output_doc)
        assert "27ABCDE1234F1Z5" in text, "Buyer GST not found in output"

    def test_item_names_present(self, output_doc, mock_invoice):
        """All item names should appear in the generated DOCX."""
        text = self._get_all_text(output_doc)
        for item in mock_invoice.items:
            assert item.item_name in text, (
                f"Item name '{item.item_name}' not found in generated DOCX"
            )

    def test_selling_rates_present(self, output_doc, mock_invoice):
        """Selling rates should appear in the document."""
        text = self._get_all_text(output_doc)
        for item in mock_invoice.items:
            # Format matches what _build_cell_data produces
            rate_str = f"{item.selling_rate:,.2f}"
            assert rate_str in text, (
                f"Selling rate '{rate_str}' not found for item '{item.item_name}'"
            )

    def test_hsn_codes_present(self, output_doc):
        """Valid HSN codes should appear; None HSN should not write 'None'."""
        text = self._get_all_text(output_doc)
        assert "12345678" in text, "HSN code '12345678' not found"
        assert "38249090" in text, "HSN code '38249090' not found"

    def test_no_none_text(self, output_doc):
        """The literal string 'None' should never appear in cell text."""
        for table in output_doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    # Allow "None" as part of "N/A" but reject standalone "None"
                    if cell_text == "None":
                        pytest.fail(
                            f"Literal 'None' found in cell. "
                            f"Row text: {[c.text for c in row.cells]}"
                        )


# ═══════════════════════════════════════════════════════════
# Security Tests
# ═══════════════════════════════════════════════════════════

class TestDocxSecurity:
    """Verify that internal/confidential fields are NOT exposed."""

    def _get_all_text(self, doc):
        texts = []
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    texts.append(cell.text.lower())
        return " ".join(texts)

    def test_no_purchase_rate_exposed(self, output_doc, mock_invoice):
        """purchase_rate values should NOT appear in the output."""
        text = self._get_all_text(output_doc)
        for item in mock_invoice.items:
            if item.purchase_rate != item.selling_rate:
                # Only check if purchase != selling (otherwise it's expected)
                purchase_str = f"{item.purchase_rate:,.2f}"
                # The purchase rate might coincidentally appear as part of other numbers
                # so we do a best-effort check
                if purchase_str in text:
                    # Verify it's not just the selling rate
                    selling_str = f"{item.selling_rate:,.2f}"
                    if purchase_str != selling_str:
                        pytest.fail(
                            f"Purchase rate '{purchase_str}' found in DOCX output "
                            f"(selling rate is '{selling_str}'). "
                            f"Internal pricing may be exposed!"
                        )

    def test_no_margin_keyword(self, output_doc):
        text = self._get_all_text(output_doc)
        assert "margin" not in text, "Keyword 'margin' found in generated DOCX"

    def test_no_profit_keyword(self, output_doc):
        text = self._get_all_text(output_doc)
        assert "estimated_profit" not in text, "Keyword 'estimated_profit' found in DOCX"
        assert "estimated profit" not in text, "Keyword 'estimated profit' found in DOCX"


# ═══════════════════════════════════════════════════════════
# Formatting Preservation Tests
# ═══════════════════════════════════════════════════════════

# pyrefly: ignore [missing-import]
from docx.oxml.ns import qn

class TestDocxFormatting:
    """Verify that template formatting is preserved."""

    def test_cell_borders_preserved(self, output_doc):
        """Check that item row cells have border XML (tcBorders) after generation."""
        table = output_doc.tables[0]
        # Check a few item rows (rows after header)
        # The exact row indices depend on the template, but we check for tcBorders
        borders_found = 0
        for row in table.rows:
            for cell in row.cells:
                tc = cell._tc
                tcPr = tc.find(qn('w:tcPr'))
                if tcPr is not None:
                    borders = tcPr.find(qn('w:tcBorders'))
                    if borders is not None:
                        borders_found += 1
        # At least some cells should have borders
        assert borders_found > 0, (
            "No tcBorders found in any cell — formatting may have been lost"
        )

    def test_cell_widths_preserved(self, output_doc):
        """Check that cell widths (tcW) are preserved."""
        table = output_doc.tables[0]
        widths_found = 0
        for row in table.rows:
            for cell in row.cells:
                tc = cell._tc
                tcPr = tc.find(qn('w:tcPr'))
                if tcPr is not None:
                    tcW = tcPr.find(qn('w:tcW'))
                    if tcW is not None:
                        widths_found += 1
        assert widths_found > 0, "No cell widths (tcW) found — layout may be broken"
