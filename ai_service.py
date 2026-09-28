"""
ai_service.py
-------------
Handles all interactions with the Groq LLM API.

The AI service takes the current incident details plus the historical memories
retrieved from Hindsight and produces a structured incident analysis.

Secret resolution order:
  1. st.secrets  (Streamlit Community Cloud)
  2. os.environ  (local .env via python-dotenv)
"""

import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()  # no-op on Streamlit Cloud, works locally


def _secret(key: str, default: str = "") -> str:
    """
    Read a secret from st.secrets (Streamlit Cloud) first,
    then fall back to environment variables (local .env).
    """
    try:
        import streamlit as st
        val = st.secrets.get(key, None)
        if val:
            return str(val)
    except Exception:
        pass
    return os.getenv(key, default)


# ── Configuration (lazy so st.secrets is initialised first) ──────────────────

def _api_key() -> str: return _secret("GROQ_API_KEY")
def _model()   -> str: return _secret("GROQ_MODEL", "openai/gpt-oss-120b")


# Expose GROQ_MODEL as a module-level attribute for the UI spinner label.
# It reads lazily from secrets so it works on both local and Cloud.
class _ModelProxy:
    def __str__(self): return _model()
    def __repr__(self): return _model()

GROQ_MODEL = _ModelProxy()


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
    key = _api_key()
    if not key:
        raise ValueError(
            "GROQ_API_KEY is not set. "
            "Add it to Streamlit Cloud secrets or your local .env file."
        )
    return Groq(api_key=key)


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

    Returns: dict(success, analysis, message)
    """
    try:
        client = get_groq_client()
        model  = _model()

        memories_section = (
            _format_memories_for_prompt(historical_memories)
            if historical_memories
            else "No historical incidents found in Hindsight memory."
        )

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

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=2048,
        )

        analysis_text = response.choices[0].message.content.strip()
        return {"success": True, "analysis": analysis_text, "message": "Analysis complete."}

    except ValueError as ve:
        return {"success": False, "analysis": "", "message": str(ve)}
    except Exception as e:
        return {"success": False, "analysis": "", "message": f"Failed to get analysis from Groq: {e}"}


# ── Health check ──────────────────────────────────────────────────────────────

def check_groq_connection() -> dict:
    """Quick connectivity check. Returns dict(success, message)."""
    if not _api_key():
        return {"success": False, "message": "GROQ_API_KEY not configured."}
    try:
        client = get_groq_client()
        client.chat.completions.create(
            model=_model(),
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
        )
        return {"success": True, "message": f"Groq connected. Model: {_model()}"}
    except Exception as e:
        return {"success": False, "message": f"Groq connection failed: {e}"}


# ── Parse analysis sections ────────────────────────────────────────────────────

def parse_analysis_sections(analysis_text: str) -> dict:
    """
    Parse the LLM markdown response into individual sections for structured
    display in the Streamlit UI.
    """
    sections = {
        "summary": "",
        "root_cause": "",
        "evidence": "",
        "investigation_steps": "",
        "recommended_resolution": "",
        "confidence": "",
    }

    header_map = {
        "## Incident Summary":                "summary",
        "## Possible Root Cause":             "root_cause",
        "## Evidence From Previous Incidents": "evidence",
        "## Investigation Steps":             "investigation_steps",
        "## Recommended Resolution":          "recommended_resolution",
        "## Confidence":                      "confidence",
    }

    current_key   = None
    current_lines = []

    for line in analysis_text.splitlines():
        matched = None
        for header, key in header_map.items():
            if line.strip().startswith(header):
                matched = key
                break
        if matched:
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key   = matched
            current_lines = []
        else:
            if current_key:
                current_lines.append(line)

    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections


# ── Internal helper ───────────────────────────────────────────────────────────

def _format_memories_for_prompt(memories: list) -> str:
    lines = []
    for i, mem in enumerate(memories, 1):
        text     = mem.get("text", "").strip()
        mem_type = mem.get("type", "observation")
        lines.append(f"Historical Memory #{i} [{mem_type}]:")
        lines.append(text)
        lines.append("")
    return "\n".join(lines).strip()
