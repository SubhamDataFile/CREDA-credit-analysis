import pdfplumber
import re
import math

RISK_THRESHOLDS = {
    "Current Ratio": {"green": 1.5, "amber": 1.0},
    "Debt-Equity Ratio": {"green": 1.0, "amber": 2.0},
    "Interest Coverage Ratio": {"green": 3.0, "amber": 1.5},
    "DSCR": {"green": 1.25, "amber": 1.0},
    "ROCE": {"green": 0.15, "amber": 0.10},
    "ROA": {"green": 0.08, "amber": 0.04},
}

PL_LABELS = {
    "Revenue": ["revenue from operations", "total income", "revenue"],
    "Net Profit": ["profit for the year", "profit after tax", "pat"],
    "PBT": ["profit before tax"],
    "Interest Expense": ["finance cost"],
    "Depreciation": ["depreciation", "amortisation"],
}

BS_LABELS = {
    "Current Assets": ["total current assets"],
    "Current Liabilities": ["total current liabilities"],
    "Total Assets": ["total assets"],
    "Net Worth": ["total equity"],
}

STATEMENT_HEADERS = {
    "balance_sheet": ["balance sheet"],
    "profit_loss": ["statement of profit", "statement of profit and loss"],
}

STOP_HEADERS = [
    "notes to the consolidated financial statements",
    "notes forming part",
    "independent auditor",
]

def parse_number(x):
    if not isinstance(x, str):
        return None
    x = x.replace(",", "").strip()
    if x.startswith("(") and x.endswith(")"):
        return -float(x[1:-1])
    try:
        return float(x)
    except Exception:
        return None


def assign_risk_flag(value, metric):
    if value is None or math.isnan(value):
        return "NA"
    t = RISK_THRESHOLDS.get(metric)
    if not t:
        return "NA"
    if value >= t["green"]:
        return "GREEN"
    elif value >= t["amber"]:
        return "AMBER"
    return "RED"

def scan_document(pdf):
    return [
        {"page": i, "text": (page.extract_text() or "").lower()}
        for i, page in enumerate(pdf.pages)
    ]


def detect_statement_pages(pages, keywords):
    return [
        p["page"] for p in pages if any(k in p["text"] for k in keywords)
    ]


def infer_statement_range(start_pages, pages):
    if not start_pages:
        return []
    start = start_pages[0]
    end = len(pages) - 1
    for p in pages[start + 1 :]:
        if any(stop in p["text"] for stop in STOP_HEADERS):
            end = p["page"] - 1
            break
    return list(range(start, end + 1))

def detect_latest_year_column(table):
    header_text = " ".join(str(c) for c in table[0] if c)
    years = re.findall(r"(20\d{2})", header_text)

    if not years:

        return len(table[0]) - 1

    latest_year = max(int(y) for y in years)

    for idx, cell in enumerate(table[0]):
        if cell and str(latest_year) in str(cell):
            return idx

    return len(table[0]) - 1


def extract_from_statement_tables(pdf, pages, label_map):
    results = {}

    debug(f"Extracting from pages: {pages}")

    for p in pages:
        tables = pdf.pages[p].extract_tables() or []
        debug(f"Page {p}: tables found = {len(tables)}")

        for table in tables:
            debug(f"Table header: {table[0]}")

            year_col = detect_latest_year_column(table)
            debug(f"Detected year column index: {year_col}")

            if year_col is None:
                continue

            for row in table[1:]:
                label = str(row[0]).lower()
                val = row[year_col] if len(row) > year_col else None
                debug(f"Row label: {label} | Value: {val}")

                parsed = parse_number(val)
                if parsed is None:
                    continue

                for metric, keywords in label_map.items():
                    if metric in results:
                        continue
                    if any(k in label for k in keywords):
                        results[metric] = parsed
                        debug(f"✔ Matched {metric} = {parsed}")

    return results


    return results

def sanity_check(financials):
    issues = []

    if financials.get("Revenue", 0) < 1000:
        issues.append("Revenue suspiciously low")

    if financials.get("EBITDA", 0) > financials.get("Revenue", 0):
        issues.append("EBITDA exceeds revenue")

    if financials.get("Net Profit", 0) > financials.get("Revenue", 0):
        issues.append("Net profit exceeds revenue")

    return issues

def debug(msg):
    print(f"[PIPELINE DEBUG] {msg}")


def run_financial_analysis(pdf_path):
    financials = {}

    with pdfplumber.open(pdf_path) as pdf:
        pages = scan_document(pdf)
        debug(f"Total pages in PDF: {len(pages)}")

        bs_candidates = detect_statement_pages(
            pages, STATEMENT_HEADERS["balance_sheet"]
        )
        pl_candidates = detect_statement_pages(
            pages, STATEMENT_HEADERS["profit_loss"]
        )

        debug(f"Balance Sheet start pages: {bs_candidates}")
        debug(f"P&L start pages: {pl_candidates}")

        bs_pages = infer_statement_range(bs_candidates, pages)
        pl_pages = infer_statement_range(pl_candidates, pages)

        debug(f"Balance Sheet page range: {bs_pages}")
        debug(f"P&L page range: {pl_pages}")

        financials.update(
            extract_from_statement_tables(pdf, bs_pages, BS_LABELS)
        )
        financials.update(
            extract_from_statement_tables(pdf, pl_pages, PL_LABELS)
        )

        debug(f"Extracted financials so far: {financials}")


    financials.setdefault("Total Debt", 0.0)
    financials.setdefault("Principal Repayment", 0.0)

    financials["EBIT"] = (
        financials.get("PBT", 0) + financials.get("Interest Expense", 0)
    )
    financials["EBITDA"] = (
        financials["EBIT"] + financials.get("Depreciation", 0)
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

    capital_employed = nw + td if nw > 0 else 0

    ratios = {
        "Current Ratio": ca / cl if cl else None,
        "Debt-Equity Ratio": td / nw if nw else None,
        "Interest Coverage Ratio": ebit / interest if interest else None,
        "DSCR": ebitda / interest if interest else None,
        "ROCE": ebit / capital_employed if capital_employed else None,
        "ROA": np / ta if ta else None,
    }

    risk_flags = {k: assign_risk_flag(v, k) for k, v in ratios.items()}
    financials["_extraction_warnings"] = sanity_check(financials)

    return financials, ratios, risk_flags
