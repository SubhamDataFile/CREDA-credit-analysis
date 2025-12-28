import pdfplumber
import re



PL_LABELS = {
    "Revenue": ["revenue from operations", "total income"],
    "PBT": ["profit before tax"],
    "Interest Expense": ["finance cost"],
    "Depreciation": ["depreciation and amortization"],
}

NET_PROFIT_ANCHORS = [
    "profit after tax",
    "profit for the year",
    "total comprehensive income",
    "attributable to owners",
]

BS_ANCHORS = {
    "Net Worth": [
        "total equity",
        "equity attributable to owners",
        "total equity attributable",
    ],
    "Total Assets": ["total assets"],
    "Current Assets": ["total current assets"],
    "Current Liabilities": ["total current liabilities"],
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
        text = "-" + text[1:-1]
    try:
        return float(text)
    except:
        return None


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
            blocks.setdefault(current, [])

        elif any(h in text for h in STATEMENT_HEADERS["profit_loss"]):
            current = "Profit & Loss"
            blocks.setdefault(current, [])

        if current:
            if any(stop in text for stop in STOP_HEADERS):
                current = None
            else:
                blocks[current].append(p["page"])

    return blocks



def extract_semantic_block_value(lines, anchor_phrases, window=4):
    candidates = []

    for i, line in enumerate(lines):
        l = line.lower()
        if any(anchor in l for anchor in anchor_phrases):
            start = max(0, i - window)
            end = min(len(lines), i + window + 1)
            for blk in lines[start:end]:
                candidates.extend(extract_numbers_from_line(blk))

    candidates = [v for v in candidates if abs(v) >= 1000]
    return max(candidates) if candidates else 0


def extract_metrics_from_text(pdf, pages, label_map, statement, diagnostics):
    results = {}

    for p in pages:
        text = pdf.pages[p].extract_text() or ""
        diagnostics["pages_scanned"].add(p + 1)
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        for i, line in enumerate(lines):
            line_l = line.lower()
            for metric, keys in label_map.items():
                if metric in results:
                    continue
                if any(k in line_l for k in keys):
                    nums = extract_numbers_from_line(" ".join(lines[i:i + 3]))
                    nums = [v for v in nums if abs(v) >= 1000]
                    if not nums:
                        continue

                    results[metric] = {
                        "value": max(nums),
                        "statement": statement,
                        "page": p + 1,
                        "method": "text-line",
                        "confidence": 0.9,
                        "warnings": [],
                    }
                    diagnostics["metrics_extracted"][metric] = results[metric]

    return results



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
        pl_pages = blocks.get("Profit & Loss", [])

        diagnostics["statements_detected"] = {
            "Balance Sheet": bs_pages,
            "Profit & Loss": pl_pages,
        }

        metrics.update(
            extract_metrics_from_text(
                pdf, pl_pages, PL_LABELS, "Profit & Loss", diagnostics
            )
        )


        def collect_lines(pages):
            lines = []
            for p in pages:
                text = pdf.pages[p].extract_text() or ""
                lines.extend([l.strip() for l in text.split("\n") if l.strip()])
            return lines

        pl_lines = collect_lines(pl_pages)
        bs_lines = collect_lines(bs_pages)

        net_profit = extract_semantic_block_value(pl_lines, NET_PROFIT_ANCHORS)
        if net_profit == 0:
            diagnostics["warnings"].append("Net Profit not found via semantic blocks")
        metrics["Net Profit"] = {
            "value": net_profit,
            "statement": "Profit & Loss",
            "method": "semantic_block",
            "confidence": 0.95,
            "warnings": [],
        }

        for metric, anchors in BS_ANCHORS.items():
            value = extract_semantic_block_value(bs_lines, anchors)
            if value == 0:
                diagnostics["warnings"].append(f"{metric} not found via semantic blocks")
            metrics[metric] = {
                "value": value,
                "statement": "Balance Sheet",
                "method": "semantic_block",
                "confidence": 0.95,
                "warnings": [],
            }

 

    def v(k): return metrics.get(k, {}).get("value", 0.0)

    metrics.setdefault("Total Debt", {"value": 0.0})
    metrics.setdefault("Principal Repayment", {"value": 0.0})

    metrics["EBIT"] = {"value": v("PBT") + v("Interest Expense")}
    metrics["EBITDA"] = {"value": metrics["EBIT"]["value"] + v("Depreciation")}

    ca, cl = v("Current Assets"), v("Current Liabilities")
    nw, td = v("Net Worth"), v("Total Debt")
    ta = v("Total Assets") or (nw + td)

    ratios = {
        "Current Ratio": ca / cl if cl else None,
        "ROCE": v("EBIT") / (nw + td) if (nw + td) else None,
        "ROA": v("Net Profit") / ta if ta else None,
    }

    return {"metrics": metrics, "ratios": ratios, "diagnostics": diagnostics}
