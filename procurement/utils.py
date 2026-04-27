from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def format_eur(value) -> str:
    """
    Format Decimal/number as EUR in pt-BR style.
    Examples: 5 -> "5,00€", 5000 -> "5.000,00€"
    """
    if value is None:
        return "—"

    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return "—"

    d = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s = f"{d:,.2f}"  # e.g. 5,000.00 (en-style)

    # Swap separators to pt-BR: thousands '.', decimals ','
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s}€"

