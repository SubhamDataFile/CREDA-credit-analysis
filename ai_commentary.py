import os
from openai import OpenAI


def polish_credit_commentary(commentary: dict) -> dict:
    """
    Language-only enhancement of credit commentary.
    Numbers, ratios, and conclusions remain unchanged.
    """

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    client = OpenAI(api_key=api_key)

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

Improve ONLY the language, clarity, and professional tone
of the following credit commentary.

STRICT RULES:
- Do NOT change numbers
- Do NOT change ratios
- Do NOT change conclusions
- Do NOT add new insights

Rewrite cleanly and concisely.

TEXT:
{base_text}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        temperature=0.3,
    )

    improved_text = response.output_text
    if not improved_text:
        raise RuntimeError("Empty response from OpenAI")

    commentary["summary"] = improved_text
    commentary["ai_enhanced"] = True
    return commentary
