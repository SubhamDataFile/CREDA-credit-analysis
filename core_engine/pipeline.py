import pdfplumber
import re

MIN_TEXT_CHARS = 120          
MAX_FIN_PAGES = 40            
MAX_PREFLIGHT_PAGES = 50     

PL_LABELS = {
    "Revenue": ["revenue from operations", "total income"],
    "PBT": ["profit before tax"],
    "Interest Expense": ["finance cost"],
    "Depreciation": ["depreciation and amortization"],
}

NET_PROFIT_ANCHORS = [
    "profit after tax",
    "profit for the year",
    "total comprehensive income for the year",
]

BS_ANCHORS = {
    "Net Worth": [
        "total equity attributable to equity holders",
        "total equity attributable",
        "total equity",
    ],
    "Total Assets": ["total assets"],
    "Current Assets": ["total current assets"],
    "Current Liabilities": ["total current liabilities"],
}

STATEMENT_HEADERS = {
    "balance_sheet": [
        "consolidated balance sheet",
        "consolidated balance sheets",
        "statement of financial position",
        "consolidated statement of financial position",
    ],
    "profit_loss": [
        "consolidated statement of profit and loss",
        "statement of profit and loss",
        "statement of profit & loss",
        "consolidated statement of profit",
    ],
}


STOP_HEADERS = [
    "notes to the consolidated financial statements",
    "notes forming part",
]


FIN_SECTION_ANCHORS = [
    "annual accounts",
    "financial statements",
    "standalone and consolidated financial statements",
    "consolidated financial statements",
    "financial section",
]

def contains_any(text, phrases):
    return any(p in text for p in phrases)


def is_text_page(text: str) -> bool:
    if not text:
        return False
    return len(text.strip()) >= MIN_TEXT_CHARS


def extract_numbers_from_line(text):
    matches = re.findall(r"\(?₹?\s*[\d,]+(?:\.\d+)?\)?", text)
    values = []

    for m in matches:
        cleaned = (
            m.replace("₹", "")
             .replace(",", "")
             .replace("(", "")
             .replace(")", "")
             .strip()
        )
        if not cleaned:
            continue
        try:
            num = float(cleaned)
        except ValueError:
            continue
        if "(" in m and ")" in m:
            num = -num
        values.append(num)

    return values


def extract_semantic_block_value(lines, anchor_phrases, window=4):
    candidates = []

    for i, line in enumerate(lines):
        if any(anchor in line.lower() for anchor in anchor_phrases):
            for blk in lines[i:i + window + 1]:
                candidates.extend(extract_numbers_from_line(blk))

    candidates = [v for v in candidates if abs(v) >= 1000]
    return candidates[0] if candidates else 0


def detect_financial_year(pdf):
    patterns = [
        r"year ended\s+march\s+31[,]?\s*(\d{4})",
        r"for the year ended\s+march\s+31[,]?\s*(\d{4})",
        r"for the year ended\s+31\s+march[,]?\s*(\d{4})",
        r"as at\s+march\s+31[,]?\s*(\d{4})",
        r"as at\s+31\s+march[,]?\s*(\d{4})",
    ]

    for page in pdf.pages[:8]:
        text = (page.extract_text() or "").lower().replace("\n", " ")
        for p in patterns:
            match = re.search(p, text)
            if match:
                return f"FY{match.group(1)}"

    return "FY_UNKNOWN"

def run_financial_analysis(pdf_path):
    metrics = {}
    diagnostics = {
        "pages_scanned": set(),
        "statements_detected": {},
        "warnings": [],
    }

    with pdfplumber.open(pdf_path) as pdf:
        detected_year = detect_financial_year(pdf)

        start_page = 0
        found_fin_section = False

        for i, page in enumerate(pdf.pages[:200]):  
            text = (page.extract_text() or "").lower()

           
            

            if any(a in text for a in FIN_SECTION_ANCHORS):
                start_page = i
                found_fin_section = True
                break

        if not found_fin_section:
            diagnostics["warnings"].append(
                "Financial statements section not found (using full scan)"
            )
            start_page = 0

        inside_financials = False
        current_statement = None
        fin_pages = {"Balance Sheet": [], "Profit & Loss": []}
        pages_processed = 0

        for i in range(start_page, len(pdf.pages)):

            if not inside_financials and (i - start_page) > MAX_PREFLIGHT_PAGES:
                break

            page = pdf.pages[i]
            raw_text = page.extract_text()
            if not is_text_page(raw_text):
                continue

            diagnostics["pages_scanned"].add(i + 1)
            text = raw_text.lower()

            if inside_financials and any(h in text for h in STOP_HEADERS):
                break

            lines = [l.strip().lower() for l in raw_text.split("\n") if l.strip()]

            if not inside_financials:
                for line in lines:
                    if contains_any(line, STATEMENT_HEADERS["balance_sheet"]):
                        inside_financials = True
                        current_statement = "Balance Sheet"
                        break
                    if contains_any(line, STATEMENT_HEADERS["profit_loss"]):
                        inside_financials = True
                        current_statement = "Profit & Loss"
                        break

            if not inside_financials or not current_statement:
                continue

            fin_pages[current_statement].append(i)
            pages_processed += 1

            if pages_processed >= MAX_FIN_PAGES:
                break

        diagnostics["statements_detected"] = fin_pages

        def collect_lines(pages):
            out = []
            for p in pages:
                txt = pdf.pages[p].extract_text() or ""
                out.extend([l.strip() for l in txt.split("\n") if l.strip()])
            return out

        pl_pages = fin_pages["Profit & Loss"]
        pl_lines = collect_lines(pl_pages)

        for metric, keys in PL_LABELS.items():
            for line in pl_lines:
                if metric in metrics:
                    break
                if any(k in line.lower() for k in keys):
                    nums = extract_numbers_from_line(line)
                    nums = [v for v in nums if abs(v) >= 1000]
                    if nums:
                        metrics[metric] = {
                            "value": max(nums),
                            "statement": "Profit & Loss",
                            "method": "text-line",
                        }

        metrics["Net Profit"] = {
            "value": extract_semantic_block_value(pl_lines, NET_PROFIT_ANCHORS),
            "statement": "Profit & Loss",
            "method": "semantic-block",
        }

        bs_pages = fin_pages["Balance Sheet"]
        bs_lines = collect_lines(bs_pages)

        for metric, anchors in BS_ANCHORS.items():
            metrics[metric] = {
                "value": extract_semantic_block_value(bs_lines, anchors),
                "statement": "Balance Sheet",
                "method": "semantic-block",
            }

    def v(k): return metrics.get(k, {}).get("value", 0)

    ta = v("Total Assets")
    nw = v("Net Worth")
    ca = v("Current Assets")
    cl = v("Current Liabilities")

    if nw > ta and ta > 0:
        diagnostics["warnings"].append("Net Worth > Total Assets — reset")
        metrics["Net Worth"]["value"] = 0

    if ca > ta and ta > 0:
        diagnostics["warnings"].append("Current Assets > Total Assets — reset")
        metrics["Current Assets"]["value"] = 0

    if metrics.get("Net Profit", {}).get("value", 0) == v("PBT"):
        diagnostics["warnings"].append("Net Profit equals PBT — reset")
        metrics["Net Profit"]["value"] = 0

    metrics.setdefault("Total Debt", {"value": 0})
    metrics.setdefault("Principal Repayment", {"value": 0})

    metrics["EBIT"] = {"value": v("PBT") + v("Interest Expense")}
    metrics["EBITDA"] = {"value": metrics["EBIT"]["value"] + v("Depreciation")}

    capital_employed = ta - cl

    ratios = {
        "Current Ratio": ca / cl if cl else None,
        "ROCE": v("EBIT") / capital_employed if capital_employed > 0.2 * ta else None,
        "ROA": v("Net Profit") / ta if ta else None,
    }

    if not fin_pages["Balance Sheet"] and not fin_pages["Profit & Loss"]:
        diagnostics["warnings"].append(
            "No consolidated financial statements detected"
        )

    return {
        "year": detected_year,
        "metrics": metrics,
        "ratios": ratios,
        "diagnostics": diagnostics,
    }
