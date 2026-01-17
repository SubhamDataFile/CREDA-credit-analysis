

RISK_THRESHOLDS = {
    "Current Ratio": {
        "green": 1.5,
        "amber": 1.0,
        "direction": "higher_better",
        "weight": 2
    },
    "DSCR": {
        "green": 1.25,
        "amber": 1.0,
        "direction": "higher_better",
        "weight": 5,
        "fatal_below": 1.0
    },
    "Interest Coverage Ratio": {
        "green": 3.0,
        "amber": 1.5,
        "direction": "higher_better",
        "weight": 5,
        "fatal_below": 1.0
    },
    "Debt-Equity Ratio": {
        "green": 1.0,
        "amber": 2.0,
        "direction": "lower_better",
        "weight": 3
    },
    "ROCE": {
        "green": 0.15,
        "amber": 0.08,
        "direction": "higher_better",
        "weight": 2
    },
    "ROA": {
        "green": 0.08,
        "amber": 0.03,
        "direction": "higher_better",
        "weight": 1
    }
}
