def evaluate_trend_flags(trends):
    flags = []

    rev_trends = list(trends["Revenue"].values())
    ebitda_trends = list(trends["EBITDA"].values())

    if any(t is not None and t < -0.10 for t in rev_trends):
        flags.append("Revenue declined by more than 10% YoY")

    if len(ebitda_trends) >= 1:
        for i, t in enumerate(ebitda_trends):
            if t is not None and t < 0 and rev_trends[i] is not None and rev_trends[i] > 0:
                flags.append("Margin compression observed")

    roce_trends = list(trends["ROCE"].values())
    if any(t is not None and t < -0.03 for t in roce_trends):
        flags.append("Capital efficiency deterioration")

    debt_trends = list(trends["Total Debt"].values())
    if any(t is not None and t > 0.15 for t in debt_trends):
        flags.append("Aggressive debt growth")

    return flags
