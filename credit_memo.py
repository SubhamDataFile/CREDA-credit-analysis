from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib import colors
import os
from datetime import datetime


def generate_credit_memo(
    financials,
    ratios,
    risk_output,
    commentary,
    company_name="Company",
    period="FY",
    logo_path=None,
    output_path="credit_memo.pdf"
):
   

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    story = []

    header_style = ParagraphStyle(
        "Header",
        fontSize=14,
        leading=18,
        spaceAfter=8,
        alignment=TA_LEFT,
        fontName="Helvetica-Bold"
    )

    normal_style = ParagraphStyle(
        "NormalText",
        fontSize=9,
        leading=13
    )

    bold_style = ParagraphStyle(
        "BoldText",
        fontSize=9,
        leading=13,
        fontName="Helvetica-Bold"
    )

    title_block = [
        Paragraph("CREDA – Credit Appraisal Memo", header_style),
        Paragraph(f"<b>Company:</b> {company_name}", normal_style),
        Paragraph(f"<b>Period:</b> {period}", normal_style),
        Paragraph(
            f"<b>Overall Credit Risk:</b> {risk_output.get('overall_risk', 'NA')}",
            bold_style
        )
    ]

    header_table_data = []
    if logo_path and os.path.exists(logo_path):
        logo = Image(logo_path, width=60, height=60)
        header_table_data.append([title_block, logo])
    else:
        header_table_data.append([title_block, ""])

    header_table = Table(header_table_data, colWidths=[400, 100])
    header_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12)
        ])
    )

    story.append(header_table)
    story.append(Spacer(1, 12))


    snapshot_data = [
        ["Revenue", "EBITDA", "Net Profit", "Net Worth"],
        [
            f"₹ {financials.get('Revenue', 0):,.0f}",
            f"₹ {financials.get('EBITDA', 0):,.0f}",
            f"₹ {financials.get('Net Profit', 0):,.0f}",
            f"₹ {financials.get('Net Worth', 0):,.0f}"
        ]
    ]

    snapshot_table = Table(snapshot_data, colWidths=[120] * 4)
    snapshot_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )

    story.append(Paragraph("Financial Snapshot", bold_style))
    story.append(snapshot_table)
    story.append(Spacer(1, 12))


    def fmt(x, pct=False):
        if x is None:
            return "NA"
        return f"{x*100:.1f}%" if pct else f"{x:.2f}"

    ratio_data = [
        ["DSCR", fmt(ratios.get("DSCR"))],
        ["ROCE", fmt(ratios.get("ROCE"), pct=True)],
        ["ROA", fmt(ratios.get("ROA"), pct=True)],
        ["Current Ratio", fmt(ratios.get("Current Ratio"))],
        ["Debt–Equity", fmt(ratios.get("Debt-Equity Ratio"))],
        ["Interest Coverage", fmt(ratios.get("Interest Coverage Ratio"))]
    ]

    ratio_table = Table(ratio_data, colWidths=[200, 100])
    ratio_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )

    story.append(Paragraph("Key Credit Ratios", bold_style))
    story.append(ratio_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Risk Summary", bold_style))

    story.append(Paragraph(
        f"- Overall Risk Level: {risk_output.get('overall_risk', 'NA')}",
        normal_style
    ))
    story.append(Paragraph(
        f"- Red Flags: {risk_output.get('red_flags', [])}",
        normal_style
    ))
    story.append(Paragraph(
        f"- Fatal Flags: {risk_output.get('fatal_flags', [])}",
        normal_style
    ))

    story.append(Spacer(1, 10))


    story.append(Paragraph("Credit Commentary", bold_style))

    strengths = commentary.get("strengths", [])
    weaknesses = commentary.get("weaknesses", [])
    lending_view = commentary.get("lending_view", "")

    story.append(Paragraph("<b>Strengths</b>", normal_style))
    if strengths:
        for s in strengths[:3]:
            story.append(Paragraph(f"- {s}", normal_style))
    else:
        story.append(Paragraph("- No major strengths highlighted.", normal_style))

    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>Watch Points</b>", normal_style))
    if weaknesses:
        for w in weaknesses[:2]:
            story.append(Paragraph(f"- {w}", normal_style))
    else:
        story.append(Paragraph("- No material weaknesses identified.", normal_style))

    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>Lending Conclusion</b>", normal_style))
    story.append(Paragraph(lending_view, normal_style))

    story.append(Spacer(1, 12))

  
    footer = (
        f"Prepared by CREDA | Generated on {datetime.now().strftime('%d %b %Y %H:%M')}"
    )
    story.append(Paragraph(
        footer,
        ParagraphStyle(
            "Footer",
            fontSize=7,
            alignment=TA_RIGHT,
            textColor=colors.grey
        )
    ))

    doc.build(story)
    return output_path
