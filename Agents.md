# AGENT RULES

IMPORTANT PROJECT RULES:

1. NEVER regenerate the entire project unless explicitly requested.

2. NEVER redesign the frontend/UI unless explicitly requested.

3. NEVER recreate invoices using HTML/CSS rendering.

4. ALWAYS use the provided DOCX invoice template directly.

5. ALWAYS preserve:
- borders
- spacing
- alignment
- logo
- footer
- header
- formatting

6. Extraction must be section-aware.

7. The extraction engine must distinguish:
- product tables
- GST summary tables
- totals sections
- footer sections

8. GST summary rows must NEVER be parsed as product rows.

9. Margin values are INTERNAL ONLY.

10. Final exported invoices must NEVER expose:
- purchase_rate
- margin_percent
- estimated_profit

11. OCR output must ALWAYS go through:
- normalization
- validation
- editable review

before invoice generation.

12. Focus ONLY on:
- extraction reliability
- DOCX template generation
- structured parsing

Avoid unrelated rewrites.