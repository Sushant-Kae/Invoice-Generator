"""
Intelligent Column Normalization Engine

Maps diverse manufacturer invoice column names to standardized internal fields.
Uses STRICT exact matching first, then safe one-directional substring matching.
Priority resolution ensures deterministic results.
"""
import re
import logging
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Field Mapping Dictionaries
# ─────────────────────────────────────────────

# Each mapping is a tuple of (field_name, exact_match_set, substring_patterns)
# substring_patterns are checked ONE-DIRECTIONAL: pattern must be IN the header text
# (never header IN pattern — that was the old bidirectional bug)

FIELD_MAPPINGS: List[Tuple[str, set, List[str]]] = [
    (
        "item_name",
        {
            "description", "item", "item name", "product", "goods", "particulars",
            "commodity", "product name", "item description", "desc", "product description",
            "name of goods", "article", "material", "product detail", "details",
            "items", "name", "product/description", "goods and services",
            "description of goods", "name of product",
        },
        # Substring patterns: these must appear IN the header for a match
        ["description", "particulars", "goods", "commodity", "product", "article", "material"],
    ),
    (
        "hsn_code",
        {
            "hsn", "hsn code", "hsn/sac", "hsn no", "hsn number", "sac", "sac code",
            "harmonized code", "tariff code", "hs code", "hscode", "hsn codes",
            "hsn/sac code", "commodity code", "chapter heading",
        },
        ["hsn", "sac", "tariff"],
    ),
    (
        "qty",
        {
            "qty", "quantity", "pcs", "pieces", "units", "no of bags",
            "bags", "cartons", "boxes", "packs", "unit qty",
            "total qty", "quantity (kg)", "net qty", "number",
        },
        ["quantity", "qty"],
    ),
    (
        "unit",
        {
            "unit", "uom", "uom unit", "unit of measurement", "measure", "unit type",
            "units", "per",
        },
        # No substring matching — too ambiguous ("unit" appears in "unit price")
        [],
    ),
    (
        "purchase_rate",
        {
            "rate", "unit price", "price", "rate per unit", "unit rate", "price/unit",
            "selling price", "cost", "cost per unit", "value per unit", "per unit",
            "rate (inr)", "rate per kg", "basic rate", "price per unit", "rate/unit",
        },
        ["rate", "price"],
    ),
    (
        "amount",
        {
            "amount", "total", "value", "total amount", "total value", "line total",
            "net amount", "subtotal", "sub total", "gross amount",
            "basic amount", "base amount", "amount (inr)",
        },
        # "amount" is safe as substring; avoid "total" (too generic) and
        # "taxable amount/value" (handled separately as exclusion)
        ["amount"],
    ),
]

# Headers that should NEVER be mapped (these belong to GST summary columns)
EXCLUDED_HEADERS = {
    "taxable value", "taxable amount", "taxable",
    "integrated tax", "central tax", "state tax",
    "total tax amount", "total tax", "tax amount",
    "cgst", "sgst", "igst", "utgst", "cess",
    "tax rate", "cgst amount", "sgst amount", "igst amount",
}

# Ambiguous short headers that need special handling
# These ONLY match as exact entries, never via substring
AMBIGUOUS_HEADERS = {"no", "no.", "nos", "sr", "sr.", "sr no", "sr.no", "s.no", "s no", "sl", "sl.", "sl no"}


# ─────────────────────────────────────────────
# Normalization Functions
# ─────────────────────────────────────────────

def normalize_header(raw_header: str) -> Optional[str]:
    """
    Normalize a raw column header from a manufacturer invoice
    to an internal standardized field name.

    Returns one of: item_name, hsn_code, qty, unit, purchase_rate, amount
    or None if unrecognized.

    Strategy (deterministic, priority-ordered):
      1. Reject if header is in EXCLUDED_HEADERS
      2. Skip ambiguous short headers (sr no, no., etc.)
      3. Exact match against each field's known variants
      4. Safe one-directional substring match (pattern IN header)
      5. Return None if no match
    """
    cleaned = raw_header.strip().lower()
    cleaned = re.sub(r"[^\w\s/.]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        return None

    # Step 1: Reject excluded headers (GST summary columns)
    if cleaned in EXCLUDED_HEADERS:
        logger.debug(f"Header '{raw_header}' excluded (GST/tax column)")
        return None

    # Step 2: Skip ambiguous short headers (serial numbers etc.)
    if cleaned in AMBIGUOUS_HEADERS:
        logger.debug(f"Header '{raw_header}' skipped (ambiguous short header)")
        return None

    # Step 3: Exact match (highest priority)
    for field_name, exact_set, _ in FIELD_MAPPINGS:
        if cleaned in exact_set:
            logger.debug(f"Header '{raw_header}' → '{field_name}' (exact match)")
            return field_name

    # Step 4: Safe substring match (pattern must be IN the header, not vice versa)
    # Only match if the substring is a substantial part of the header
    matches = []
    for field_name, _, patterns in FIELD_MAPPINGS:
        for pattern in patterns:
            if pattern in cleaned and len(pattern) >= 3:
                # Require the pattern to be at least 40% of the header length
                # to avoid spurious matches on long headers
                if len(pattern) / len(cleaned) >= 0.3:
                    matches.append((field_name, pattern, len(pattern)))
                    break

    if len(matches) == 1:
        field_name = matches[0][0]
        logger.debug(f"Header '{raw_header}' → '{field_name}' (substring match: '{matches[0][1]}')")
        return field_name
    elif len(matches) > 1:
        # Multiple matches — pick the one with the longest matching pattern
        matches.sort(key=lambda x: x[2], reverse=True)
        field_name = matches[0][0]
        logger.debug(
            f"Header '{raw_header}' → '{field_name}' (best substring match: '{matches[0][1]}', "
            f"competing: {[m[0] for m in matches[1:]]})"
        )
        return field_name

    logger.debug(f"Header '{raw_header}' → None (no match)")
    return None


def normalize_headers(raw_headers: List[str]) -> Dict[str, str]:
    """
    Map a list of raw headers to normalized field names.
    Returns {raw_header: normalized_field}

    Ensures no two headers map to the same field — first match wins.
    """
    mapping = {}
    used_fields = set()

    for header in raw_headers:
        normalized = normalize_header(header)
        if normalized and normalized not in used_fields:
            mapping[header] = normalized
            used_fields.add(normalized)
            logger.debug(f"Column mapping: '{header}' → '{normalized}'")
        elif normalized and normalized in used_fields:
            logger.debug(f"Column '{header}' → '{normalized}' skipped (field already mapped)")

    logger.info(f"Header normalization result: {mapping}")
    return mapping


# ─────────────────────────────────────────────
# Value Normalization
# ─────────────────────────────────────────────

def clean_numeric(value: str) -> float:
    """Extract a float from a string that may contain currency symbols, commas, etc."""
    if not value:
        return 0.0
    # Remove currency symbols and commas
    cleaned = re.sub(r"[₹$€£,\s]", "", str(value))
    # Extract first numeric occurrence
    match = re.search(r"[\d]+\.?[\d]*", cleaned)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return 0.0
    return 0.0


def is_hsn_code(value: str) -> bool:
    """HSN codes are typically 4-8 digit numeric strings"""
    cleaned = str(value).strip().replace(" ", "")
    return bool(re.match(r"^\d{4,8}$", cleaned))


def infer_column_type_from_data(values: List[str]) -> Optional[str]:
    """
    Infer a column's type by analyzing its data when header matching fails.
    """
    non_empty = [v for v in values if str(v).strip()]
    if not non_empty:
        return None

    # Check for HSN codes
    hsn_matches = sum(1 for v in non_empty if is_hsn_code(str(v)))
    if hsn_matches / len(non_empty) > 0.6:
        return "hsn_code"

    # Check for pure numeric (could be qty or rate or amount)
    numeric_count = 0
    numeric_values = []
    for v in non_empty:
        try:
            n = clean_numeric(str(v))
            if n > 0:
                numeric_count += 1
                numeric_values.append(n)
        except Exception:
            pass

    if not non_empty:
        return None

    numeric_ratio = numeric_count / len(non_empty)

    if numeric_ratio > 0.7:
        avg = sum(numeric_values) / len(numeric_values) if numeric_values else 0
        max_val = max(numeric_values) if numeric_values else 0
        # Heuristic: small integers are likely qty
        if avg < 500 and all(v == int(v) for v in numeric_values[:5]):
            return "qty"
        # Large values or averages suggest amount
        if avg > 1000 or max_val > 5000:
            return "amount"
        # Medium values suggest rate
        return "purchase_rate"

    # Text-heavy column is likely item name
    text_count = sum(1 for v in non_empty if re.search(r"[a-zA-Z]", str(v)))
    if text_count / len(non_empty) > 0.7:
        return "item_name"

    return None
