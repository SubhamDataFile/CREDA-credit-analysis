import os
from openai import OpenAI


def polish_credit_commentary(commentary: dict) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    client = OpenAI(api_key=api_key)

    prompt = f"""
Improve the professional tone and clarity of the following credit commentary.
Do NOT change any numbers, logic, or conclusions.

Commentary:
{commentary}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        temperature=0.3,
    )

    
    text = response.output_text
    if not text:
        raise RuntimeError("Empty response from OpenAI")

    commentary["summary"] = text
    return commentary
