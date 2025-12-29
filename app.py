from pipeline import run_financial_analysis
from risk_engine import evaluate_credit_risk
from credit_commentary import generate_credit_commentary
from credit_memo import generate_credit_memo
from ai_commentary import polish_credit_commentary

import pandas as pd
import streamlit as st
import math
import os


st.set_page_config(page_title="CREDA – AI Credit Analysis", layout="centered")

st.title("CREDA – AI-Powered Credit Analysis")
st.caption("Rule-based credit engine with optional AI-assisted commentary")

st.info(
    "Workflow: Upload annual report → Review extracted figures → "
    "Adjust key financials if needed → Ratios, risk, and credit memo update live."
)

st.caption(
    "AI improves language only. All credit logic, ratios, and conclusions remain rule-based."
)


OVERRIDABLE_FIELDS = [
    "Revenue",
    "Net Profit",
    "EBITDA",
    "Depreciation",
    "PBT",
    "Current Assets",
    "Current Liabilities",
    "Total Assets",
    "Net Worth",
    "Total Debt",
    "Interest Expense",
    "Principal Repayment",
]


if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

if "metrics_raw" not in st.session_state:
    st.session_state.metrics_raw = {}

if "diagnostics" not in st.session_state:
    st.session_state.diagnostics = {}

if "adjusted_financials" not in st.session_state:
    st.session_state.adjusted_financials = {}


def safe_number(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return 0.0
    return float(x)


def get_effective_value(financials, key, fallback_fn):
    """
    Priority:
    1. Manual override (if > 0)
    2. Accounting fallback
    """
    val = financials.get(key, 0)
    if val and val > 0:
        return val
    return fallback_fn()


def recompute_ratios(financials):
    ca = financials.get("Current Assets", 0)
    cl = financials.get("Current Liabilities", 0)
    nw = financials.get("Net Worth", 0)
    td = financials.get("Total Debt", 0)
    ta = financials.get("Total Assets", nw + td)

    net_profit = financials.get("Net Profit", 0)
    ebitda = financials.get("EBITDA", 0)
    interest = financials.get("Interest Expense", 0)
    principal = financials.get("Principal Repayment", 0)

    debt_service = interest + principal

    return {
        "DSCR": ebitda / debt_service if debt_service > 0 else None,
        "ROA": net_profit / ta if ta > 0 else None,
        "Current Ratio": ca / cl if cl > 0 else None,
        "Debt-Equity Ratio": td / nw if nw > 0 else None,
    }


uploaded_file = st.file_uploader("Upload Annual Report (PDF)", type=["pdf"])
logo_path = None

if uploaded_file:
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", uploaded_file.name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success("Annual report uploaded")

    st.markdown("### Company Logo (Optional)")
    logo_file = st.file_uploader("Upload Company Logo", type=["png", "jpg", "jpeg"])

    if logo_file:
        logo_path = os.path.join("uploads", "company_logo.png")
        with open(logo_path, "wb") as f:
            f.write(logo_file.getbuffer())
        st.success("Company logo uploaded")

    if st.button("Run Credit Analysis"):
        with st.spinner("Extracting financials..."):
            result = run_financial_analysis(file_path)

        st.session_state.metrics_raw = result["metrics"]
        st.session_state.diagnostics = result["diagnostics"]
        st.session_state.analysis_done = True
        st.session_state.adjusted_financials = {}
        st.success("Analysis completed")


if st.session_state.analysis_done:
    metrics_raw = st.session_state.metrics_raw

    financials = {
        k: safe_number(v.get("value"))
        for k, v in metrics_raw.items()
    }

    for field in OVERRIDABLE_FIELDS:
        financials.setdefault(field, 0.0)

    financials["EBIT"] = financials.get("PBT", 0) + financials.get("Interest Expense", 0)
    financials["Capital Employed"] = financials.get("Net Worth", 0) + financials.get("Total Assets", 0) - financials.get("Current Liabilities",0)
    st.markdown("## Analyst Adjustments")
    st.caption("Overrides trigger live recomputation")

    with st.expander("Edit Financial Inputs"):
        for field in OVERRIDABLE_FIELDS:
            st.session_state.adjusted_financials.setdefault(
                field, float(financials.get(field, 0.0))
            )

            st.session_state.adjusted_financials[field] = st.number_input(
                field,
                value=st.session_state.adjusted_financials[field],
                step=1.0,
                format="%.2f",
            )

    financials.update(st.session_state.adjusted_financials)

    ratios = recompute_ratios(financials)

    effective_ebit = get_effective_value(
        financials,
        "EBIT",
        fallback_fn=lambda: financials.get("PBT", 0) + financials.get("Interest Expense", 0),
    )

    effective_capital_employed = get_effective_value(
        financials,
        "Capital Employed",
        fallback_fn=lambda: financials.get("Net Worth", 0) + financials.get("Total Debt", 0),
    )

    ratios["ROCE"] = (
        effective_ebit / effective_capital_employed
        if effective_capital_employed > 0
        else None
    )

    risk_output = evaluate_credit_risk(
        ratios=ratios,
        balance_sheet={
            "total_debt": financials.get("Total Debt", 0),
            "interest_expense": financials.get("Interest Expense", 0),
        },
    )

    st.markdown("## Credit Commentary")

    use_ai = st.toggle("Enhance commentary using AI (language only)", value=False)

    commentary = generate_credit_commentary(
        risk_output=risk_output,
        ratios=ratios,
        financials=financials,
    )

    if use_ai:
        commentary = polish_credit_commentary(commentary)
        st.caption("✳ AI enhanced language only. Credit logic unchanged.")

  
    st.markdown("## Credit Snapshot")
    c1, c2, c3 = st.columns(3)
    c1.metric("Revenue", f"₹ {financials['Revenue']:,.0f}")
    c2.metric("Net Profit", f"₹ {financials['Net Profit']:,.0f}")
    c3.metric("EBITDA", f"₹ {financials['EBITDA']:,.0f}")

    st.markdown("### Key Ratios")
    r1, r2, r3 = st.columns(3)
    r1.metric("DSCR", "NA" if ratios["DSCR"] is None else f"{ratios['DSCR']:.2f}")
    r2.metric("ROCE", "NA" if ratios["ROCE"] is None else f"{ratios['ROCE']*100:.1f}%")
    r3.metric("ROA", "NA" if ratios["ROA"] is None else f"{ratios['ROA']*100:.1f}%")

   
    st.markdown("## Credit Risk Assessment")

    icon = {"LOW": "🟢", "MODERATE": "🟠", "HIGH": "🔴"}
    st.markdown(
      f"### {icon.get(risk_output['overall_risk'], '⚪')} "
      f"{risk_output['overall_risk']} RISK"
   )

    if "ratio_flags" in risk_output and risk_output["ratio_flags"]:
      risk_df = pd.DataFrame(risk_output["ratio_flags"])

    
      if "value" in risk_df.columns:
          risk_df["value"] = risk_df["value"].apply(
            lambda x: "NA" if x is None else round(x, 3)
        )

      st.dataframe(risk_df, use_container_width=True)
    else:
      st.info("No ratio-level risk flags triggered.")


  
    st.markdown("### Audit Trail")
    audit_df = pd.DataFrame(
        {
            "Metric": OVERRIDABLE_FIELDS,
            "Extracted": [metrics_raw.get(k, {}).get("value", 0) for k in OVERRIDABLE_FIELDS],
            "Adjusted": [financials.get(k, 0) for k in OVERRIDABLE_FIELDS],
        }
    )
    st.dataframe(audit_df, use_container_width=True)

   
    if st.button("Reset Analysis"):
        st.session_state.clear()
        st.experimental_rerun()
