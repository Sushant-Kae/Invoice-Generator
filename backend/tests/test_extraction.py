"""
Extraction Pipeline Regression Test Suite

Formal pytest-based tests that guard against:
  - GST summary rows leaking into product items
  - Stop sentinels not halting parsing
  - Multiline descriptions being split instead of merged
  - Header normalizer regressions
  - Row/table classification errors

Run with:
  cd backend && source venv/bin/activate
  python -m pytest tests/test_extraction.py -v
"""
import re
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.extraction.normalizer import (
    normalize_header,
    normalize_headers,
    clean_numeric,
    is_hsn_code,
)
from app.services.extraction.pdf_extractor import (
    _classify_table,
    _classify_row,
    _STOP_RE,
    _TAX_ROW_RE,
)


# ─────────────────────────────────────────────────────────
# Common regex guards — no test item name should match these
# ─────────────────────────────────────────────────────────

TAX_KEYWORDS = [
    "cgst", "sgst", "igst", "taxable", "tax amount",
    "central tax", "state tax", "integrated tax",
]
STOP_KEYWORDS = [
    "total", "grand total", "subtotal", "amount in words",
    "bank details", "terms and conditions",
]


def _assert_no_gst_leakage(items):
    """Assert that no extracted item has a tax keyword in its name."""
    for item in items:
        name = item.get("item_name", "").lower()
        for kw in TAX_KEYWORDS:
            assert kw not in name, (
                f"GST LEAKAGE: Tax keyword '{kw}' found in item_name '{item['item_name']}'"
            )


def _assert_no_stop_leakage(items):
    """Assert that no extracted item has a stop sentinel in its name."""
    for item in items:
        name = item.get("item_name", "")
        assert not _STOP_RE.search(name), (
            f"STOP LEAKAGE: Stop sentinel matched in item_name '{name}'"
        )


def _assert_no_pure_numeric_names(items):
    """Assert that no extracted item has a purely numeric name."""
    for item in items:
        name = item.get("item_name", "")
        assert not re.match(r"^[\d\s.,/%]+$", name), (
            f"NUMERIC NAME: Purely numeric item_name '{name}'"
        )


# ═══════════════════════════════════════════════════════════
# Invoice 1 Tests (manufacturer_invoice_1.pdf)
# ═══════════════════════════════════════════════════════════

class TestInvoice1:
    """Tests for manufacturer_invoice_1.pdf — Supratik stamps/ink invoice."""

    def test_item_count(self, invoice1_items):
        """Should extract exactly 6 items."""
        assert len(invoice1_items) == 6, (
            f"Expected 6 items, got {len(invoice1_items)}: "
            f"{[i.get('item_name') for i in invoice1_items]}"
        )

    def test_method_is_table(self, invoice1_result):
        """Should use pdfplumber table extraction, not text fallback."""
        assert invoice1_result["method"] == "pdfplumber_table"

    def test_no_gst_leakage(self, invoice1_items):
        _assert_no_gst_leakage(invoice1_items)

    def test_no_stop_leakage(self, invoice1_items):
        _assert_no_stop_leakage(invoice1_items)

    def test_no_pure_numeric_names(self, invoice1_items):
        _assert_no_pure_numeric_names(invoice1_items)

    def test_amounts_positive(self, invoice1_items):
        """Every item should have a positive rate and amount."""
        for item in invoice1_items:
            assert item.get("purchase_rate", 0) > 0, (
                f"Item '{item.get('item_name')}' has zero/negative rate"
            )
            assert item.get("amount", 0) > 0, (
                f"Item '{item.get('item_name')}' has zero/negative amount"
            )

    def test_hsn_codes_valid(self, invoice1_items):
        """All items should have valid HSN codes (4-8 digits)."""
        for item in invoice1_items:
            hsn = item.get("hsn_code")
            if hsn:
                assert re.match(r"^\d{4,8}$", hsn), (
                    f"Invalid HSN '{hsn}' for item '{item.get('item_name')}'"
                )

    def test_known_items_present(self, invoice1_items):
        """Spot-check that specific known items are extracted."""
        names = [i.get("item_name", "").lower() for i in invoice1_items]
        assert any("stamp" in n for n in names), "Missing stamp item"
        assert any("ink" in n for n in names), "Missing ink item"
        assert any("polymer" in n for n in names), "Missing polymer item"


# ═══════════════════════════════════════════════════════════
# Invoice 2 Tests (manufacturer_invoice_2.pdf)
# ═══════════════════════════════════════════════════════════

class TestInvoice2:
    """Tests for manufacturer_invoice_2.pdf — Gurbakshish PVC invoice (duplicate pages)."""

    def test_item_count(self, invoice2_items):
        """Should extract exactly 2 items (one per page, dedup happens at pipeline layer)."""
        assert len(invoice2_items) == 2, (
            f"Expected 2 items, got {len(invoice2_items)}: "
            f"{[i.get('item_name') for i in invoice2_items]}"
        )

    def test_method_is_table(self, invoice2_result):
        assert invoice2_result["method"] == "pdfplumber_table"

    def test_no_gst_leakage(self, invoice2_items):
        _assert_no_gst_leakage(invoice2_items)

    def test_no_stop_leakage(self, invoice2_items):
        _assert_no_stop_leakage(invoice2_items)

    def test_no_pure_numeric_names(self, invoice2_items):
        _assert_no_pure_numeric_names(invoice2_items)

    def test_hsn_valid(self, invoice2_items):
        """HSN codes should be valid 4-8 digit strings."""
        for item in invoice2_items:
            hsn = item.get("hsn_code")
            if hsn:
                assert re.match(r"^\d{4,8}$", hsn), (
                    f"Invalid HSN '{hsn}' for item '{item.get('item_name')}'"
                )

    def test_amounts_positive(self, invoice2_items):
        for item in invoice2_items:
            assert item.get("purchase_rate", 0) > 0
            assert item.get("amount", 0) > 0

    def test_gst_values_not_in_items(self, invoice2_items):
        """The specific GST values 8640, 14112, 198 should NOT appear as item amounts."""
        gst_values = {8640.0, 14112.0, 198.0}
        for item in invoice2_items:
            assert item.get("amount") not in gst_values, (
                f"GST value {item.get('amount')} leaked as item amount!"
            )


# ═══════════════════════════════════════════════════════════
# Invoice 3 Tests (manufacturer_invoice_3.pdf)
# ═══════════════════════════════════════════════════════════

class TestInvoice3:
    """Tests for manufacturer_invoice_3.pdf — agricultural products invoice."""

    def test_item_count(self, invoice3_items):
        """Should extract exactly 4 items."""
        assert len(invoice3_items) == 4, (
            f"Expected 4 items, got {len(invoice3_items)}: "
            f"{[i.get('item_name') for i in invoice3_items]}"
        )

    def test_method_is_table(self, invoice3_result):
        assert invoice3_result["method"] == "pdfplumber_table"

    def test_no_gst_leakage(self, invoice3_items):
        _assert_no_gst_leakage(invoice3_items)

    def test_no_stop_leakage(self, invoice3_items):
        _assert_no_stop_leakage(invoice3_items)

    def test_no_pure_numeric_names(self, invoice3_items):
        _assert_no_pure_numeric_names(invoice3_items)

    def test_multiline_merge(self, invoice3_items):
        """Multiline descriptions should be merged, not split.
        'BLACK SEAWEED POWDER' should include '(25 kg x 12 bag)' in the same item."""
        seaweed_items = [
            i for i in invoice3_items
            if "seaweed" in i.get("item_name", "").lower()
        ]
        assert len(seaweed_items) == 1, (
            f"Expected 1 seaweed item, got {len(seaweed_items)}"
        )
        name = seaweed_items[0]["item_name"]
        assert "25 kg" in name or "25kg" in name.replace(" ", ""), (
            f"Multiline merge failed: seaweed item_name is '{name}' "
            f"but should include packaging info"
        )

    def test_known_items_present(self, invoice3_items):
        names = [i.get("item_name", "").lower() for i in invoice3_items]
        assert any("seaweed" in n for n in names), "Missing seaweed item"
        assert any("fulvate" in n or "fulvat" in n for n in names), "Missing potassium fulvate"
        assert any("humate" in n for n in names), "Missing potassium humate"

    def test_amounts_positive(self, invoice3_items):
        for item in invoice3_items:
            assert item.get("purchase_rate", 0) > 0
            assert item.get("amount", 0) > 0


# ═══════════════════════════════════════════════════════════
# Normalizer Unit Tests
# ═══════════════════════════════════════════════════════════

class TestNormalizer:
    """Unit tests for the header normalizer engine."""

    @pytest.mark.parametrize("raw,expected", [
        ("Description", "item_name"),
        ("item name", "item_name"),
        ("product", "item_name"),
        ("particulars", "item_name"),
        ("Goods and Services", "item_name"),
        ("Description of Goods", "item_name"),
        ("HSN/SAC", "hsn_code"),
        ("HSN Code", "hsn_code"),
        ("HSN", "hsn_code"),
        ("Quantity", "qty"),
        ("Qty", "qty"),
        ("Qty.", "qty"),
        ("Rate", "purchase_rate"),
        ("Unit Price", "purchase_rate"),
        ("Price", "purchase_rate"),
        ("Amount", "amount"),
        ("Total Amount", "amount"),
        ("Unit", "unit"),
        ("UOM", "unit"),
    ])
    def test_exact_matches(self, raw, expected):
        result = normalize_header(raw)
        assert result == expected, f"'{raw}' → '{result}', expected '{expected}'"

    @pytest.mark.parametrize("raw", [
        "Taxable Value", "Taxable Amount", "CGST", "SGST", "IGST",
        "Central Tax", "State Tax", "Total Tax Amount", "Tax Amount",
        "Integrated Tax", "Cess",
    ])
    def test_excluded_gst_headers(self, raw):
        result = normalize_header(raw)
        assert result is None, f"GST header '{raw}' should return None, got '{result}'"

    @pytest.mark.parametrize("raw", [
        "Sr No", "S.No", "Sr.", "Sl No", "No.", "Nos",
    ])
    def test_ambiguous_headers_rejected(self, raw):
        result = normalize_header(raw)
        assert result is None, f"Ambiguous header '{raw}' should return None, got '{result}'"

    def test_normalize_headers_no_duplicate_fields(self):
        """Two columns mapping to the same field — first wins."""
        headers = ["Description", "Product Name", "HSN", "Qty", "Rate", "Amount"]
        mapping = normalize_headers(headers)
        fields = list(mapping.values())
        assert len(fields) == len(set(fields)), f"Duplicate fields in mapping: {mapping}"

    def test_clean_numeric(self):
        assert clean_numeric("48,000.00") == 48000.0
        assert clean_numeric("₹1,234.56") == 1234.56
        assert clean_numeric("") == 0.0
        assert clean_numeric("abc") == 0.0
        assert clean_numeric("300.00") == 300.0

    def test_is_hsn_code(self):
        assert is_hsn_code("96110000") is True
        assert is_hsn_code("3215") is True
        assert is_hsn_code("123") is False   # Too short
        assert is_hsn_code("abc") is False
        assert is_hsn_code("123456789") is False  # Too long


# ═══════════════════════════════════════════════════════════
# Table & Row Classification Unit Tests
# ═══════════════════════════════════════════════════════════

class TestClassification:
    """Unit tests for table-level and row-level classification."""

    def test_classify_table_tax_summary(self):
        """A table with ONLY GST header keywords (no product headers) → tax_summary.
        Note: if HSN/SAC appears as a header, the classifier returns 'product'
        because HSN/SAC is in PRODUCT_HEADER_KEYWORDS — row-level classification
        then handles the individual rows. This test uses a pure tax table."""
        table = [
            ["Taxable Value", "Central Tax", "State Tax", "Total Tax Amount"],
            ["48,000.00", "9%", "9%", "8,640.00"],
            ["78,400.00", "9%", "9%", "14,112.00"],
            ["Total", "", "", "22,950.00"],
        ]
        assert _classify_table(table) == "tax_summary"

    def test_classify_table_product(self):
        """A table with product header keywords should classify as product."""
        table = [
            ["Sr No", "Description", "HSN", "Qty", "Rate", "Amount"],
            ["1", "Widget", "12345678", "10", "100.00", "1000.00"],
        ]
        assert _classify_table(table) == "product"

    def test_classify_table_metadata(self):
        """A table with no header keywords and < 2 rows → metadata."""
        table = [
            ["Company Name: XYZ"],
        ]
        assert _classify_table(table) == "metadata"

    def test_classify_row_stop_detection(self):
        """A row with 'Grand Total' in the item_name column → stop."""
        header_map = {"Description": "item_name", "Amount": "amount"}
        raw_headers = ["Description", "Amount"]
        row = ["Grand Total", "50,000.00"]
        assert _classify_row(row, header_map, raw_headers) == "stop"

    def test_classify_row_tax_detection(self):
        """A row with tax keywords but no item_name → tax_summary."""
        header_map = {"Col1": "item_name", "Col2": "amount"}
        raw_headers = ["Col1", "Col2"]
        row = ["", "CGST @ 9%: 4,500.00"]
        assert _classify_row(row, header_map, raw_headers) == "tax_summary"

    def test_classify_row_product(self):
        """A row with a valid item name → product."""
        header_map = {"Description": "item_name", "Qty": "qty", "Amount": "amount"}
        raw_headers = ["Description", "Qty", "Amount"]
        row = ["Black Seaweed Powder", "300", "51,975.00"]
        assert _classify_row(row, header_map, raw_headers) == "product"

    def test_classify_row_empty(self):
        """An all-empty row → empty."""
        header_map = {"Col1": "item_name"}
        raw_headers = ["Col1"]
        row = [""]
        assert _classify_row(row, header_map, raw_headers) == "empty"

    def test_classify_row_pure_numeric_skip(self):
        """A row with only numbers and no text → skip."""
        header_map = {"Col1": "item_name", "Col2": "amount"}
        raw_headers = ["Col1", "Col2"]
        row = ["", "8640"]
        result = _classify_row(row, header_map, raw_headers)
        assert result in ("skip", "tax_summary", "empty"), (
            f"Pure numeric row should not be 'product', got '{result}'"
        )


# ═══════════════════════════════════════════════════════════
# Pipeline Integration Tests
# ═══════════════════════════════════════════════════════════

class TestPipelineIntegration:
    """Integration tests for the full extraction pipeline."""

    def test_pipeline_invoice1(self, reference_dir):
        """Pipeline should return success for invoice 1."""
        from app.services.extraction.pipeline import run_extraction_pipeline
        filepath = os.path.join(reference_dir, "manufacturer_invoice_1.pdf")
        result = run_extraction_pipeline(filepath)
        assert result.success is True
        assert len(result.items) >= 1
        assert result.confidence > 0

    def test_pipeline_confidence_range(self, reference_dir):
        """Confidence should be between 0 and 99."""
        from app.services.extraction.pipeline import run_extraction_pipeline
        filepath = os.path.join(reference_dir, "manufacturer_invoice_1.pdf")
        result = run_extraction_pipeline(filepath)
        assert 0 < result.confidence <= 99.0, (
            f"Confidence {result.confidence} is out of range"
        )

    def test_pipeline_dedup(self, reference_dir):
        """Pipeline should deduplicate identical items from invoice 2's duplicate pages."""
        from app.services.extraction.pipeline import run_extraction_pipeline
        filepath = os.path.join(reference_dir, "manufacturer_invoice_2.pdf")
        result = run_extraction_pipeline(filepath)
        # After dedup, identical items (same name+qty+rate) should be merged
        names = [i.item_name for i in result.items]
        unique_keys = set((i.item_name, i.qty, i.purchase_rate) for i in result.items)
        assert len(unique_keys) == len(result.items), (
            f"Duplicates remain after pipeline dedup: {names}"
        )

    def test_pipeline_no_internal_fields_exposed(self, reference_dir):
        """Pipeline output items should not expose margin/profit in their names."""
        from app.services.extraction.pipeline import run_extraction_pipeline
        filepath = os.path.join(reference_dir, "manufacturer_invoice_1.pdf")
        result = run_extraction_pipeline(filepath)
        for item in result.items:
            name = item.item_name.lower()
            assert "margin" not in name
            assert "profit" not in name
            assert "purchase_rate" not in name
