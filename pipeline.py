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
    "EBITDA Margin": {"green": 0.20, "amber": 0.12},
    "Net Profit Margin": {"green": 0.10, "amber": 0.05},
}

PL_LABELS = {
    "Revenue": ["revenue from operations", "total income", "revenue"],
    "Net Profit": ["profit for the year", "profit after tax", "pat"],
    "PBT": ["profit before tax"],
    "Interest Expense": ["finance cost", "interest"],
    "Depreciation": ["depreciation", "amortisation"],
}

BS_LABELS = {
    "Current Assets": ["total current assets"],
    "Current Liabilities": ["total current liabilities"],
    "Total Assets": ["total assets"],
    "Net Worth": ["total equity", "equity attributable"],
}

STATEMENT_HEADERS = {
    "balance_sheet": [
        "consolidated balance sheet",
        "consolidated statement of financial position",
    ],
    "profit_loss": [
        "consolidated statement of profit",
        "consolidated statement of profit and loss",
    ],
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
    if value is None or (isinstance(value, float) and math.isnan(value)):
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
    pages = []
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        pages.append({"page": i, "text": text.lower()})
    return pages


def detect_statement_pages(pages, headers):
    return [p["page"] for p in pages if any(h in p["text"] for h in headers)]


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
    header = table[0]
    latest_year = 0
    year_col = None

    for idx, cell in enumerate(header):
        if not cell:
            continue
        match = re.search(r"(20\d{2})", str(cell))
        if match:
            year = int(match.group(1))
            if year > latest_year:
                latest_year = year
                year_col = idx

    return year_col


def extract_from_statement_tables(pdf, pages, label_map):
    results = {}

    for p in pages:
        tables = pdf.pages[p].extract_tables()
        if not tables:
            continue

        for table in tables:
            if not table or len(table) < 2:
                continue

            year_col = detect_latest_year_column(table)
            if year_col is None:
                continue  

            for row in table[1:]:
                if not row or len(row) <= year_col:
                    continue

                label = str(row[0]).lower()

                for metric, keywords in label_map.items():
                    if metric in results:
                        continue
                    if any(k in label for k in keywords):
                        val = row[year_col]
                        parsed = parse_number(val)
                        if parsed is not None:
                            results[metric] = parsed

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

def run_financial_analysis(pdf_path):
    financial_data = {}

    with pdfplumber.open(pdf_path) as pdf:
        pages = scan_document(pdf)

        bs_pages = infer_statement_range(
            detect_statement_pages(pages, STATEMENT_HEADERS["balance_sheet"]),
            pages,
        )
        pl_pages = infer_statement_range(
            detect_statement_pages(pages, STATEMENT_HEADERS["profit_loss"]),
            pages,
        )

        financial_data.update(
            extract_from_statement_tables(pdf, bs_pages, BS_LABELS)
        )
        financial_data.update(
            extract_from_statement_tables(pdf, pl_pages, PL_LABELS)
        )

        financial_data.setdefault("Total Debt", 0.0)
        financial_data.setdefault("Principal Repayment", 0.0)

   
    financial_data["EBIT"] = (
        financial_data.get("PBT", 0) + financial_data.get("Interest Expense", 0)
    )
    financial_data["EBITDA"] = (
        financial_data["EBIT"] + financial_data.get("Depreciation", 0)
    )

    ca = financial_data.get("Current Assets", 0)
    cl = financial_data.get("Current Liabilities", 0)
    nw = financial_data.get("Net Worth", 0)
    td = financial_data.get("Total Debt", 0)
    ta = financial_data.get("Total Assets", nw + td)

    rev = financial_data.get("Revenue", 0)
    np = financial_data.get("Net Profit", 0)
    ebit = financial_data.get("EBIT", 0)
    ebitda = financial_data.get("EBITDA", 0)
    interest = financial_data.get("Interest Expense", 0)

    capital_employed = nw + td if nw > 0 else 0

    ratios = {
        "Current Ratio": ca / cl if cl > 0 else None,
        "Debt-Equity Ratio": td / nw if nw > 0 else None,
        "Interest Coverage Ratio": ebit / interest if interest > 0 else None,
        "DSCR": ebitda / interest if interest > 0 else None,
        "ROCE": ebit / capital_employed if capital_employed > 0 else None,
        "ROA": np / ta if ta > 0 else None,
        "EBITDA Margin": ebitda / rev if rev > 0 else None,
        "Net Profit Margin": np / rev if rev > 0 else None,
    }

    risk_flags = {k: assign_risk_flag(v, k) for k, v in ratios.items()}

    financial_data["_extraction_warnings"] = sanity_check(financial_data)

    return financial_data, ratios, risk_flags
