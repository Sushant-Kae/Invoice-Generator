# CURRENT BUGS

## BUG 1 — GST SUMMARY PARSED AS PRODUCTS

Problem:
GST summary rows are being parsed as product rows.

Wrong extraction example:

8640
14112
198

Expected:
Only actual product rows should be extracted.

Required fix:
- section-aware parsing
- GST summary detection
- stop-keyword detection
- proper table parsing

--------------------------------------------------

## BUG 2 — HTML/CSS INVOICE GENERATION

Problem:
Invoices are being recreated using HTML/CSS.

This changes the original invoice structure completely.

Required fix:
- use DOCX template directly
- placeholder replacement
- dynamic row insertion
- preserve original layout

--------------------------------------------------

## BUG 3 — MULTILINE DESCRIPTION PARSING

Problem:
Multiline product descriptions break row parsing.

Example:

BLACK SEAWEED POWDER
(25 kg x 12 bag)

should become:

BLACK SEAWEED POWDER (25 kg x 12 bag)

Required fix:
- multiline row merging
- row continuation detection

--------------------------------------------------

## BUG 4 — COLUMN NORMALIZATION

Different manufacturer invoices use different column names.

Examples:
- DESCRIPTION
- ITEM NAME
- PRODUCT

All should map to:
item_name

Required fix:
- normalization layer
- dynamic column mapping