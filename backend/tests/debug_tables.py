"""Debug script to inspect raw table structure from PDFs"""
import sys
import os
import pdfplumber

REFERENCE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reference_files")

def debug_pdf(filename):
    filepath = os.path.join(REFERENCE_DIR, filename)
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    print(f"\n{'='*70}")
    print(f"DEBUG: {filename}")
    print(f"{'='*70}")

    with pdfplumber.open(filepath) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            print(f"\n--- Page {page_idx + 1} ---")
            
            text = page.extract_text() or ""
            print(f"Text length: {len(text)}")
            print(f"Text preview (first 500 chars):")
            print(text[:500])
            print("...")
            
            # Try line-based tables
            tables = page.extract_tables({
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
            })
            print(f"\nLine-based tables: {len(tables)}")
            for t_idx, table in enumerate(tables):
                print(f"\n  Table {t_idx + 1}: {len(table)} rows x {max(len(r) for r in table if r) if table else 0} cols")
                for r_idx, row in enumerate(table):
                    row_preview = [str(c)[:30] if c else "(empty)" for c in row]
                    print(f"    Row {r_idx}: {row_preview}")
            
            # Try text-based tables
            tables2 = page.extract_tables({
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "snap_tolerance": 5,
            })
            print(f"\nText-based tables: {len(tables2)}")
            for t_idx, table in enumerate(tables2):
                print(f"\n  Table {t_idx + 1}: {len(table)} rows x {max(len(r) for r in table if r) if table else 0} cols")
                for r_idx, row in enumerate(table[:15]):  # First 15 rows
                    row_preview = [str(c)[:30] if c else "(empty)" for c in row]
                    print(f"    Row {r_idx}: {row_preview}")
                if len(table) > 15:
                    print(f"    ... ({len(table) - 15} more rows)")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "manufacturer_invoice_2.pdf"
    debug_pdf(target)
