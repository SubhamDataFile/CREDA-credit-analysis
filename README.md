# CREDA – AI-Powered Credit Analysis System

CREDA is a bank-style credit analysis application built using Streamlit.

## Key Features
- PDF annual report ingestion
- Financial extraction with analyst overrides
- Canonical ratio engine (DSCR, ROCE, ROA, etc.)
- Rule-based credit risk engine (traffic-light model)
- Optional AI-assisted commentary (language only)
- One-page downloadable credit memo (PDF)

## Design Philosophy
- Conservative by default (no silent assumptions)
- Analyst-first workflow
- AI as an assistant, not a decision-maker
- Cloud-native and auditable

## Tech Stack
- Python, Streamlit
- pdfplumber
- ReportLab
- OpenAI (optional)

## Demo Flow
1. Upload annual report PDF
2. Review extracted values
3. Adjust key financials if required
4. Review ratios, risk, and commentary
5. Download credit memo

