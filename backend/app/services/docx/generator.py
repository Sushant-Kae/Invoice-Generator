"""
DOCX Invoice Generation Service — Template-Driven

Uses the ACTUAL Shah Enterprises DOCX template (templates/invoice_template.docx)
and fills it by:
  1. Replacing text in specific known cells (invoice number, date, buyer, etc.)
  2. Cloning the template data row and inserting one row per line item
  3. Filling totals, tax amounts, and amount-in-words into the footer section

Template Structure (single table, 15 rows, 8 columns):
  Row 0:   TAX INVOICE (merged header)
  Row 1:   GST No. (cols 0-1)  |  Tax Invoice No: (cols 2-7)
  Row 2:   GST No. (cols 0-1)  |  Date: (cols 2-7)
  Row 3:   GST No. (cols 0-1)  |  Country/Transport (cols 2-7)
  Row 4:   [blank col headers]  |  QTY. | RATE | AMOUNT INR. (item header)
  Row 5:   [empty template data row — cloned per item]
  Row 6:   [blank]              |  TOTAL (cols 5-6)
  Row 7:   Amount in Words (cols 0-2)  |  Total Amount Before Tax (cols 3-5) | : | value
  Row 8:   Amount in Words (cols 0-2)  |  Add: CGST (cols 3-5) | : | value
  Row 9:   Amount in Words (cols 0-2)  |  Add: SGST (cols 3-5) | : | value
  Row 10:  Bank Details  (cols 0-2)    |  Add: SGST (cols 3-5) | : | value
  Row 11:  Bank Details  (cols 0-2)    |  Add: IGST (cols 3-5) | : | value
  Row 12:  Bank Details  (cols 0-2)    |  Tax Amount: GST (cols 3-5) | : | value
  Row 13:  Bank Details  (cols 0-2)    |  Total Amount After Tax (cols 3-5) | : | value
  Row 14:  Terms & Conditions

SECURITY: Only selling_rate is written. purchase_rate, margin_percent,
and estimated_profit are NEVER written to the document.
"""
import os
import re
import copy
from typing import List, Dict, Any, Optional
from docx import Document
# pyrefly: ignore [missing-import]
from docx.shared import Pt, RGBColor, Emu
# pyrefly: ignore [missing-import]
from docx.oxml.ns import qn
# pyrefly: ignore [missing-import]
from docx.oxml import OxmlElement
# pyrefly: ignore [missing-import]
import lxml.etree as etree

from app.schemas.schemas import InvoiceCreate, InvoiceItemCreate
from app.services.margin_calculator import calculate_taxes, number_to_words
from app.core.config import settings


# ─────────────────────────────────────────────────────────
# Known Row Indices in the Template Table
# ─────────────────────────────────────────────────────────

ROW_TAX_INVOICE   = 0   # "TAX INVOICE" header
ROW_GST_INV_NO    = 1   # GST No. | Tax Invoice No:
ROW_GST_DATE      = 2   # GST No. | Date:
ROW_GST_SHIPMENT  = 3   # GST No. | Country / Transport
ROW_ITEM_HEADER   = 4   # Column headers: QTY. RATE AMOUNT
ROW_ITEM_TEMPLATE = 5   # Template data row (to be cloned)
ROW_TOTAL         = 6   # TOTAL row
ROW_BEFORE_TAX    = 7   # Total Amount Before Tax
ROW_CGST          = 8   # Add: CGST
ROW_SGST          = 9   # Add: SGST
ROW_SGST2         = 10  # Add: SGST (duplicate for multi-tax)
ROW_IGST          = 11  # Add: IGST
ROW_TAX_AMOUNT    = 12  # Tax Amount: GST
ROW_AFTER_TAX     = 13  # Total Amount After Tax
ROW_TERMS         = 14  # Terms & Conditions


def generate_docx_invoice(
    invoice_data: InvoiceCreate,
    output_path: str,
    template_path: Optional[str] = None,
) -> str:
    """
    Generate a DOCX invoice from the master template.

    The template's exact layout, fonts, borders, and cell sizes are preserved.
    Only text content is modified in known cell positions.

    SECURITY: Only selling_rate is included in output. purchase_rate,
    margin_percent, and estimated_profit are NEVER written to the document.
    """
    if not template_path:
        template_path = settings.get_template_path()

    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found: {template_path}")

    doc = Document(template_path)

    # Calculate financial totals
    items = invoice_data.items
    subtotal = sum(item.amount for item in items)
    tax_mode = invoice_data.tax_mode.value if hasattr(invoice_data.tax_mode, 'value') else invoice_data.tax_mode
    taxes = calculate_taxes(
        subtotal=subtotal,
        tax_mode=tax_mode,
        cgst_percent=invoice_data.cgst_percent,
        sgst_percent=invoice_data.sgst_percent,
        igst_percent=invoice_data.igst_percent,
    )
    total_with_tax = taxes["total_with_tax"]
    amount_words = number_to_words(total_with_tax)

    # Get the main table (the template has exactly 1 table)
    if not doc.tables:
        raise ValueError("Template has no tables — cannot generate invoice")

    table = doc.tables[0]

    # ── Fill Invoice Header (Rows 1-3) ──
    _fill_header_cells(table, invoice_data)

    # ── Fill Item Rows (Row 5 is template, clone it per item) ──
    _fill_item_rows(table, items)

    # ── Fill Totals Section (Rows 6-13) ──
    _fill_totals_section(table, subtotal, taxes, total_with_tax, amount_words,
                         invoice_data, tax_mode)

    # ── Save ──
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    doc.save(output_path)
    return output_path


# ─────────────────────────────────────────────────────────
# Header Filling (Rows 1-3)
# ─────────────────────────────────────────────────────────

def _fill_header_cells(table, invoice_data: InvoiceCreate):
    """
    Fill the invoice header cells:
      Row 1, Col 0 (span 2): Buyer GST No.
      Row 1, Col 2 (span 6): Tax Invoice No: <value>
      Row 2, Col 2 (span 6): Date: <value>
      Row 3, Col 0 (span 2): Buyer details (GST, name, address)
      Row 3, Col 2 (span 6): Country/Transport details
    """
    rows = table.rows

    # Row 1: Invoice Number
    _set_cell_text_preserve_format(
        rows[ROW_GST_INV_NO].cells[0],
        f"{invoice_data.buyer_gst or ''}"
    )
    _set_cell_text_preserve_format(
        rows[ROW_GST_INV_NO].cells[2],
        f"Tax Invoice No: {invoice_data.invoice_number}"
    )

    # Row 2: Date
    _set_cell_text_preserve_format(
        rows[ROW_GST_DATE].cells[2],
        f"Date: {invoice_data.invoice_date}"
    )

    # Row 3: Buyer info in left cell, shipment info in right cell
    buyer_lines = []
    if invoice_data.buyer_gst:
        buyer_lines.append(f"GST No: {invoice_data.buyer_gst}")
    buyer_lines.append(f"\n{invoice_data.buyer_name}")
    _set_cell_text_preserve_format(
        rows[ROW_GST_SHIPMENT].cells[0],
        "\n".join(buyer_lines)
    )

    # Shipment details
    shipment_lines = []
    country = invoice_data.country_of_shipment or "INDIA"
    transport = invoice_data.transport_mode or "By Road"
    shipment_lines.append(f"COUNTRY OF SHIPMENT: {country.upper()}")
    shipment_lines.append(f"Mode of Transport: {transport}")
    if invoice_data.port_of_loading:
        shipment_lines.append(f"Port of Loading: {invoice_data.port_of_loading}")
    if invoice_data.port_of_discharge:
        shipment_lines.append(f"Port of Discharge: {invoice_data.port_of_discharge}")
    _set_cell_text_preserve_format(
        rows[ROW_GST_SHIPMENT].cells[2],
        "\n".join(shipment_lines)
    )


# ─────────────────────────────────────────────────────────
# Item Row Insertion
# ─────────────────────────────────────────────────────────

def _fill_item_rows(table, items: List[InvoiceItemCreate]):
    """
    Clone the template data row (Row 5) for each item, preserving exact
    formatting (fonts, borders, cell widths).

    The template row is removed after cloning. Items are inserted between
    the header row (Row 4) and the TOTAL row (originally Row 6).

    Column layout (8 grid columns):
      Cols 0-1: SR NO (span 2 or 1+1)
      Col 2:    Description
      Col 3:    HSN Code
      Col 4:    QTY
      Cols 5-6: RATE (span 2)
      Col 7:    AMOUNT INR.
    """
    rows = table.rows
    if len(rows) <= ROW_ITEM_TEMPLATE:
        return

    template_row = rows[ROW_ITEM_TEMPLATE]

    # Get the XML element BEFORE the template row — we insert after header
    header_tr = rows[ROW_ITEM_HEADER]._tr
    template_tr = template_row._tr
    tbl = table._tbl

    # Clone the template row for each item
    new_trs = []
    for idx, item in enumerate(items, start=1):
        new_tr = copy.deepcopy(template_tr)
        # pyrefly: ignore [missing-import]
        from docx.table import _Row
        new_row = _Row(new_tr, table)

        # Fill cells — ONLY customer-facing data
        cells = new_row.cells

        # Map values to cell indices based on template structure
        # The template has 8 cells per row with merges
        cell_data = _build_cell_data(idx, item, len(cells))

        for ci, value in cell_data.items():
            if ci < len(cells):
                _set_cell_text_preserve_format(cells[ci], value)

        new_trs.append(new_tr)

    # Remove the template data row
    tbl.remove(template_tr)

    # Insert new rows after the header row
    insert_after = header_tr
    for new_tr in new_trs:
        insert_after.addnext(new_tr)
        insert_after = new_tr


def _build_cell_data(sr_no: int, item: InvoiceItemCreate, num_cells: int) -> Dict[int, str]:
    """
    Build a mapping of cell_index -> value for an item row.
    Adjusts based on the actual number of cells in the template row.

    Template cell structure (8 grid cells, 6 actual <w:tc> elements):
      cells[0]         = SR NO (unique tc)
      cells[1]         = Description (unique tc)
      cells[2]=cells[3]= HSN Code (merged, gridSpan=2)
      cells[4]         = QTY (unique tc)
      cells[5]=cells[6]= RATE (merged, gridSpan=2)
      cells[7]         = AMOUNT INR (unique tc)

    SECURITY: Uses item.selling_rate — NEVER item.purchase_rate
    """
    # Safely handle hsn_code=None → empty string (never write literal "None")
    hsn = str(item.hsn_code) if item.hsn_code else ""
    # Safely handle unit
    unit = str(item.unit) if item.unit else "Nos"

    if num_cells >= 8:
        return {
            0: str(sr_no),               # SR NO
            1: str(item.item_name),       # Description (cell[1], unique tc)
            2: hsn,                       # HSN Code (cell[2], merged with cell[3])
            4: f"{item.qty:g} {unit}",    # QTY + unit
            5: f"{item.selling_rate:,.2f}",# RATE (cell[5], merged with cell[6])
            7: f"{item.amount:,.2f}",     # AMOUNT INR.
        }
    elif num_cells >= 6:
        return {
            0: str(sr_no),
            1: str(item.item_name),
            2: hsn,
            3: f"{item.qty:g}",
            4: f"{item.selling_rate:,.2f}",
            5: f"{item.amount:,.2f}",
        }
    else:
        # Minimal fallback
        return {
            0: str(sr_no),
            1: str(item.item_name),
            num_cells - 1: f"{item.amount:,.2f}",
        }


# ─────────────────────────────────────────────────────────
# Totals Section (Rows 6-13)
# ─────────────────────────────────────────────────────────

def _fill_totals_section(table, subtotal: float, taxes: dict,
                         total_with_tax: float, amount_words: str,
                         invoice_data: InvoiceCreate, tax_mode: str):
    """
    Fill the financial totals in the template's known row positions.

    Uses CONTENT-BASED row finding: scans rows for known text markers
    ("Total", "Amount Before Tax", "CGST", etc.) rather than relying on
    fragile arithmetic offsets. Falls back to offset-based lookup if
    markers are not found.
    """
    num_items = len(invoice_data.items)
    offset = num_items - 1  # How many rows were added beyond the original template row
    rows = table.rows

    # Build a content-based row index for known markers
    marker_rows = _find_marker_rows(rows)

    def _get_row_by_marker(marker: str, fallback_original_idx: int):
        """Find a row by content marker, falling back to offset-based index."""
        if marker in marker_rows:
            return marker_rows[marker]
        adjusted = fallback_original_idx + offset
        if adjusted < len(rows):
            return rows[adjusted]
        return None

    # TOTAL row
    total_row = _get_row_by_marker("total", ROW_TOTAL)
    if total_row:
        _set_cell_text_preserve_format(total_row.cells[-1], f"{subtotal:,.2f}")

    # Total Amount Before Tax
    before_tax_row = _get_row_by_marker("before_tax", ROW_BEFORE_TAX)
    if before_tax_row:
        _set_cell_text_preserve_format(before_tax_row.cells[-1], f"{subtotal:,.2f}")

    # Amount in words — look for the row with "amount in words" or use before_tax_row
    words_row = _get_row_by_marker("amount_words", ROW_BEFORE_TAX)
    if words_row:
        _set_cell_text_preserve_format(
            words_row.cells[0],
            f"Total Invoice Amount in Words (Indian Rupees):\n{amount_words}"
        )

    # CGST
    cgst_row = _get_row_by_marker("cgst", ROW_CGST)
    if cgst_row:
        cgst_val = taxes.get("cgst_amount", 0)
        if tax_mode == "cgst_sgst" and cgst_val > 0:
            _set_cell_text_preserve_format(
                cgst_row.cells[3],
                f"Add: CGST @ {invoice_data.cgst_percent}%"
            )
            _set_cell_text_preserve_format(cgst_row.cells[-1], f"{cgst_val:,.2f}")
        else:
            _set_cell_text_preserve_format(cgst_row.cells[-1], "N/A")

    # SGST
    sgst_row = _get_row_by_marker("sgst", ROW_SGST)
    if sgst_row:
        sgst_val = taxes.get("sgst_amount", 0)
        if tax_mode == "cgst_sgst" and sgst_val > 0:
            _set_cell_text_preserve_format(
                sgst_row.cells[3],
                f"Add: SGST @ {invoice_data.sgst_percent}%"
            )
            _set_cell_text_preserve_format(sgst_row.cells[-1], f"{sgst_val:,.2f}")
        else:
            _set_cell_text_preserve_format(sgst_row.cells[-1], "N/A")

    # SGST duplicate (second row) — clear it
    sgst2_row = _get_row_by_marker("sgst2", ROW_SGST2)
    if sgst2_row:
        _set_cell_text_preserve_format(sgst2_row.cells[-1], "N/A")

    # IGST
    igst_row = _get_row_by_marker("igst", ROW_IGST)
    if igst_row:
        igst_val = taxes.get("igst_amount", 0)
        if tax_mode == "igst" and igst_val > 0:
            _set_cell_text_preserve_format(
                igst_row.cells[3],
                f"Add: IGST @ {invoice_data.igst_percent}%"
            )
            _set_cell_text_preserve_format(igst_row.cells[-1], f"{igst_val:,.2f}")
        else:
            _set_cell_text_preserve_format(igst_row.cells[-1], "N/A")

    # Tax Amount: GST
    tax_row = _get_row_by_marker("tax_amount", ROW_TAX_AMOUNT)
    if tax_row:
        tax_total = taxes.get("tax_amount", 0)
        if tax_total > 0:
            _set_cell_text_preserve_format(tax_row.cells[-1], f"{tax_total:,.2f}")
        else:
            _set_cell_text_preserve_format(tax_row.cells[-1], "N/A")

    # Total Amount After Tax
    after_tax_row = _get_row_by_marker("after_tax", ROW_AFTER_TAX)
    if after_tax_row:
        _set_cell_text_preserve_format(after_tax_row.cells[-1], f"{total_with_tax:,.2f}")


def _find_marker_rows(rows) -> Dict[str, Any]:
    """
    Scan all table rows for known text markers and return a mapping
    of marker_name → row object.

    This makes the totals section resilient to template variations
    (different row counts, inserted/removed rows).
    """
    markers = {}
    sgst_count = 0

    for row in rows:
        row_text = " ".join(
            str(cell.text).strip().lower()
            for cell in row.cells if cell.text
        )

        if "total amount before tax" in row_text or "before tax" in row_text:
            markers["before_tax"] = row
        elif "total amount after tax" in row_text or "after tax" in row_text:
            markers["after_tax"] = row
        elif "amount in words" in row_text or "amount chargeable" in row_text:
            markers["amount_words"] = row
        elif "tax amount" in row_text and "gst" in row_text:
            markers["tax_amount"] = row
        elif re.search(r"\bcgst\b", row_text):
            markers["cgst"] = row
        elif re.search(r"\bsgst\b", row_text):
            sgst_count += 1
            if sgst_count == 1:
                markers["sgst"] = row
            else:
                markers["sgst2"] = row
        elif re.search(r"\bigst\b", row_text):
            markers["igst"] = row
        elif re.search(r"^\s*total\s*$", row_text) or row_text.strip() == "total":
            markers["total"] = row

    return markers


# ─────────────────────────────────────────────────────────
# Cell Text Replacement (Format Preserving)
# ─────────────────────────────────────────────────────────

def _set_cell_text_preserve_format(cell, text: str):
    """
    Set text in a cell while preserving the original formatting
    (font, size, color, bold, alignment, borders, shading, cell width).

    Strategy:
      1. Snapshot cell-level XML properties (tcPr: borders, shading, width)
      2. If the cell has runs, copy the first run's formatting
      3. Clear all paragraph content
      4. Set new text using the preserved formatting
      5. Restore cell-level XML properties if they were damaged
      6. Handle multiline text by creating multiple paragraphs
    """
    # ── Step 1: Snapshot cell-level XML properties ──
    tc = cell._tc
    tcPr = tc.find(qn('w:tcPr'))
    tcPr_snapshot = copy.deepcopy(tcPr) if tcPr is not None else None

    # ── Step 2: Capture formatting from existing content ──
    first_para = cell.paragraphs[0] if cell.paragraphs else None
    font_props = None
    para_format = None

    if first_para:
        para_format = _capture_paragraph_format(first_para)
        if first_para.runs:
            font_props = _capture_run_format(first_para.runs[0])

    # ── Step 3: Clear ALL existing paragraphs (remove extra ones, keep first) ──
    for para in cell.paragraphs[1:]:
        p = para._element
        p.getparent().remove(p)

    # ── Step 4: Set new text ──
    lines = text.split("\n")

    if cell.paragraphs:
        first_p = cell.paragraphs[0]
        # Clear existing runs
        for run in first_p.runs:
            run._element.getparent().remove(run._element)
        # Also clear any direct text nodes
        for child in list(first_p._element):
            if child.tag.endswith('}r'):
                first_p._element.remove(child)

        # Set first line
        run = first_p.add_run(lines[0])
        if font_props:
            _apply_run_format(run, font_props)
        if para_format:
            _apply_paragraph_format(first_p, para_format)

        # Add remaining lines as new paragraphs
        for line in lines[1:]:
            new_para = cell.add_paragraph()
            run = new_para.add_run(line)
            if font_props:
                _apply_run_format(run, font_props)
            if para_format:
                _apply_paragraph_format(new_para, para_format)

    # ── Step 5: Restore cell-level XML properties ──
    # If our text operations damaged the tcPr, restore it
    if tcPr_snapshot is not None:
        current_tcPr = tc.find(qn('w:tcPr'))
        if current_tcPr is None:
            # tcPr was lost — re-insert it as the first child
            tc.insert(0, tcPr_snapshot)
        else:
            # Restore specific properties that may have been damaged
            for prop_tag in ['w:tcBorders', 'w:shd', 'w:vAlign', 'w:tcW', 'w:tcMar']:
                existing = current_tcPr.find(qn(prop_tag))
                snapshot_prop = tcPr_snapshot.find(qn(prop_tag))
                if snapshot_prop is not None:
                    if existing is not None:
                        current_tcPr.remove(existing)
                    current_tcPr.append(copy.deepcopy(snapshot_prop))


def _capture_run_format(run) -> Dict[str, Any]:
    """Capture font formatting from a run."""
    return {
        "font_name": run.font.name,
        "font_size": run.font.size,
        "bold": run.font.bold,
        "italic": run.font.italic,
        "color": run.font.color.rgb if run.font.color and run.font.color.rgb else None,
    }


def _apply_run_format(run, props: Dict[str, Any]):
    """Apply captured formatting to a run."""
    if props.get("font_name"):
        run.font.name = props["font_name"]
    if props.get("font_size"):
        run.font.size = props["font_size"]
    if props.get("bold") is not None:
        run.font.bold = props["bold"]
    if props.get("italic") is not None:
        run.font.italic = props["italic"]
    if props.get("color"):
        run.font.color.rgb = props["color"]


def _capture_paragraph_format(para) -> Dict[str, Any]:
    """Capture paragraph formatting including alignment and spacing."""
    fmt = para.paragraph_format
    return {
        "alignment": para.alignment,
        "space_before": fmt.space_before,
        "space_after": fmt.space_after,
        "line_spacing": fmt.line_spacing,
        "keep_together": fmt.keep_together,
        "keep_with_next": fmt.keep_with_next,
    }


def _apply_paragraph_format(para, props: Dict[str, Any]):
    """Apply captured paragraph formatting."""
    if props.get("alignment") is not None:
        para.alignment = props["alignment"]
    fmt = para.paragraph_format
    if props.get("space_before") is not None:
        fmt.space_before = props["space_before"]
    if props.get("space_after") is not None:
        fmt.space_after = props["space_after"]
    if props.get("line_spacing") is not None:
        fmt.line_spacing = props["line_spacing"]
    if props.get("keep_together") is not None:
        fmt.keep_together = props["keep_together"]
    if props.get("keep_with_next") is not None:
        fmt.keep_with_next = props["keep_with_next"]
