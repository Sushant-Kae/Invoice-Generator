# PROJECT STATE

## WORKING FEATURES

- Frontend dashboard is working
- Backend FastAPI server is working
- File upload system is working
- Margin calculations are working
- Invoice generation flow is working
- PostgreSQL connection is working
- Environment variables are configured
- DOCX/PDF export pipeline exists

## CURRENT MAJOR ISSUES

### 1. Extraction Pipeline Issue

The extraction pipeline is incorrectly parsing GST summary rows as product rows.

Example wrong extraction:

8640
14112
198

These values from GST summary sections are getting inserted into DESCRIPTION fields.

The parser currently lacks:
- section awareness
- product table detection
- GST summary exclusion
- totals exclusion

### 2. DOCX Template Issue

The invoice generator is recreating invoice layouts using HTML/CSS rendering.

This is incorrect.

The system MUST instead:
- use the provided DOCX template directly
- preserve exact formatting
- preserve borders
- preserve spacing
- preserve alignment
- preserve footer/header
- preserve logo

The final invoice must visually match the provided Shah Enterprises invoice template almost exactly.

## CURRENT TECH STACK

Frontend:
- Next.js
- TypeScript
- TailwindCSS
- shadcn/ui

Backend:
- FastAPI
- SQLAlchemy
- PostgreSQL

Extraction:
- pdfplumber
- PaddleOCR
- Camelot

Generation:
- python-docx
- reportlab

## CURRENT DEVELOPMENT DIRECTION

Focus ONLY on:
1. section-aware extraction
2. DOCX template injection

Avoid unrelated rewrites.