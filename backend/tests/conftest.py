"""
Shared pytest fixtures for extraction and generation tests.
"""
import os
import sys
import pytest
import logging

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Suppress noisy pdfminer/pdfplumber logs during tests
logging.getLogger("pdfminer").setLevel(logging.ERROR)
logging.getLogger("pdfplumber").setLevel(logging.ERROR)


REFERENCE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reference_files")


@pytest.fixture(scope="session")
def reference_dir():
    """Absolute path to reference_files/"""
    path = os.path.abspath(REFERENCE_DIR)
    assert os.path.isdir(path), f"Reference directory not found: {path}"
    return path


@pytest.fixture(scope="session")
def invoice1_result(reference_dir):
    """Cached extraction result for manufacturer_invoice_1.pdf"""
    from app.services.extraction.pdf_extractor import extract_from_pdf
    filepath = os.path.join(reference_dir, "manufacturer_invoice_1.pdf")
    assert os.path.exists(filepath), f"Invoice 1 not found: {filepath}"
    items, method, warnings = extract_from_pdf(filepath)
    return {"items": items, "method": method, "warnings": warnings}


@pytest.fixture(scope="session")
def invoice2_result(reference_dir):
    """Cached extraction result for manufacturer_invoice_2.pdf"""
    from app.services.extraction.pdf_extractor import extract_from_pdf
    filepath = os.path.join(reference_dir, "manufacturer_invoice_2.pdf")
    assert os.path.exists(filepath), f"Invoice 2 not found: {filepath}"
    items, method, warnings = extract_from_pdf(filepath)
    return {"items": items, "method": method, "warnings": warnings}


@pytest.fixture(scope="session")
def invoice3_result(reference_dir):
    """Cached extraction result for manufacturer_invoice_3.pdf"""
    from app.services.extraction.pdf_extractor import extract_from_pdf
    filepath = os.path.join(reference_dir, "manufacturer_invoice_3.pdf")
    assert os.path.exists(filepath), f"Invoice 3 not found: {filepath}"
    items, method, warnings = extract_from_pdf(filepath)
    return {"items": items, "method": method, "warnings": warnings}


@pytest.fixture(scope="session")
def invoice1_items(invoice1_result):
    return invoice1_result["items"]


@pytest.fixture(scope="session")
def invoice2_items(invoice2_result):
    return invoice2_result["items"]


@pytest.fixture(scope="session")
def invoice3_items(invoice3_result):
    return invoice3_result["items"]


@pytest.fixture(scope="session")
def template_path():
    """Path to the DOCX invoice template"""
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "templates", "invoice_template.docx")
    )
    assert os.path.exists(path), f"Template not found: {path}"
    return path
