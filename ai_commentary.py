from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """
You are a senior credit analyst at a commercial bank.

Your task is to REWRITE credit commentary in professional banking language.

STRICT RULES:
- Do NOT add new facts.
- Do NOT change any numbers.
- Do NOT change the risk level or conclusion.
- Do NOT add opinions beyond what is stated.
- Preserve the meaning exactly.
- Improve clarity, tone, and conciseness only.
"""

def polish_credit_commentary(commentary):
    """
    Input:
      commentary = {
        "summary": str,
        "strengths": [str],
        "weaknesses": [str],
        "conclusion": str
      }

    Output: same structure, improved language
    """

    user_prompt = f"""
Rewrite the following credit commentary strictly following the rules.

SUMMARY:
{commentary['summary']}

STRENGTHS:
{chr(10).join(commentary['strengths'])}

WEAKNESSES / WATCH POINTS:
{chr(10).join(commentary['weaknesses'])}

CONCLUSION:
{commentary['conclusion']}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2
    )

    text = response.choices[0].message.content.strip()

    # ---------- Simple parsing back into structure ----------
    # We keep this conservative to avoid hallucinations

    sections = {
        "summary": "",
        "strengths": [],
        "weaknesses": [],
        "conclusion": ""
    }

    current = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.upper().startswith("SUMMARY"):
            current = "summary"
            continue
        elif line.upper().startswith("STRENGTH"):
            current = "strengths"
            continue
        elif line.upper().startswith("WEAK"):
            current = "weaknesses"
            continue
        elif line.upper().startswith("CONCLUSION"):
            current = "conclusion"
            continue

        if current == "summary":
            sections["summary"] += (" " + line)
        elif current == "conclusion":
            sections["conclusion"] += (" " + line)
        elif current in ("strengths", "weaknesses"):
            sections[current].append(line.lstrip("- ").strip())

    # Fallback safety
    if not sections["summary"]:
        return commentary

    return sections
