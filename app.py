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
    "Workflow: Upload annual reports → Select financial year → "
    "Adjust financials → Ratios, risk, and credit memo update live."
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



if "analysis_by_year" not in st.session_state:
    st.session_state.analysis_by_year = {}

if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False


def safe_number(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return 0.0
    return float(x)


def get_effective_value(financials, key, fallback_fn):
    val = financials.get(key, 0)
    return val if val > 0 else fallback_fn()


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


uploaded_files = st.file_uploader(
    "Upload Annual Reports (Multiple Years)",
    type=["pdf"],
    accept_multiple_files=True,
)

manual_year = "Auto-detect"

if uploaded_files:
    st.markdown("### Financial Year (manual override if auto-detection fails)")
    manual_year = st.selectbox(
        "Select Financial Year",
        ["Auto-detect", "FY2025", "FY2024", "FY2023", "FY2022"],
    )

    st.markdown("### Company Logo (Optional)")
    logo_file = st.file_uploader("Upload Company Logo", type=["png", "jpg", "jpeg"])
    logo_path = None

    if logo_file:
        os.makedirs("uploads", exist_ok=True)
        logo_path = os.path.join("uploads", "company_logo.png")
        with open(logo_path, "wb") as f:
            f.write(logo_file.getbuffer())

    if st.button("Run Credit Analysis"):
        with st.spinner("Running analysis for all uploaded reports..."):
            for file in uploaded_files:
                os.makedirs("uploads", exist_ok=True)
                file_path = os.path.join("uploads", file.name)

                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())

                result = run_financial_analysis(file_path)

                year = result.get("year", "FY_UNKNOWN")
                if year == "FY_UNKNOWN" and manual_year != "Auto-detect":
                    year = manual_year

                financials = {
                    k: safe_number(v.get("value"))
                    for k, v in result["metrics"].items()
                }

                for field in OVERRIDABLE_FIELDS:
                    financials.setdefault(field, 0.0)

                financials["EBIT"] = (
                    financials.get("PBT", 0) + financials.get("Interest Expense", 0)
                )

                financials["Capital Employed"] = (
                    financials.get("Net Worth", 0) + financials.get("Total Debt", 0)
                )

                st.session_state.analysis_by_year[year] = {
                    "metrics_raw": result["metrics"],
                    "financials": financials,
                    "overrides": {},
                    "diagnostics": result["diagnostics"],
                }

        st.session_state.analysis_done = True
        st.success("Analysis completed for all years")


if st.session_state.analysis_done and st.session_state.analysis_by_year:

    selected_year = st.selectbox(
        "Select Financial Year",
        sorted(st.session_state.analysis_by_year.keys(), reverse=True),
    )

    current = st.session_state.analysis_by_year[selected_year]
    metrics_raw = current["metrics_raw"]
    financials = current["financials"]
    overrides = current["overrides"]

    st.markdown("## Analyst Adjustments")

    with st.expander("Edit Financial Inputs"):
        for field in OVERRIDABLE_FIELDS:
            overrides.setdefault(field, financials.get(field, 0.0))
            overrides[field] = st.number_input(
                field,
                value=float(overrides[field]),
                step=1.0,
                format="%.2f",
            )

    financials.update(overrides)

    ratios = recompute_ratios(financials)

    effective_ebit = get_effective_value(
        financials,
        "EBIT",
        lambda: financials.get("PBT", 0) + financials.get("Interest Expense", 0),
    )

    effective_capital_employed = get_effective_value(
        financials,
        "Capital Employed",
        lambda: financials.get("Total Assets", 0) - financials.get("Current Liabilities", 0),
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

    if risk_output.get("ratio_flags"):
      risk_df = pd.DataFrame(risk_output["ratio_flags"])

      if "value" in risk_df.columns:
        risk_df["value"] = risk_df["value"].apply(
            lambda x: "NA" if x is None else round(x, 3)
        )

      st.dataframe(risk_df, use_container_width=True)
    else:
      st.info("No risk flags generated for this analysis.")


    pdf_path = generate_credit_memo(
        financials=financials,
        ratios=ratios,
        risk_output=risk_output,
        commentary=generate_credit_commentary(
            risk_output=risk_output, ratios=ratios, financials=financials
        ),
        company_name=selected_year,
        period=selected_year,
        logo_path=logo_path,
        output_path=f"credit_memo_{selected_year}.pdf",
    )

    with open(pdf_path, "rb") as f:
        st.download_button(
            " Download Credit Memo (PDF)",
            data=f,
            file_name=f"Credit_Memo_{selected_year}.pdf",
            mime="application/pdf",
        )

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
