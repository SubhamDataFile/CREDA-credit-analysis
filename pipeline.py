import pdfplumber
import re


# =====================================================
# Label Dictionaries (Consolidated Statements Only)
# =====================================================

PL_LABELS = {
    "Revenue": ["revenue from operations", "total income"],
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


# =====================================================
# Utilities
# =====================================================

def parse_number(text):
    if not isinstance(text, str):
        return None
    text = text.replace(",", "").strip()
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    try:
        return float(text)
    except:
        return None


def scan_pages(pdf):
    return [
        {"page": i, "text": (p.extract_text() or "").lower()}
        for i, p in enumerate(pdf.pages)
    ]



def detect_consolidated_statement_blocks(pages):
    blocks = {}
    current = None

    for p in pages:
        text = p["text"]

        if "standalone" in text:
            current = None
            continue

        if any(h in text for h in STATEMENT_HEADERS["balance_sheet"]):
            current = "Balance Sheet"
            blocks[current] = []

        elif any(h in text for h in STATEMENT_HEADERS["profit_loss"]):
            current = "Profit & Loss"
            blocks[current] = []

        if current:
            if any(stop in text for stop in STOP_HEADERS):
                current = None
            else:
                blocks[current].append(p["page"])

    return blocks



def detect_year_columns(table):
    year_cols = {}
    header = table[0]

    for idx, cell in enumerate(header):
        if not cell:
            continue
        m = re.search(r"(20\d{2})", str(cell))
        if m:
            year_cols[m.group(1)] = idx

    return year_cols


def extract_from_table(table, label_map, statement, page_no, diagnostics):
    results = {}
    year_cols = detect_year_columns(table)

    if not year_cols:
        return results

    latest_year = max(year_cols.keys())
    col_idx = year_cols[latest_year]

    for row in table[1:]:
        if not row or not row[0]:
            continue

        label = str(row[0]).lower()

        for metric, keys in label_map.items():
            if metric in results:
                continue

            if any(k in label for k in keys):
                value = parse_number(str(row[col_idx]))
                if value is None or abs(value) < 1000:
                    continue

                results[metric] = {
                    "value": value,
                    "statement": statement,
                    "page": page_no,
                    "method": "table-column",
                    "confidence": 0.95,
                    "warnings": [],
                }
                diagnostics["metrics_extracted"][metric] = results[metric]

    return results



def extract_net_profit_from_text(pdf, pages):
    """
    Extract Net Profit from flattened text.
    Priority:
    1. Profit after tax / Profit for the year
    2. Total comprehensive income attributable to owners
    """
    candidates = []

    for p in pages:
        text = pdf.pages[p].extract_text() or ""
        for line in text.split("\n"):
            line_l = line.lower()

            if (
                "profit after tax" in line_l
                or "profit for the year" in line_l
                or "attributable to the owners" in line_l
            ):
                nums = re.findall(r"\(?\d[\d,]*\)?", line)
                values = [parse_number(n) for n in nums if parse_number(n)]
                values = [v for v in values if abs(v) >= 1000]
                candidates.extend(values)

    return max(candidates) if candidates else None




def run_financial_analysis(pdf_path):
    metrics = {}

    diagnostics = {
        "pages_scanned": set(),
        "statements_detected": {},
        "metrics_extracted": {},
        "warnings": [],
    }

    with pdfplumber.open(pdf_path) as pdf:
        pages = scan_pages(pdf)
        blocks = detect_consolidated_statement_blocks(pages)

        
        bs_pages = blocks.get("Balance Sheet", [])
        diagnostics["statements_detected"]["Balance Sheet"] = {
            "detected": bool(bs_pages),
            "pages": [p + 1 for p in bs_pages],
        }

        for p in bs_pages:
            diagnostics["pages_scanned"].add(p + 1)
            for table in pdf.pages[p].extract_tables() or []:
                metrics.update(
                    extract_from_table(table, BS_LABELS, "Balance Sheet", p + 1, diagnostics)
                )

        pl_pages = blocks.get("Profit & Loss", [])
        diagnostics["statements_detected"]["Profit & Loss"] = {
            "detected": bool(pl_pages),
            "pages": [p + 1 for p in pl_pages],
        }

        for p in pl_pages:
            diagnostics["pages_scanned"].add(p + 1)
            for table in pdf.pages[p].extract_tables() or []:
                metrics.update(
                    extract_from_table(table, PL_LABELS, "Profit & Loss", p + 1, diagnostics)
                )

        
        net_profit = extract_net_profit_from_text(pdf, pl_pages)
        if net_profit:
            metrics["Net Profit"] = {
                "value": net_profit,
                "statement": "Profit & Loss",
                "method": "text-block",
                "confidence": 0.9,
                "warnings": ["Extracted from flattened text"],
            }

    for k in ["Total Debt", "Principal Repayment"]:
        metrics.setdefault(
            k,
            {
                "value": 0.0,
                "statement": "Manual / Assumed",
                "confidence": 0.5,
                "warnings": ["Defaulted to zero"],
            },
        )

    def v(k): return metrics.get(k, {}).get("value", 0.0)

    metrics["EBIT"] = {
        "value": v("PBT") + v("Interest Expense"),
        "statement": "Derived",
        "confidence": 0.9,
        "warnings": [],
    }

    metrics["EBITDA"] = {
        "value": metrics["EBIT"]["value"] + v("Depreciation"),
        "statement": "Derived",
        "confidence": 0.9,
        "warnings": [],
    }

    ca, cl = v("Current Assets"), v("Current Liabilities")
    nw, td = v("Net Worth"), v("Total Debt")
    ta = v("Total Assets") or (nw + td)

    ratios = {
        "Current Ratio": ca / cl if cl else None,
        "Debt-Equity Ratio": td / nw if nw else None,
        "Interest Coverage Ratio": v("EBIT") / v("Interest Expense") if v("Interest Expense") else None,
        "DSCR": v("EBITDA") / (v("Interest Expense") + v("Principal Repayment"))
        if (v("Interest Expense") + v("Principal Repayment")) else None,
        "ROCE": v("EBIT") / (nw + td) if (nw + td) else None,
        "ROA": v("Net Profit") / ta if ta else None,
    }

    return {
        "metrics": metrics,
        "ratios": ratios,
        "diagnostics": diagnostics,
    }
