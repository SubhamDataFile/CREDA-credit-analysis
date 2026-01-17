def determine_outlook(trend_flags, latest_overall_risk):
    joined = " ".join(trend_flags)

    if "declined" in joined or "deterioration" in joined:
        return "Negative"

    if latest_overall_risk == "LOW" and not trend_flags:
        return "Positive"

    return "Stable"
