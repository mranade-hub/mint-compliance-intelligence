import json

def classify_structure(wolfgang, structure_text):

    prompt = f"""
You are auditing a project folder.

Classify files into phases.

Phases:
- Engage
- Design
- Build
- Partner Onboarding
- Validation
- Closure

Return ONLY valid JSON in this exact format:

{{
  "phases": ["Engage","Design","Build"]
}}

Structure:
{structure_text}
"""

    response = wolfgang.send_prompt(prompt)

    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        raise Exception("Invalid JSON from Wolfgang classification")

    return data