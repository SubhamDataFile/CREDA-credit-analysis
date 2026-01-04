from trend_engine.trend_metrics import compute_yoy_series

def build_trend_block(financials_by_year, ratios_by_year):
    trends = {}

    for metric in ["Revenue", "EBITDA", "Net Profit", "Total Debt"]:
        series = {
            fy: financials_by_year[fy].get(metric)
            for fy in financials_by_year
        }
        trends[metric] = compute_yoy_series(series)

    for ratio in ["ROCE", "ROA", "DSCR", "Interest Coverage"]:
        series = {
            fy: ratios_by_year[fy].get(ratio)
            for fy in ratios_by_year
        }
        trends[ratio] = compute_yoy_series(series)

    return trends
