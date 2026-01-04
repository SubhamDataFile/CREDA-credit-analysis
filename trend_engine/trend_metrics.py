def compute_yoy_series(series: dict):
    """
    series: {FY: numeric_value}
    returns: {FY: yoy_pct_change}
    """
    years = sorted(series.keys())
    yoy = {}

    for i in range(1, len(years)):
        prev, curr = years[i-1], years[i]
        prev_val = series[prev]
        curr_val = series[curr]

        if prev_val in (None, 0) or curr_val is None:
            yoy[curr] = None
        else:
            yoy[curr] = round((curr_val - prev_val) / abs(prev_val), 4)

    return yoy
