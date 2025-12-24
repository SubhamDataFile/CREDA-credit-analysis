from pipeline import run_financial_analysis
from risk_engine import evaluate_credit_risk
from credit_commentary import generate_credit_commentary
from credit_memo import generate_credit_memo
from ai_commentary import polish_credit_commentary

import pandas as pd
import streamlit as st
import math
import os


# =========================
# Config
# =========================
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
    "Principal Repayment"
]

st.set_page_config(page_title="CREDA – AI Credit Analysis", layout="centered")
st.title("📊 CREDA – AI-Powered Credit Analysis")
st.caption("Rule-based credit engine with optional AI-assisted commentary")


# =========================
# Session State
# =========================
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

if "extracted" not in st.session_state:
    st.session_state.extracted = {}

if "adjusted_financials" not in st.session_state:
    st.session_state.adjusted_financials = {}


# =========================
# Helpers
# =========================
def safe_number(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return 0
    return x


def recompute_ratios(f):
    ca = f.get("Current Assets", 0)
    cl = f.get("Current Liabilities", 0)
    nw = f.get("Net Worth", 0)
    td = f.get("Total Debt", 0)
    ta = f.get("Total Assets", nw + td)

    revenue = f.get("Revenue", 0)
    net_profit = f.get("Net Profit", 0)
    ebitda = f.get("EBITDA", 0)
    depreciation = f.get("Depreciation", 0)
    pbt = f.get("PBT", 0)
    interest = f.get("Interest Expense", 0)
    principal = f.get("Principal Repayment", 0)

    ebit = ebitda - depreciation
    capital_employed = nw + td

    earnings_for_debt_service = pbt + depreciation + interest
    debt_service = interest + principal

    return {
        "DSCR": earnings_for_debt_service / debt_service if debt_service > 0 else None,
        "ROCE": ebit / capital_employed if capital_employed > 0 else None,
        "ROA": net_profit / ta if ta > 0 else None,
        "Current Ratio": ca / cl if cl > 0 else None,
        "Debt-Equity Ratio": td / nw if nw > 0 else None,
        "Interest Coverage Ratio": ebit / interest if interest > 0 else None,
    }


# =========================
# File Uploads
# =========================
uploaded_file = st.file_uploader("Upload Annual Report (PDF)", type=["pdf"])
logo_path = None

if uploaded_file:
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", uploaded_file.name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success("Annual report uploaded")

    st.markdown("### 🏢 Company Logo (Optional)")
    logo_file = st.file_uploader(
        "Upload Company Logo (PNG / JPG)",
        type=["png", "jpg", "jpeg"]
    )

    if logo_file:
        logo_path = os.path.join("uploads", "company_logo.png")
        with open(logo_path, "wb") as f:
            f.write(logo_file.getbuffer())
        st.success("Company logo uploaded")

    if st.button("Run Credit Analysis"):
        with st.spinner("Extracting financials..."):
            financial_data, ratios, risk_flags = run_financial_analysis(file_path)

        st.session_state.extracted = financial_data
        st.session_state.analysis_done = True
        st.success("Analysis completed")


# =========================
# Main Analysis Section
# =========================
if st.session_state.analysis_done:
    extracted = st.session_state.extracted
    financials = extracted.copy()

    for field in OVERRIDABLE_FIELDS:
        financials.setdefault(field, 0)

    # -------- Analyst Overrides --------
    st.markdown("## ✍️ Analyst Adjustments")
    st.caption("Overrides trigger live recomputation")

    with st.expander("Edit Financial Inputs"):
        for field in OVERRIDABLE_FIELDS:
            if field not in st.session_state.adjusted_financials:
                st.session_state.adjusted_financials[field] = float(financials.get(field, 0))

            st.session_state.adjusted_financials[field] = st.number_input(
                field,
                value=st.session_state.adjusted_financials[field],
                step=1.0,
                format="%.2f",
                key=f"override_{field}"
            )

    financials.update(st.session_state.adjusted_financials)
    ratios = recompute_ratios(financials)

    # -------- Risk Engine --------
    balance_sheet_context = {
        "total_debt": financials.get("Total Debt", 0),
        "interest_expense": financials.get("Interest Expense", 0)
    }

    risk_output = evaluate_credit_risk(
        ratios=ratios,
        balance_sheet=balance_sheet_context
    )

    # -------- Commentary --------
    st.markdown("## 🧠 Credit Commentary")
    use_ai = st.toggle(
        "Enhance commentary using AI (language only)",
        value=False
    )

    commentary = generate_credit_commentary(
        risk_output=risk_output,
        ratios=ratios,
        financials=financials
    )

    if use_ai:
        try:
            commentary = polish_credit_commentary(commentary)
            commentary["ai_enhanced"] = True
            st.caption("✳ Commentary language enhanced using AI.")
        except Exception:
            commentary["ai_enhanced"] = False
            st.warning("AI enhancement failed. Showing rule-based commentary.")

    # -------- Credit Memo --------
    pdf_path = generate_credit_memo(
        financials=financials,
        ratios=ratios,
        risk_output=risk_output,
        commentary=commentary,
        company_name=uploaded_file.name.replace(".pdf", ""),
        period="FY",
        logo_path=logo_path,
        output_path="credit_memo.pdf"
    )

    # -------- Snapshot --------
    st.markdown("## 📊 Credit Snapshot")
    c1, c2, c3 = st.columns(3)
    c1.metric("Revenue", f"₹ {safe_number(financials['Revenue']):,.0f}")
    c2.metric("Net Profit", f"₹ {safe_number(financials['Net Profit']):,.0f}")
    c3.metric("EBITDA", f"₹ {safe_number(financials['EBITDA']):,.0f}")

    st.markdown("### 📈 Key Ratios")
    r1, r2, r3 = st.columns(3)
    r1.metric("DSCR", "NA" if ratios["DSCR"] is None else f"{ratios['DSCR']:.2f}")
    r2.metric("ROCE", "NA" if ratios["ROCE"] is None else f"{ratios['ROCE']*100:.1f}%")
    r3.metric("ROA", "NA" if ratios["ROA"] is None else f"{ratios['ROA']*100:.1f}%")

    # -------- Risk Table --------
    st.markdown("## 🚦 Credit Risk Assessment")
    icon = {"LOW": "🟢", "MODERATE": "🟠", "HIGH": "🔴"}
    st.markdown(f"### {icon[risk_output['overall_risk']]} {risk_output['overall_risk']} RISK")

    risk_df = pd.DataFrame(risk_output["ratio_flags"])
    risk_df["value"] = risk_df["value"].apply(lambda x: "NA" if x is None else round(x, 3))
    st.dataframe(risk_df, use_container_width=True)

    # -------- Download --------
    with open(pdf_path, "rb") as f:
        st.download_button(
            "📥 Download Credit Memo (PDF)",
            data=f,
            file_name="Credit_Memo.pdf",
            mime="application/pdf"
        )

    # -------- Audit Trail --------
    st.markdown("### 🧾 Audit Trail")
    audit_df = pd.DataFrame({
        "Metric": OVERRIDABLE_FIELDS,
        "Extracted": [extracted.get(k, 0) for k in OVERRIDABLE_FIELDS],
        "Adjusted": [financials.get(k, 0) for k in OVERRIDABLE_FIELDS],
    })
    st.dataframe(audit_df, use_container_width=True)

    if st.button("Reset Analysis"):
        st.session_state.analysis_done = False
        st.session_state.adjusted_financials = {}
        st.experimental_rerun()
