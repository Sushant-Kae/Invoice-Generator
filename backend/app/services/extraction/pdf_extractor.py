"""
Section-Aware PDF Extraction Engine (v2)

Parses manufacturer invoices with STRICT section awareness to distinguish:
  - PRODUCT TABLE rows (the actual items)
  - TAX SUMMARY rows (GST breakdown — NEVER included as items)
  - TOTALS / FOOTER rows (grand total, amount-in-words, bank details)

Key improvements over v1:
  1. ROW-LEVEL classification inside mixed tables (not just whole-table)
  2. Multiline description MERGING (not splitting)
  3. Stronger GST-summary numeric pattern rejection
  4. Deterministic stop-row detection with configurable sentinels
  5. Comprehensive debug logging

Strategy:
  1. Identify all tables per page
  2. Classify each table as PRODUCT, TAX_SUMMARY, or METADATA
  3. For PRODUCT tables (or MIXED tables):
     a. Find header row
     b. Walk rows with ROW-LEVEL classification
     c. Merge multiline descriptions
     d. Validate each row strictly
  4. Dynamic column normalization using the normalizer engine
"""
import pdfplumber
import re
import logging
from typing import List, Dict, Optional, Tuple

from app.services.extraction.normalizer import (
    normalize_headers, clean_numeric, infer_column_type_from_data, is_hsn_code
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
# Section Detection Constants
# ─────────────────────────────────────────────────────────

# These keywords in a TABLE HEADER row identify a TAX SUMMARY table.
# If ANY of these appear as column headers, the table is NOT a product table.
TAX_SUMMARY_HEADER_KEYWORDS = {
    "taxable value", "taxable amount", "taxable",
    "integrated tax", "central tax", "state tax",
    "total tax amount", "total tax", "tax amount",
    "cgst", "sgst", "igst", "utgst", "cess",
}

# Product table headers — at least 2 must match to classify as a product table
PRODUCT_HEADER_KEYWORDS = {
    "description", "goods", "item", "item name", "product",
    "particulars", "goods and services", "commodity",
    "hsn", "hsn/sac", "hsn code", "sac",
    "quantity", "qty", "rate", "amount", "price",
    "unit", "uom", "per", "unit price",
}

# ─────────────────────────────────────────────────────────
# Stop-Row Sentinels (terminate product row parsing)
# ─────────────────────────────────────────────────────────

STOP_SENTINELS = [
    r"\btotal\b",
    r"\bgrand\s+total\b",
    r"\bsub[\s-]?total\b",
    r"\bamount\s+(chargeable|payable)\b",
    r"\btaxable\s+(value|amount)\b",
    r"\bcentral\s+tax\b",
    r"\bstate\s+tax\b",
    r"\bintegrated\s+tax\b",
    r"\btax\s+amount\b",
    r"\bamount\s+in\s+words\b",
    r"\btotal\s+invoice\s+amount\b",
    r"\bbank\s+details?\b",
    r"\bterms\s+(&|and)\s+conditions?\b",
    r"\bauthori[sz]ed\s+signatory\b",
    r"\breceiver'?s?\s+signature\b",
    r"\be\.?\s*&?\s*o\.?\s*e\.?\b",
]
_STOP_RE = re.compile("|".join(STOP_SENTINELS), re.IGNORECASE)

# ─────────────────────────────────────────────────────────
# GST/Tax Row Detection (row-level, not just table-level)
# ─────────────────────────────────────────────────────────

TAX_ROW_KEYWORDS = [
    r"\bcgst\b", r"\bsgst\b", r"\bigst\b", r"\butgst\b",
    r"\bcess\b", r"\btax\s+rate\b", r"\btax\s+amount\b",
    r"\bcentral\s+tax\b", r"\bstate\s+tax\b", r"\bintegrated\s+tax\b",
    r"\btaxable\s+value\b", r"\btaxable\s+amount\b",
    r"\brate\s+of\s+tax\b", r"\boutput\s+tax\b",
]
_TAX_ROW_RE = re.compile("|".join(TAX_ROW_KEYWORDS), re.IGNORECASE)

# Numeric-only patterns that typically appear in GST summary sections
# e.g., rows with just "8640", "14112", "198" — values without item names
_PURE_NUMERIC_ROW_RE = re.compile(r"^[\d\s.,/%]+$")


def extract_from_pdf(file_path: str) -> Tuple[List[Dict], str, List[str]]:
    """
    Extract invoice items from a PDF file using section-aware parsing.

    Returns:
        (items, method_used, warnings)
    """
    warnings = []
    items = []

    logger.info(f"Starting PDF extraction: {file_path}")

    try:
        with pdfplumber.open(file_path) as pdf:
            all_tables = []
            full_text = ""

            for page_idx, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                full_text += text + "\n"
                logger.debug(f"Page {page_idx + 1}: extracted {len(text)} chars of text")

                # Try line-based extraction first (best for bordered tables)
                tables = page.extract_tables({
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                })
                if not tables:
                    # Fallback to text-based detection
                    tables = page.extract_tables({
                        "vertical_strategy": "text",
                        "horizontal_strategy": "text",
                        "snap_tolerance": 5,
                    })
                if tables:
                    logger.debug(f"Page {page_idx + 1}: found {len(tables)} table(s)")
                    all_tables.extend(tables)

            if all_tables:
                logger.info(f"Total tables found across all pages: {len(all_tables)}")
                items = _extract_product_items(all_tables, warnings)
                if items:
                    logger.info(f"Table extraction yielded {len(items)} item(s)")
                    return items, "pdfplumber_table", warnings

            # Fallback: text-based extraction
            if full_text.strip():
                logger.info("Table extraction yielded 0 items — trying text-based fallback")
                items = _parse_text(full_text, warnings)
                if items:
                    logger.info(f"Text-based extraction yielded {len(items)} item(s)")
                    return items, "pdfplumber_text", warnings

    except Exception as e:
        logger.error(f"pdfplumber error: {str(e)}", exc_info=True)
        warnings.append(f"pdfplumber error: {str(e)}")

    logger.warning("PDF extraction yielded 0 items")
    return [], "pdfplumber_failed", warnings


# ─────────────────────────────────────────────────────────
# Table Classification
# ─────────────────────────────────────────────────────────

def _classify_table(table: List[List]) -> str:
    """
    Classify a table as PRODUCT, TAX_SUMMARY, or METADATA.

    Scans ALL rows for header-like rows (not just the first 3), because in
    mixed Tally-generated invoices, the product header can appear deep in
    the table (e.g., row 8 after company/buyer info rows).

    Returns: "product", "tax_summary", or "metadata"
    """
    if not table or len(table) < 2:
        return "metadata"

    # Scan ALL rows for header keywords (tax or product)
    best_tax_score = 0
    best_product_score = 0
    has_product_header = False

    for row in table:
        if not row:
            continue
        row_str = " ".join(str(c).lower().strip() for c in row if c)

        tax_matches = sum(1 for kw in TAX_SUMMARY_HEADER_KEYWORDS if kw in row_str)
        product_matches = sum(1 for kw in PRODUCT_HEADER_KEYWORDS if kw in row_str)

        best_tax_score = max(best_tax_score, tax_matches)
        best_product_score = max(best_product_score, product_matches)

        if product_matches >= 2:
            has_product_header = True

    # If any row looks like a product header, classify as product
    # (even if a later row has tax headers — they'll be handled at row-level)
    if has_product_header:
        logger.debug(f"Table classified as PRODUCT (header row found, best score={best_product_score})")
        return "product"

    # Pure tax summary table (no product header found)
    if best_tax_score >= 2:
        logger.debug(f"Table classified as TAX_SUMMARY ({best_tax_score} keyword matches)")
        return "tax_summary"

    # Ambiguous — check if it has rows with item-like data (text + numbers)
    data_rows_with_text_and_numbers = 0
    for row in table[1:min(8, len(table))]:
        if not row:
            continue
        row_str = " ".join(str(c) for c in row if c)
        has_text = bool(re.search(r"[a-zA-Z]{3,}", row_str))
        has_numbers = bool(re.search(r"\d+\.?\d*", row_str))
        if has_text and has_numbers:
            data_rows_with_text_and_numbers += 1
    if data_rows_with_text_and_numbers >= 2:
        logger.debug(f"Table classified as PRODUCT (data heuristic: {data_rows_with_text_and_numbers} mixed rows)")
        return "product"

    logger.debug("Table classified as METADATA")
    return "metadata"


# ─────────────────────────────────────────────────────────
# Row-Level Classification
# ─────────────────────────────────────────────────────────

def _classify_row(row: List, header_map: Dict[str, str], raw_headers: List[str]) -> str:
    """
    Classify a single row within a product table.

    Returns: "product", "tax_summary", "stop", "empty", or "skip"

    This is the KEY improvement — instead of only classifying at the table level,
    we classify EACH ROW to handle mixed tables (common in Tally invoices).
    """
    if not row:
        return "empty"

    # Check if all cells are empty
    cell_texts = [str(c).strip() if c else "" for c in row]
    row_text = " ".join(cell_texts).strip()

    if not row_text:
        return "empty"

    # Check for pure-numeric rows FIRST (no alphabetic text at all)
    # These are often GST summary values like "8640", "14112", "198"
    if _PURE_NUMERIC_ROW_RE.match(row_text):
        logger.debug(f"Row classified as SKIP (pure numeric): '{row_text[:80]}'")
        return "skip"

    # Find the item_name column and check its content
    item_name_col = None
    item_text = ""
    for col_idx, header in enumerate(raw_headers):
        if header_map.get(header) == "item_name" and col_idx < len(row):
            item_name_col = col_idx
            item_text = str(row[col_idx]).strip() if row[col_idx] else ""
            break

    # KEY LOGIC: If item_name has real alphabetic text, classify as PRODUCT
    # even if other cells contain tax-related keywords (they're part of the data)
    has_meaningful_item_name = bool(item_text and re.search(r"[a-zA-Z]{2,}", item_text))

    if has_meaningful_item_name:
        # The item_name itself might be a stop word — check that
        if _STOP_RE.search(item_text):
            logger.debug(f"Row classified as STOP (item_name is stop keyword): '{item_text[:60]}'")
            return "stop"
        # Item name looks like real product text — classify as product
        return "product"

    # No meaningful item_name — check the full row text for stop/tax patterns
    if _STOP_RE.search(row_text):
        logger.debug(f"Row classified as STOP: '{row_text[:80]}...'")
        return "stop"

    if _TAX_ROW_RE.search(row_text):
        logger.debug(f"Row classified as TAX_SUMMARY: '{row_text[:80]}...'")
        return "tax_summary"

    # Empty item_name with numeric-only other cells
    if item_name_col is not None and not item_text:
        non_empty_cells = [c for c in cell_texts if c]
        all_numeric = all(re.match(r"^[\d,.\s/%]+$", c) for c in non_empty_cells)
        if all_numeric and non_empty_cells:
            logger.debug(f"Row classified as SKIP (empty item_name, all-numeric cells): '{row_text[:80]}'")
            return "skip"

    return "product"


# ─────────────────────────────────────────────────────────
# Product Item Extraction (Section-Aware)
# ─────────────────────────────────────────────────────────

def _extract_product_items(tables: List[List[List]], warnings: List[str]) -> List[Dict]:
    """
    From all extracted tables, identify PRODUCT tables and parse items.
    Tax summary and metadata tables are excluded.
    """
    all_items = []

    for table_idx, table in enumerate(tables):
        table_type = _classify_table(table)
        logger.info(f"Table {table_idx + 1}: classified as '{table_type}' ({len(table)} rows)")

        if table_type == "tax_summary":
            warnings.append(f"Table {table_idx + 1}: Identified as GST tax summary — excluded")
            continue
        if table_type == "metadata":
            logger.debug(f"Table {table_idx + 1}: Skipping metadata table")
            continue

        items = _parse_product_table(table, warnings, table_idx)
        all_items.extend(items)

    return all_items


def _find_header_row(table: List[List]) -> Tuple[Optional[int], Optional[List[str]]]:
    """
    Find the header row within a product table.
    Returns (header_row_index, clean_header_list) or (None, None).
    """
    for i, row in enumerate(table):
        if not row:
            continue
        row_strs = [str(c).strip().lower() if c else "" for c in row]
        row_text = " ".join(row_strs)

        # Count product header keyword matches
        matches = sum(1 for kw in PRODUCT_HEADER_KEYWORDS if kw in row_text)
        if matches >= 2:
            logger.debug(f"Header row found at index {i}: {[str(c).strip() for c in row if c]}")
            return i, [str(c).strip() if c else "" for c in row]

    return None, None


def _is_empty_row(row: List) -> bool:
    """Check if all cells are empty or whitespace."""
    return not any(str(c).strip() for c in row if c)


# ─────────────────────────────────────────────────────────
# Smart Multiline Handling (Split or Merge)
# ─────────────────────────────────────────────────────────

def _distribute_lines(name_lines: List[str], n_items: int) -> List[str]:
    """
    Distribute item_name lines across n_items.

    If name_lines and n_items match 1:1, return as-is.
    If name_lines > n_items, merge extra lines into previous item's name.

    Example:
      name_lines = ["VM 3040 Pvc Black", "9092 PVC ECO RHEOLOGY", "Cartage 18%", ""]
      n_items = 2
      → ["VM 3040 Pvc Black", "9092 PVC ECO RHEOLOGY Cartage 18%"]
    """
    if len(name_lines) == n_items:
        return name_lines

    if len(name_lines) < n_items:
        # Fewer names than items — pad with empty strings
        return name_lines + [""] * (n_items - len(name_lines))

    # More name lines than items — distribute extras
    # Strategy: assign lines round-robin, but keep them attached to the preceding item
    result = [""] * n_items
    lines_per_item = len(name_lines) / n_items

    for i in range(n_items):
        start = int(i * lines_per_item)
        end = int((i + 1) * lines_per_item)
        assigned = name_lines[start:end]
        result[i] = " ".join(line for line in assigned if line.strip())

    return result

def _handle_multiline_row(row: List, raw_headers: List[str], header_map: Dict[str, str]) -> List[List]:
    """
    Smart multiline row handling that determines whether to SPLIT or MERGE.

    SPLIT when: Multiple products are packed in one row (Tally-style).
      - item_name has N lines AND at least one numeric column also has N lines
      - Each line becomes a separate product row

    MERGE when: A single product has a multi-line description.
      - item_name has N lines BUT numeric columns have only 1 value
      - All description lines are joined into one

    Returns: list of rows (1 row if merged, N rows if split)
    """
    # Check which mapped columns have multiline content
    col_line_counts = {}  # {col_idx: (field, [lines])}

    for col_idx, header in enumerate(raw_headers):
        if col_idx >= len(row) or row[col_idx] is None:
            continue
        field = header_map.get(header)
        if not field:
            continue

        cell_val = str(row[col_idx])
        if "\n" in cell_val:
            lines = [l.strip() for l in cell_val.split("\n") if l.strip()]
            if len(lines) > 1:
                col_line_counts[col_idx] = (field, lines)

    if not col_line_counts:
        return [row]  # No multiline content

    # Determine if this is a SPLIT or MERGE scenario
    # Get line count for item_name (if multiline)
    item_name_lines = None
    item_name_col = None
    for col_idx, (field, lines) in col_line_counts.items():
        if field == "item_name":
            item_name_lines = lines
            item_name_col = col_idx
            break

    if not item_name_lines:
        # No multiline item_name — just take first value for each column
        merged = list(row)
        for col_idx, (field, lines) in col_line_counts.items():
            if field in ("qty", "purchase_rate", "amount"):
                for line in lines:
                    if clean_numeric(line) > 0:
                        merged[col_idx] = line
                        break
            elif field == "hsn_code":
                for line in lines:
                    if is_hsn_code(line.strip()):
                        merged[col_idx] = line.strip()
                        break
        return [merged]

    n_name_lines = len(item_name_lines)

    # Determine the actual number of items by looking at numeric column line counts.
    # Key insight: the number of qty/rate/amount values tells us the TRUE item count.
    # item_name may have MORE lines (sub-descriptions, packaging info, etc.)
    numeric_line_counts = []
    for col_idx, (field, lines) in col_line_counts.items():
        if field in ("qty", "purchase_rate", "amount") and len(lines) >= 2:
            numeric_line_counts.append(len(lines))

    # Determine split count:
    # - If numeric columns agree on a count >= 2, use that as the item count
    # - If item_name lines match numeric lines, great — 1:1 mapping
    # - If item_name has MORE lines, distribute extra lines as sub-descriptions
    if numeric_line_counts:
        # Use the most common count among numeric columns
        from collections import Counter
        count_freq = Counter(numeric_line_counts)
        split_count = count_freq.most_common(1)[0][0]
    else:
        split_count = 0

    should_split = split_count >= 2

    if should_split:
        logger.info(f"Splitting multiline row into {split_count} separate items "
                    f"(name has {n_name_lines} lines, numeric cols have {split_count})")

        # Distribute item_name lines across split_count items
        # If item_name has more lines, merge extras into the previous item's name
        names_per_item = _distribute_lines(item_name_lines, split_count)

        expanded_rows = []
        for line_idx in range(split_count):
            new_row = list(row)  # shallow copy

            # Set the item name (with any merged sub-descriptions)
            new_row[item_name_col] = names_per_item[line_idx]

            # Set other multiline columns
            for col_idx, (field, lines) in col_line_counts.items():
                if col_idx == item_name_col:
                    continue
                if line_idx < len(lines):
                    new_row[col_idx] = lines[line_idx]
                else:
                    new_row[col_idx] = ""

            expanded_rows.append(new_row)
        return expanded_rows
    else:
        # MERGE: Join description lines into one
        merged = list(row)
        merged[item_name_col] = " ".join(item_name_lines)
        logger.debug(f"Merged multiline item_name: '{merged[item_name_col]}'")

        # For other multiline columns, take first non-empty value
        for col_idx, (field, lines) in col_line_counts.items():
            if col_idx == item_name_col:
                continue
            if field in ("qty", "purchase_rate", "amount"):
                for line in lines:
                    if clean_numeric(line) > 0:
                        merged[col_idx] = line
                        break
            elif field == "hsn_code":
                for line in lines:
                    if is_hsn_code(line.strip()):
                        merged[col_idx] = line.strip()
                        break

        return [merged]


# ─────────────────────────────────────────────────────────
# Product Table Parsing (Core Loop)
# ─────────────────────────────────────────────────────────

def _parse_product_table(table: List[List], warnings: List[str], table_idx: int) -> List[Dict]:
    """
    Parse a classified-product table with ROW-LEVEL section awareness.

    1. Find header row
    2. Normalize headers to standard fields
    3. Walk data rows with PER-ROW classification:
       - "product" → parse and validate
       - "tax_summary" → skip (GST section)
       - "stop" → break (totals/footer)
       - "skip" → ignore (pure numeric, etc.)
       - "empty" → ignore
    4. Merge multiline descriptions (not split)
    5. Validate each row as a real product item
    """
    header_idx, raw_headers = _find_header_row(table)
    if header_idx is None:
        # Try first non-empty row as header
        for i, row in enumerate(table):
            if row and any(str(c).strip() for c in row if c):
                header_idx = i
                raw_headers = [str(c).strip() if c else "" for c in row]
                break
        if header_idx is None:
            logger.debug(f"Table {table_idx + 1}: No header row found")
            return []

    header_map = normalize_headers(raw_headers)
    logger.info(f"Table {table_idx + 1}: Header map = {header_map}")

    # Try data-inference for unmapped columns
    data_start = header_idx + 1
    if len(header_map) < 2:
        for col_idx, header in enumerate(raw_headers):
            if header not in header_map and col_idx < len(raw_headers):
                col_data = [
                    str(table[r][col_idx]).strip()
                    for r in range(data_start, min(len(table), data_start + 10))
                    if r < len(table) and col_idx < len(table[r]) and table[r][col_idx]
                ]
                inferred = infer_column_type_from_data(col_data)
                if inferred and inferred not in set(header_map.values()):
                    header_map[header] = inferred
                    logger.debug(f"Inferred column '{header}' as '{inferred}' from data")

    # Need at least item_name or purchase_rate to proceed
    mapped_fields = set(header_map.values())
    if "item_name" not in mapped_fields and "purchase_rate" not in mapped_fields:
        logger.debug(f"Table {table_idx + 1}: Insufficient mapped fields: {mapped_fields}")
        return []

    # Parse data rows with ROW-LEVEL section awareness
    items = []
    consecutive_non_product = 0  # Track consecutive non-product rows

    for row_idx, row in enumerate(table[data_start:], start=data_start):
        if not row:
            continue
        if _is_empty_row(row):
            continue

        # ROW-LEVEL classification (the key improvement)
        row_class = _classify_row(row, header_map, raw_headers)
        logger.debug(f"Table {table_idx + 1}, Row {row_idx}: class='{row_class}'")

        if row_class == "stop":
            logger.info(f"Table {table_idx + 1}: Stop sentinel at row {row_idx}")
            break

        if row_class == "tax_summary":
            consecutive_non_product += 1
            logger.debug(f"Table {table_idx + 1}, Row {row_idx}: Skipping tax summary row")
            # If we see 3+ consecutive non-product rows after finding items,
            # we've likely entered the GST summary section
            if consecutive_non_product >= 3 and items:
                logger.info(f"Table {table_idx + 1}: 3+ consecutive non-product rows — stopping")
                break
            continue

        if row_class in ("skip", "empty"):
            consecutive_non_product += 1
            if consecutive_non_product >= 3 and items:
                logger.info(f"Table {table_idx + 1}: 3+ consecutive non-product rows — stopping")
                break
            continue

        # Row is classified as "product" — reset counter
        consecutive_non_product = 0

        # Smart multiline handling: split packed rows OR merge descriptions
        expanded_rows = _handle_multiline_row(row, raw_headers, header_map)

        for merged_row in expanded_rows:
            item = _parse_single_row(merged_row, raw_headers, header_map)
            if item:
                items.append(item)
                logger.debug(f"Table {table_idx + 1}, Row {row_idx}: Extracted item '{item.get('item_name', '?')}'")

    if items:
        warnings.append(f"Table {table_idx + 1}: Extracted {len(items)} product item(s)")
        logger.info(f"Table {table_idx + 1}: Final extraction: {len(items)} items")

    return items


# ─────────────────────────────────────────────────────────
# Single Row Parsing & Validation
# ─────────────────────────────────────────────────────────

def _parse_single_row(row: List, raw_headers: List[str], header_map: Dict[str, str]) -> Optional[Dict]:
    """
    Parse one table row into a structured item dict.
    Returns None if the row is not a valid product item.

    Validation rules (strict):
      - item_name must exist and have ≥ 2 chars
      - item_name must NOT be purely numeric
      - item_name must NOT match stop sentinels or tax keywords
      - Must have at least one financial value (rate or amount)
      - Rejects rows where most cells are empty
    """
    item: Dict = {}

    for col_idx, header in enumerate(raw_headers):
        if col_idx >= len(row):
            continue
        field = header_map.get(header)
        if not field:
            continue

        cell_value = str(row[col_idx]).strip() if row[col_idx] else ""

        # Clean up qty cells that have unit suffixes like "160.00 Kg"
        if field == "qty":
            qty_match = re.match(r"([\d,.]+)\s*([A-Za-z]*)", cell_value)
            if qty_match:
                item["qty"] = clean_numeric(qty_match.group(1))
                unit_from_qty = qty_match.group(2).strip()
                if unit_from_qty and "unit" not in item:
                    item["unit"] = unit_from_qty
            else:
                item["qty"] = clean_numeric(cell_value)
        elif field in ("purchase_rate", "amount"):
            item[field] = clean_numeric(cell_value)
        elif field == "hsn_code":
            # HSN codes are sometimes multiline in merged cells; take first valid one
            cleaned = cell_value.replace("\n", " ").strip()
            hsn_candidates = re.findall(r"\b\d{4,8}\b", cleaned)
            item["hsn_code"] = hsn_candidates[0] if hsn_candidates else (cleaned if is_hsn_code(cleaned) else None)
        else:
            item[field] = cell_value

    # ── Strict Validation ──

    item_name = item.get("item_name", "").strip()
    purchase_rate = item.get("purchase_rate", 0)
    amount = item.get("amount", 0)
    qty = item.get("qty", 0)

    # V1: Must have a meaningful item name (not just numbers or blanks)
    if not item_name or len(item_name) < 2:
        logger.debug(f"Row rejected: item_name too short or empty: '{item_name}'")
        return None

    # V2: Item name should not be purely numeric (those are serial numbers or tax values)
    if re.match(r"^[\d\s.,/%]+$", item_name):
        logger.debug(f"Row rejected: purely numeric item_name: '{item_name}'")
        return None

    # V3: Item name should have at least some alphabetic characters
    if not re.search(r"[a-zA-Z]{2,}", item_name):
        logger.debug(f"Row rejected: item_name lacks alphabetic content: '{item_name}'")
        return None

    # V4: Must have at least one financial value
    if purchase_rate == 0 and amount == 0:
        # Try to derive rate from amount/qty
        if qty and amount:
            item["purchase_rate"] = round(amount / qty, 2)
        else:
            logger.debug(f"Row rejected: no financial values for '{item_name}'")
            return None

    # V5: Reject rows where item_name looks like a tax/summary label
    if _STOP_RE.search(item_name):
        logger.debug(f"Row rejected: item_name matches stop sentinel: '{item_name}'")
        return None

    # V6: Reject rows where item_name contains GST/tax keywords
    if _TAX_ROW_RE.search(item_name):
        logger.debug(f"Row rejected: item_name matches tax keyword: '{item_name}'")
        return None

    # V7: Reject implausibly short item names that are just symbols/abbreviations
    # common in GST summary tables (e.g., "%", "@", ":")
    cleaned_name = re.sub(r"[\s\d.,@%:()/-]", "", item_name)
    if len(cleaned_name) < 2:
        logger.debug(f"Row rejected: item_name is mostly non-alphabetic: '{item_name}'")
        return None

    # Defaults
    item.setdefault("unit", "Nos")
    item.setdefault("hsn_code", None)
    item.setdefault("qty", 1.0)
    item.setdefault("purchase_rate", 0.0)
    if "amount" not in item or item["amount"] == 0:
        item["amount"] = round(item["purchase_rate"] * item["qty"], 2)

    return item


# ─────────────────────────────────────────────────────────
# Text-Based Fallback Extraction
# ─────────────────────────────────────────────────────────

def _parse_text(text: str, warnings: List[str]) -> List[Dict]:
    """
    Fallback: Parse invoice items from raw text using pattern matching.
    Uses the same section-awareness — stops at sentinel lines.
    """
    items = []
    lines = text.split("\n")
    in_product_section = False

    # Pattern: line with HSN code (4-8 digits) + numeric amounts
    pattern = re.compile(
        r"(.{5,60}?)\s+(\d{4,8})\s+([\d.]+)\s+([A-Z]{1,5})?\s+([\d,.]+)\s+([\d,.]+)",
        re.IGNORECASE
    )

    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue

        # Stop at sentinel lines
        if _STOP_RE.search(line):
            if in_product_section:
                break  # We were in the product section, so stop completely
            continue

        # Skip tax keyword lines
        if _TAX_ROW_RE.search(line):
            continue

        match = pattern.search(line)
        if match:
            in_product_section = True
            groups = match.groups()
            item_name = groups[0].strip()

            # Skip if item name looks like a summary label
            if _STOP_RE.search(item_name):
                continue
            if _TAX_ROW_RE.search(item_name):
                continue
            # Skip purely numeric item names
            if re.match(r"^[\d\s.,]+$", item_name):
                continue

            item = {
                "item_name": item_name,
                "hsn_code": groups[1] if is_hsn_code(groups[1]) else None,
                "qty": clean_numeric(groups[2]),
                "unit": groups[3] or "Nos",
                "purchase_rate": clean_numeric(groups[4]),
                "amount": clean_numeric(groups[5]),
            }
            if item["item_name"] and (item["purchase_rate"] > 0 or item["amount"] > 0):
                items.append(item)

    return items
