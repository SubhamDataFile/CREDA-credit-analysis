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
    "Net Profit Margin": {"green": 0.10, "amber": 0.05}
}


PL_LABELS = {
    "Revenue": ["revenue", "total income", "turnover"],
    "Net Profit": ["net profit", "profit after tax", "pat", "profit for the year"],
    "PBT": ["profit before tax", "pbt"],
    "Interest Expense": ["finance cost", "interest"],
    "Depreciation": ["depreciation", "amortisation"]
}

BS_LABELS = {
    "Current Assets": ["current assets"],
    "Current Liabilities": ["current liabilities"],
    "Total Assets": ["total assets"],
    "Net Worth": ["net worth", "equity", "shareholders"]
}


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


def find_consolidated_section(pdf):
    for i, page in enumerate(pdf.pages):
        txt = page.extract_text()
        if txt and "consolidated" in txt.lower():
            return i
    return 0  


def extract_from_tables(tables, label_map):
    results = {}

    for table in tables:
        for row in table:
            if not row or len(row) < 2:
                continue

            label = str(row[0]).lower().strip()

            for metric, keywords in label_map.items():
                if metric in results:
                    continue
                if any(k in label for k in keywords):
                    val = row[-1]
                    if isinstance(val, str) and re.search(r"\d", val):
                        parsed = parse_number(val)
                        if parsed is not None:
                            results[metric] = parsed
    return results


def extract_from_text(pdf, label_map):
    """
    Fallback extraction when tables fail.
    Extremely important for real annual reports.
    """
    results = {}

    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue

        lines = text.lower().split("\n")
        for line in lines:
            for metric, keywords in label_map.items():
                if metric in results:
                    continue
                if any(k in line for k in keywords):
                    nums = re.findall(r"\(?\d[\d,]*\)?", line)
                    if nums:
                        parsed = parse_number(nums[-1])
                        if parsed is not None:
                            results[metric] = parsed
    return results


def run_financial_analysis(pdf_path):
    financial_data = {}

    with pdfplumber.open(pdf_path) as pdf:
        start_page = find_consolidated_section(pdf)

        tables = []
        for p in range(start_page, min(start_page + 40, len(pdf.pages))):
            page_tables = pdf.pages[p].extract_tables()
            if page_tables:
                tables.extend(page_tables)

        pl_data = extract_from_tables(tables, PL_LABELS)
        bs_data = extract_from_tables(tables, BS_LABELS)

        if not pl_data:
            pl_data = extract_from_text(pdf, PL_LABELS)
        if not bs_data:
            bs_data = extract_from_text(pdf, BS_LABELS)

        financial_data.update(pl_data)
        financial_data.update(bs_data)

        financial_data.setdefault("Total Debt", 0.0)

    financial_data["EBIT"] = (
        financial_data.get("PBT", 0) + financial_data.get("Interest Expense", 0)
    )
    financial_data["EBITDA"] = (
        financial_data["EBIT"] + financial_data.get("Depreciation", 0)
    )
    financial_data["Principal Repayment"] = 0.0

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

    return financial_data, ratios, risk_flags
