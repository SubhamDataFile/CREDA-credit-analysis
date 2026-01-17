from risk_thresholds import RISK_THRESHOLDS
def classify_ratio(value, cfg):
    if value is None:
        return "AMBER"

    if cfg["direction"] == "higher_better":
        if value >= cfg["green"]:
            return "GREEN"
        elif value >= cfg["amber"]:
            return "AMBER"
        else:
            return "RED"

    if cfg["direction"] == "lower_better":
        if value <= cfg["green"]:
            return "GREEN"
        elif value <= cfg["amber"]:
            return "AMBER"
        else:
            return "RED"
        
def score_ratio(status, weight):
    if status == "GREEN":
        return weight
    if status == "RED":
        return -weight
    return 0

def check_fatal_flag(value, cfg):
    if value is None:
        return False

    fatal_threshold = cfg.get("fatal_below")
    if fatal_threshold is not None:
        return value < fatal_threshold

    return False

def apply_debt_light_logic(ratios, balance_sheet):
    total_debt = balance_sheet.get("total_debt", 0)
    interest = balance_sheet.get("interest_expense", 0)

    if total_debt <= 0 or interest <= 0:
        ratios = ratios.copy()
        ratios["dscr"] = None
        ratios["interest_coverage"] = None

    return ratios


def evaluate_credit_risk(ratios, balance_sheet):
    
    ratios = apply_debt_light_logic(ratios, balance_sheet)

    ratio_results = []
    total_score = 0
    red_flags = 0
    fatal_flags = 0

    for ratio_name, cfg in RISK_THRESHOLDS.items():
        value = ratios.get(ratio_name)

        status = classify_ratio(value, cfg)
        score = score_ratio(status, cfg["weight"])
        fatal = check_fatal_flag(value, cfg)

        if status == "RED":
            red_flags += 1
        if fatal:
            fatal_flags += 1

        total_score += score

        ratio_results.append({
            "ratio": ratio_name,
            "value": value,
            "status": status,
            "score": score,
            "fatal": fatal
        })

    if fatal_flags >= 1:
        overall_risk = "HIGH"
    elif red_flags >= 2 or total_score <= -5:
        overall_risk = "HIGH"
    elif red_flags == 1 or total_score < 0:
        overall_risk = "MODERATE"
    else:
        overall_risk = "LOW"

    return {
        "ratio_flags": ratio_results,
        "total_score": total_score,
        "red_flags": red_flags,
        "fatal_flags": fatal_flags,
        "overall_risk": overall_risk
    }
