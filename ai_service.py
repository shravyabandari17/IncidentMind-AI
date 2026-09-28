"""
ai_service.py
-------------
Handles all interactions with the Groq LLM API.

The AI service takes the current incident details plus the historical memories
retrieved from Hindsight and produces a structured incident analysis:
  - Incident Summary
  - Possible Root Cause
  - Evidence From Previous Incidents  (based ONLY on Hindsight memories)
  - Investigation Steps
  - Recommended Resolution
  - Confidence level

The LLM is explicitly instructed NOT to invent historical incidents —
it may only reference memories that were actually returned by Hindsight.
"""

import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are IncidentMind AI, an expert Site Reliability Engineer (SRE) and
incident responder. Your job is to help software engineers investigate and resolve
production incidents quickly.

You are given:
1. Details of the CURRENT incident (service, error, severity, environment, recent changes).
2. HISTORICAL MEMORIES retrieved from Hindsight — real postmortems of past incidents
   that have been stored in persistent memory.

IMPORTANT RULES:
- You MUST base the "Evidence From Previous Incidents" section ONLY on the historical
  memories actually provided to you. Do NOT invent or hallucinate historical incidents.
- If no historical memories are provided, clearly state that no historical data is available
  and base your analysis on general SRE knowledge.
- Clearly distinguish between historical evidence (from Hindsight) and your own reasoning.
- Be specific, practical, and actionable in your recommendations.
- Write for an experienced engineer — skip generic advice and focus on what matters.

OUTPUT FORMAT:
Respond with exactly these sections, using markdown headers:

## Incident Summary
Brief overview of what is happening and its potential impact.

## Possible Root Cause
Most likely root cause(s) based on the error, environment, and any historical evidence.
Explain your reasoning.

## Evidence From Previous Incidents
What the historical Hindsight memories tell us about this type of incident.
If no memories were found, say: "No historical data available in Hindsight memory."
Quote or paraphrase specific details from the memories — do not fabricate.

## Investigation Steps
Numbered list of concrete diagnostic steps the engineer should take right now,
in priority order.

## Recommended Resolution
Specific actions to resolve the incident based on the evidence and analysis.
Include any configuration changes, rollbacks, or fixes to try.

## Confidence
Rate your confidence in this analysis: Low / Medium / High
Explain briefly why (e.g., strong historical match, limited data, novel error).
"""

# ── Groq client factory ────────────────────────────────────────────────────────

def get_groq_client() -> Groq:
    """Return a configured Groq client. Raises ValueError if key is missing."""
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not set. "
            "Copy .env.example to .env and add your Groq API key."
        )
    return Groq(api_key=GROQ_API_KEY)


# ── Main analysis function ─────────────────────────────────────────────────────

def analyze_incident(
    service: str,
    error: str,
    severity: str,
    environment: str,
    recent_changes: str,
    historical_memories: list,
) -> dict:
    """
    Send the current incident + Hindsight memories to Groq for analysis.

    Parameters
    ----------
    service             : Name of the affected service.
    error               : Error message / log snippet.
    severity            : Low | Medium | High | Critical.
    environment         : Development | Testing | Production.
    recent_changes      : What changed recently before the incident.
    historical_memories : List of memory dicts from hindsight_service.recall_similar_incidents()
                          Each has 'text' and 'type'.

    Returns
    -------
    dict with keys:
        success  (bool)
        analysis (str)   – full markdown analysis text
        message  (str)   – error message on failure
    """
    try:
        client = get_groq_client()

        # ── Build the user prompt ─────────────────────────────────────────────
        # Format historical memories clearly so the LLM can reference them.
        if historical_memories:
            memories_section = _format_memories_for_prompt(historical_memories)
        else:
            memories_section = "No historical incidents found in Hindsight memory."

        user_prompt = f"""
CURRENT INCIDENT
================
Service Name:      {service}
Severity:          {severity}
Environment:       {environment}
Error / Logs:      {error}
Recent Changes:    {recent_changes if recent_changes.strip() else "None reported"}

HISTORICAL MEMORY (from Hindsight)
====================================
{memories_section}

Please analyze this incident and provide your structured assessment following the
format defined in your instructions.
""".strip()

        # ── Call Groq ──────────────────────────────────────────────────────────
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.3,   # lower = more focused, less hallucination
            max_tokens=2048,
        )

        analysis_text = response.choices[0].message.content.strip()

        return {
            "success": True,
            "analysis": analysis_text,
            "message": "Analysis complete.",
        }

    except ValueError as ve:
        return {
            "success": False,
            "analysis": "",
            "message": str(ve),
        }
    except Exception as e:
        return {
            "success": False,
            "analysis": "",
            "message": f"Failed to get analysis from Groq: {e}",
        }


# ── Helper: format memories for the LLM prompt ────────────────────────────────

def _format_memories_for_prompt(memories: list) -> str:
    """
    Convert Hindsight memory dicts into a clearly numbered text block
    for injection into the LLM user prompt.
    """
    lines = []
    for i, mem in enumerate(memories, 1):
        text = mem.get("text", "").strip()
        mem_type = mem.get("type", "observation")
        lines.append(f"Historical Memory #{i} [{mem_type}]:")
        lines.append(text)
        lines.append("")   # blank line separator
    return "\n".join(lines).strip()


# ── Health check ──────────────────────────────────────────────────────────────

def check_groq_connection() -> dict:
    """
    Quick connectivity check: sends a minimal request to Groq.
    Returns a dict with keys: success (bool), message (str).
    """
    if not GROQ_API_KEY:
        return {
            "success": False,
            "message": "GROQ_API_KEY not configured.",
        }
    try:
        client = get_groq_client()
        # Minimal test request
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
        )
        return {
            "success": True,
            "message": f"Groq connected. Model: {GROQ_MODEL}",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Groq connection failed: {e}",
        }


# ── Parse analysis sections ────────────────────────────────────────────────────

def parse_analysis_sections(analysis_text: str) -> dict:
    """
    Parse the LLM markdown response into individual sections for structured
    display in the Streamlit UI.

    Returns a dict with keys matching the section headers:
        summary, root_cause, evidence, investigation_steps,
        recommended_resolution, confidence
    """
    sections = {
        "summary": "",
        "root_cause": "",
        "evidence": "",
        "investigation_steps": "",
        "recommended_resolution": "",
        "confidence": "",
    }

    # Map markdown headers to dict keys
    header_map = {
        "## Incident Summary":                "summary",
        "## Possible Root Cause":             "root_cause",
        "## Evidence From Previous Incidents": "evidence",
        "## Investigation Steps":             "investigation_steps",
        "## Recommended Resolution":          "recommended_resolution",
        "## Confidence":                      "confidence",
    }

    current_key = None
    current_lines = []

    for line in analysis_text.splitlines():
        # Check if this line is a known section header
        matched_header = None
        for header, key in header_map.items():
            if line.strip().startswith(header):
                matched_header = key
                break

        if matched_header:
            # Save previous section
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = matched_header
            current_lines = []
        else:
            if current_key:
                current_lines.append(line)

    # Save the last section
    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections
