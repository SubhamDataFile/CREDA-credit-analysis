import os
from openai import OpenAI


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def polish_credit_commentary(commentary: dict) -> dict:
    """
    Language-only enhancement of credit commentary.
    Numbers, ratios, and conclusions remain unchanged.
    """

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not configured")

    base_text = f"""
CREDIT SUMMARY:
{commentary.get("summary", "")}

STRENGTHS:
- """ + "\n- ".join(commentary.get("strengths", [])) + """

WEAKNESSES:
- """ + "\n- ".join(commentary.get("weaknesses", [])) + """

CONCLUSION:
{commentary.get("conclusion", "")}
"""

    prompt = f"""
You are a senior credit analyst.

Improve the language, structure, and professional tone of the following
credit commentary. Do NOT change numbers, logic, or conclusions.
Do NOT add new insights.

Rewrite cleanly and concisely.

TEXT:
{base_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a professional credit analyst."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )

    improved_text = response.choices[0].message.content.strip()
    if not improved_text:
        raise RuntimeError("Empty response from OpenAI")

    commentary["summary"] = improved_text
    commentary["ai_enhanced"] = True
    return commentary
