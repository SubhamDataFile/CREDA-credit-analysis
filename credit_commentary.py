def generate_credit_commentary(risk_output, ratios, financials):
    """
    Generate structured, explainable credit commentary
    based on deterministic risk signals.
    """

    

    dscr = ratios.get("DSCR")
    current_ratio = ratios.get("Current-Ratio", 0)
    debt_equity = ratios.get("Debt-Equity Ratio", 0)
    roce = ratios.get("ROCE", 0)

    signals = {
        "strong_dscr": dscr is not None and dscr >= 1.25,
        "excellent_dscr": dscr is not None and dscr >= 2.0,

        "healthy_liquidity": current_ratio >= 1.5,

        "low_leverage": debt_equity <= 1.0,
        "high_leverage": debt_equity > 2.0,

        "strong_profitability": roce >= 0.15,
        "weak_profitability": roce < 0.08,

        "fatal_flags": risk_output.get("fatal_flags", 0) > 0,
        "overall_risk": risk_output.get("overall_risk", "MODERATE")
    }


    strengths = []

    if signals["excellent_dscr"]:
        strengths.append(
            f"Exceptional debt servicing capacity with DSCR of {dscr:.2f}×."
        )
    elif signals["strong_dscr"]:
        strengths.append(
            f"Comfortable debt servicing ability supported by DSCR of {dscr:.2f}×."
        )

    if signals["healthy_liquidity"]:
        strengths.append(
            f"Healthy liquidity position with a current ratio of {current_ratio:.2f}×."
        )

    if signals["low_leverage"]:
        strengths.append(
            "Low leverage profile, providing balance sheet flexibility."
        )

    if signals["strong_profitability"]:
        strengths.append(
            f"Strong operating efficiency with ROCE of {roce * 100:.1f}%."
        )


    weaknesses = []

    if signals["weak_profitability"]:
        weaknesses.append(
            f"Profitability remains modest with ROCE of {roce * 100:.1f}%."
        )

    if signals["high_leverage"]:
        weaknesses.append(
            "Elevated leverage may constrain future borrowing capacity."
        )

    if not weaknesses:
        weaknesses.append("No material credit weaknesses observed.")

   

    overall_risk = signals["overall_risk"]

    summary = (
        f"The borrower is assessed as {overall_risk.lower()} credit risk. "
        "The assessment is based on the company’s cash flow strength, "
        "liquidity position, and capital structure."
    )

   

    if overall_risk == "LOW":
        conclusion = (
            "The company appears suitable for bank financing, "
            "subject to standard terms and covenants."
        )
    elif overall_risk == "MODERATE":
        conclusion = (
            "The company may be considered for financing with "
            "appropriate risk mitigants and monitoring."
        )
    else:
        conclusion = (
            "The company exhibits elevated credit risk and may not "
            "be suitable for incremental borrowing at this stage."
        )

    

    return {
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "conclusion": conclusion
    }
