"""
Margin Calculation Engine

Handles profit margin calculations internally.
These calculations NEVER appear on customer invoices.
"""
from typing import List
from app.schemas.schemas import ExtractedItem, ApplyMarginResponse


def apply_margin(
    items: List[ExtractedItem],
    global_margin_percent: float = 0.0,
    round_values: bool = True,
) -> ApplyMarginResponse:
    """
    Apply profit margin to a list of extracted items.

    For each item:
      selling_rate = purchase_rate × (1 + margin_percent / 100)
      amount = selling_rate × qty

    If global_margin_percent > 0, it overrides individual item margin.
    """
    updated_items = []
    total_purchase = 0.0
    total_selling = 0.0

    for item in items:
        margin = global_margin_percent if global_margin_percent > 0 else item.margin_percent

        purchase = item.purchase_rate
        qty = item.qty

        selling = purchase * (1 + margin / 100)
        if round_values:
            selling = round(selling, 2)

        amount = selling * qty
        if round_values:
            amount = round(amount, 2)

        profit_per_unit = selling - purchase
        item_profit = profit_per_unit * qty

        total_purchase += purchase * qty
        total_selling += amount

        updated = item.model_copy(update={
            "margin_percent": margin,
            "selling_rate": selling,
            "amount": amount,
        })
        updated_items.append(updated)

    estimated_profit = total_selling - total_purchase

    return ApplyMarginResponse(
        items=updated_items,
        total_purchase_value=round(total_purchase, 2),
        total_selling_value=round(total_selling, 2),
        estimated_profit=round(estimated_profit, 2),
    )


def calculate_taxes(
    subtotal: float,
    tax_mode: str,
    cgst_percent: float = 0.0,
    sgst_percent: float = 0.0,
    igst_percent: float = 18.0,
) -> dict:
    """
    Calculate tax amounts based on mode.

    Returns dict with:
      - cgst_amount
      - sgst_amount
      - igst_amount
      - tax_amount (total)
      - total_with_tax
    """
    cgst_amount = 0.0
    sgst_amount = 0.0
    igst_amount = 0.0

    if tax_mode == "cgst_sgst":
        cgst_amount = round(subtotal * cgst_percent / 100, 2)
        sgst_amount = round(subtotal * sgst_percent / 100, 2)
    elif tax_mode == "igst":
        igst_amount = round(subtotal * igst_percent / 100, 2)

    tax_amount = cgst_amount + sgst_amount + igst_amount
    total = round(subtotal + tax_amount, 2)

    return {
        "cgst_amount": cgst_amount,
        "sgst_amount": sgst_amount,
        "igst_amount": igst_amount,
        "tax_amount": tax_amount,
        "total_with_tax": total,
    }


def number_to_words(amount: float) -> str:
    """Convert amount to words for invoice footer (Indian numbering system)"""
    try:
        # Basic implementation
        units = [
            "", "One", "Two", "Three", "Four", "Five", "Six", "Seven",
            "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
            "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"
        ]
        tens = [
            "", "", "Twenty", "Thirty", "Forty", "Fifty",
            "Sixty", "Seventy", "Eighty", "Ninety"
        ]

        def _to_words(n: int) -> str:
            if n < 0:
                return "Minus " + _to_words(-n)
            if n < 20:
                return units[n]
            if n < 100:
                return tens[n // 10] + (" " + units[n % 10] if n % 10 else "")
            if n < 1000:
                return units[n // 100] + " Hundred" + (" " + _to_words(n % 100) if n % 100 else "")
            if n < 100000:  # Thousands
                return _to_words(n // 1000) + " Thousand" + (" " + _to_words(n % 1000) if n % 1000 else "")
            if n < 10000000:  # Lakhs
                return _to_words(n // 100000) + " Lakh" + (" " + _to_words(n % 100000) if n % 100000 else "")
            return _to_words(n // 10000000) + " Crore" + (" " + _to_words(n % 10000000) if n % 10000000 else "")

        int_part = int(amount)
        decimal_part = round((amount - int_part) * 100)

        words = _to_words(int_part) + " Rupees"
        if decimal_part > 0:
            words += " and " + _to_words(decimal_part) + " Paise"
        words += " Only"

        return words
    except Exception:
        return f"Rupees {amount:.2f} Only"
