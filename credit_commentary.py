def generate_credit_commentary(risk_output, ratios, financials):
    

    dscr = ratios.get("DSCR")
    roce = ratios.get("ROCE")
    roa = ratios.get("ROA")
    current_ratio = ratios.get("Current Ratio")
    debt_equity = ratios.get("Debt-Equity Ratio")
    interest_coverage = ratios.get("Interest Coverage Ratio")

    total_debt = financials.get("Total Debt", 0)

    flags = {
        "strong_liquidity": current_ratio is not None and current_ratio >= 1.5,
        "adequate_liquidity": current_ratio is not None and 1.0 <= current_ratio < 1.5,

        "low_leverage": debt_equity is not None and debt_equity <= 1.0,
        "high_leverage": debt_equity is not None and debt_equity > 2.0,

        "strong_dscr": dscr is not None and dscr >= 1.25,
        "weak_dscr": dscr is not None and dscr < 1.0,

        "strong_profitability": (
            (roce is not None and roce >= 0.15) or
            (roa is not None and roa >= 0.08)
        ),

        "weak_profitability": (
            (roce is not None and roce < 0.10) or
            (roa is not None and roa < 0.04)
        ),

        "strong_coverage": interest_coverage is not None and interest_coverage >= 3.0,
        "weak_coverage": interest_coverage is not None and interest_coverage < 1.5,
    }

    if total_debt <= 0:
        flags["low_leverage"] = True
        flags["high_leverage"] = False
        flags["strong_dscr"] = False
        flags["weak_dscr"] = False
        flags["strong_coverage"] = False
        flags["weak_coverage"] = False

    strengths = []
    weaknesses = []

    if flags["strong_liquidity"]:
        strengths.append("The company demonstrates strong short-term liquidity.")
    elif flags["adequate_liquidity"]:
        strengths.append("Liquidity position is adequate but should be monitored.")

    if flags["low_leverage"]:
        strengths.append("Leverage profile is comfortable, indicating conservative capital structure.")

    if flags["strong_dscr"]:
        strengths.append("Debt service coverage is strong, providing adequate cushion for lenders.")

    if flags["strong_profitability"]:
        strengths.append("Profitability metrics reflect efficient use of capital and assets.")

    if flags["strong_coverage"]:
        strengths.append("Interest servicing ability is strong.")

    if flags["high_leverage"]:
        weaknesses.append("High leverage increases financial risk and reduces balance sheet flexibility.")

    if flags["weak_dscr"]:
        weaknesses.append("Debt service coverage is weak, increasing refinancing risk.")

    if flags["weak_profitability"]:
        weaknesses.append("Profitability metrics are weak, which may constrain internal accruals.")

    if flags["weak_coverage"]:
        weaknesses.append("Interest coverage is weak, indicating limited headroom for debt servicing.")

    overall_risk = risk_output.get("overall_risk", "MODERATE")

    summary = (
        f"The overall credit risk is assessed as {overall_risk.lower()}. "
        "This assessment considers liquidity, leverage, profitability, and debt servicing capacity."
    )

    lending_view = {
        "LOW": "The credit profile is strong and the company appears suitable for lending at normal terms.",
        "MODERATE": "The credit profile is moderate. Lending may be considered with appropriate safeguards.",
        "HIGH": "The credit profile is weak. Lending should be approached cautiously with strong risk mitigants."
    }.get(overall_risk, "")

    return {
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "lending_view": lending_view
    }
