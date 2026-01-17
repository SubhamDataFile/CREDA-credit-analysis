def generate_trend_commentary(trend_flags):
    if not trend_flags:
        return (
            "The company has demonstrated stable operating and financial "
            "performance over the review period."
        )

    return (
        "Multi-year trend analysis indicates the following: "
        + "; ".join(trend_flags)
        + "."
    )
