import pdfplumber
import re



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


def find_statement_pages(pages, headers):
    return [p["page"] for p in pages if any(h in p["text"] for h in headers)]



def extract_text_values(pdf, pages, label_map, statement_name, diagnostics):
    """
    Phase 1 extraction:
    - Statement locked
    - Provenance aware
    - Confidence + warnings
    """
    results = {}

    for p in pages:
        text = pdf.pages[p].extract_text()
        if not text:
            continue

        diagnostics["pages_scanned"].add(p + 1)

        for line in text.split("\n"):
            line_l = line.lower()

            for metric, keys in label_map.items():
                if metric in results:
                    continue

                if any(k in line_l for k in keys):
                    warnings = []
                    confidence = 0.8  # base confidence

                    # Unit contamination detection
                    if "nos" in line_l or "units" in line_l:
                        warnings.append("Unit-based row (Nos/Units)")
                        confidence -= 0.3

                    numbers = re.findall(r"\(?\d[\d,]*\)?", line)
                    if not numbers:
                        warnings.append("Label matched but no numeric value found")
                        confidence = 0.0
                        continue

                    value = parse_number(numbers[-1])  # rightmost = latest year
                    if value is None:
                        warnings.append("Numeric parsing failed")
                        confidence = 0.0
                        continue

                    results[metric] = {
                        "value": value,
                        "statement": statement_name,
                        "page": p + 1,
                        "method": "regex-row",
                        "confidence": round(max(confidence, 0.0), 2),
                        "warnings": warnings,
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

        bs_pages = find_statement_pages(
            pages, STATEMENT_HEADERS["balance_sheet"]
        )
        pl_pages = find_statement_pages(
            pages, STATEMENT_HEADERS["profit_loss"]
        )

        diagnostics["statements_detected"]["Balance Sheet"] = {
            "detected": bool(bs_pages),
            "pages": [p + 1 for p in bs_pages],
        }

        diagnostics["statements_detected"]["Profit & Loss"] = {
            "detected": bool(pl_pages),
            "pages": [p + 1 for p in pl_pages],
        }

        metrics.update(
            extract_text_values(
                pdf, bs_pages, BS_LABELS, "Balance Sheet", diagnostics
            )
        )

        metrics.update(
            extract_text_values(
                pdf, pl_pages, PL_LABELS, "Profit & Loss", diagnostics
            )
        )

    

    for k in ["Total Debt", "Principal Repayment"]:
        if k not in metrics:
            metrics[k] = {
                "value": 0.0,
                "statement": "Manual / Assumed",
                "confidence": 0.5,
                "warnings": ["Defaulted to zero"],
            }


    def v(key):
        return metrics.get(key, {}).get("value", 0.0)

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

    np = v("Net Profit")
    ebit, ebitda = v("EBIT"), v("EBITDA")
    interest, principal = v("Interest Expense"), v("Principal Repayment")

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

    return {
        "metrics": metrics,
        "ratios": ratios,
        "diagnostics": diagnostics,
    }
