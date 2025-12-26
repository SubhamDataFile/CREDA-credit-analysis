import pdfplumber
import re
import math



PL_LABELS = {
    "Revenue": ["revenue from operations", "total income"],
    "Net Profit": ["profit for the year"],
    "PBT": ["profit before tax"],
    "Interest Expense": ["finance cost"],
    "Depreciation": ["depreciation and amortization"],
}

BS_LABELS = {
    "Current Assets": ["total current assets"],
    "Current Liabilities": ["total current liabilities"],
    "Total Assets": ["total assets"],
    "Net Worth": ["total equity attributable"],
}

STATEMENT_HEADERS = {
    "balance_sheet": [
        "consolidated balance sheet",
        "consolidated statement of financial position",
    ],
    "profit_loss": [
        "consolidated statement of profit and loss",
        "consolidated statement of profit",
    ],
}

STOP_HEADERS = [
    "notes to the consolidated financial statements",
    "notes forming part",
]


def parse_number(text):
    if not isinstance(text, str):
        return None
    text = text.replace(",", "").strip()
    if text.startswith("(") and text.endswith(")"):
        return -float(text[1:-1])
    try:
        return float(text)
    except:
        return None


def scan_pages(pdf):
    return [
        {"page": i, "text": (p.extract_text() or "").lower()}
        for i, p in enumerate(pdf.pages)
    ]


def find_statement_pages(pages, headers):
    return [p["page"] for p in pages if any(h in p["text"] for h in headers)]


def extract_text_values(pdf, pages, label_map):
    """
    Statement-locked, row-based extraction.
    Picks the rightmost numeric value on the matching row.
    """
    results = {}

    for p in pages:
        text = pdf.pages[p].extract_text()
        if not text:
            continue

        for line in text.split("\n"):
            line_l = line.lower()

            for metric, keys in label_map.items():
                if metric in results:
                    continue

                if any(k in line_l for k in keys):
                    numbers = re.findall(r"\(?\d[\d,]*\)?", line)
                    if numbers:
                        value = parse_number(numbers[-1])  # latest year = rightmost
                        if value is not None:
                            results[metric] = value

    return results


def run_financial_analysis(pdf_path):
    financials = {}

    with pdfplumber.open(pdf_path) as pdf:
        pages = scan_pages(pdf)

        bs_pages = find_statement_pages(
            pages, STATEMENT_HEADERS["balance_sheet"]
        )
        pl_pages = find_statement_pages(
            pages, STATEMENT_HEADERS["profit_loss"]
        )

        financials.update(
            extract_text_values(pdf, bs_pages, BS_LABELS)
        )
        financials.update(
            extract_text_values(pdf, pl_pages, PL_LABELS)
        )


    financials.setdefault("Total Debt", 0.0)
    financials.setdefault("Principal Repayment", 0.0)

    

    financials["EBIT"] = (
        financials.get("PBT", 0)
        + financials.get("Interest Expense", 0)
    )

    financials["EBITDA"] = (
        financials["EBIT"]
        + financials.get("Depreciation", 0)
    )

   

    ca = financials.get("Current Assets", 0)
    cl = financials.get("Current Liabilities", 0)
    nw = financials.get("Net Worth", 0)
    td = financials.get("Total Debt", 0)
    ta = financials.get("Total Assets", nw + td)

    rev = financials.get("Revenue", 0)
    np = financials.get("Net Profit", 0)
    ebit = financials.get("EBIT", 0)
    ebitda = financials.get("EBITDA", 0)
    interest = financials.get("Interest Expense", 0)
    principal = financials.get("Principal Repayment", 0)

    capital_employed = nw + td if nw > 0 else None
    debt_service = interest + principal

    ratios = {
        "Current Ratio": ca / cl if cl > 0 else None,
        "Debt-Equity Ratio": td / nw if nw > 0 else None,
        "Interest Coverage Ratio": ebit / interest if interest > 0 else None,
        "DSCR": ebitda / debt_service if debt_service > 0 else None,
        "ROCE": ebit / capital_employed if capital_employed else None,
        "ROA": np / ta if ta > 0 else None,
    }

    return financials, ratios
