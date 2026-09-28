"""
hindsight_service.py
--------------------
Handles all interactions with the Hindsight persistent memory API.

Hindsight gives IncidentMind AI its long-term memory:
  - RETAIN: Store resolved incident postmortems so future incidents can learn from them.
  - RECALL: Retrieve relevant historical incidents when a new incident is reported.

SDK: hindsight-client
Docs: https://docs.hindsight.vectorize.io/python-sdk/

Secret resolution order:
  1. st.secrets  (Streamlit Community Cloud)
  2. os.environ  (local .env via python-dotenv)
"""

import os
from dotenv import load_dotenv
from hindsight_client import Hindsight

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


# ── Configuration ─────────────────────────────────────────────────────────────
# Values are resolved lazily inside functions so st.secrets is available
# by the time Streamlit has fully initialised.

def _api_key()  -> str: return _secret("HINDSIGHT_API_KEY")
def _base_url() -> str: return _secret("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io")
def _bank_id()  -> str: return _secret("HINDSIGHT_BANK_ID", "incidentmind-ai")


# ── Client factory ────────────────────────────────────────────────────────────

def get_hindsight_client() -> Hindsight:
    """
    Create and return a configured Hindsight client.
    Raises ValueError if the API key is not set.
    """
    key = _api_key()
    if not key:
        raise ValueError(
            "HINDSIGHT_API_KEY is not set. "
            "Add it to Streamlit Cloud secrets or your local .env file."
        )
    return Hindsight(
        base_url=_base_url(),
        api_key=key,
        timeout=60.0,
    )


# ── Bank initialisation ───────────────────────────────────────────────────────

def ensure_bank_exists() -> dict:
    """
    Make sure the IncidentMind memory bank exists in Hindsight.
    Creates it on first run; safe to call repeatedly.

    Returns: dict(success, message, bank_id)
    """
    try:
        client = get_hindsight_client()
        bank_id = _bank_id()
        try:
            bank = client.create_bank(
                bank_id=bank_id,
                name="IncidentMind AI – Incident Memory",
                background=(
                    "This memory bank stores production incident postmortems for "
                    "IncidentMind AI. It contains root causes, successful resolutions, "
                    "and lessons learned so that future similar incidents can be resolved "
                    "faster using historical evidence."
                ),
            )
            client.close()
            return {"success": True, "message": f"Memory bank '{bank_id}' created.", "bank_id": bank.bank_id}
        except Exception as inner:
            client.close()
            err = str(inner).lower()
            if any(x in err for x in ("already exists", "conflict", "400", "409")):
                return {"success": True, "message": f"Memory bank '{bank_id}' ready.", "bank_id": bank_id}
            raise
    except ValueError as ve:
        return {"success": False, "message": str(ve), "bank_id": ""}
    except Exception as e:
        return {"success": False, "message": f"Could not connect to Hindsight: {e}", "bank_id": ""}


# ── RETAIN – Store a postmortem ───────────────────────────────────────────────

def retain_postmortem(
    service: str,
    error: str,
    severity: str,
    environment: str,
    recent_changes: str,
    root_cause: str,
    resolution: str,
    resolution_time: str,
) -> dict:
    """
    RETAIN: Store a resolved incident postmortem in Hindsight memory.

    Returns: dict(success, message)
    """
    postmortem_text = f"""
INCIDENT POSTMORTEM — IncidentMind AI

Service: {service}
Severity: {severity}
Environment: {environment}

Error / Symptom:
{error}

Recent Changes Before Incident:
{recent_changes if recent_changes.strip() else "No recent changes reported."}

Root Cause:
{root_cause}

Successful Resolution:
{resolution}

Resolution Time: {resolution_time}

Summary:
The {severity.lower()}-severity incident in the {service} service on the {environment}
environment was caused by {root_cause.lower()}. It was resolved by {resolution.lower()}.
Total time to resolution was {resolution_time}.
""".strip()

    try:
        client = get_hindsight_client()
        client.retain(
            bank_id=_bank_id(),
            content=postmortem_text,
            context=(
                f"Production incident postmortem: {service} | {severity} | "
                f"{environment} | Root cause: {root_cause}"
            ),
            metadata={
                "service": service,
                "severity": severity,
                "environment": environment,
                "root_cause": root_cause,
                "resolution_time": resolution_time,
                "type": "incident_postmortem",
            },
        )
        client.close()
        return {
            "success": True,
            "message": (
                f"Postmortem for '{service}' stored in Hindsight. "
                "Future incidents can now recall this experience."
            ),
        }
    except ValueError as ve:
        return {"success": False, "message": str(ve)}
    except Exception as e:
        return {"success": False, "message": f"Failed to store postmortem in Hindsight: {e}"}


# ── RECALL – Retrieve relevant historical incidents ───────────────────────────

def recall_similar_incidents(
    service: str,
    error: str,
    severity: str,
    environment: str,
    recent_changes: str,
) -> dict:
    """
    RECALL: Search Hindsight for historical incidents similar to the current one.

    Returns: dict(success, memories, count, message)
    """
    query = (
        f"Service: {service}. "
        f"Error: {error}. "
        f"Severity: {severity}. "
        f"Environment: {environment}."
    )
    if recent_changes.strip():
        query += f" Recent changes: {recent_changes}."
    query += (
        " Find previous incidents with similar symptoms, root causes, "
        "or resolutions that could help diagnose this issue."
    )

    try:
        client = get_hindsight_client()
        result = client.recall(
            bank_id=_bank_id(),
            query=query,
            budget="mid",
            max_tokens=4096,
        )
        client.close()

        memories = [
            {"text": mem.text, "type": getattr(mem, "type", "observation")}
            for mem in result.results
        ]
        count = len(memories)
        message = (
            f"{count} relevant historical memory{'s' if count != 1 else ''} retrieved from Hindsight."
            if count > 0
            else (
                "No relevant historical incidents were found. "
                "This may be the first occurrence of this type of incident."
            )
        )
        return {"success": True, "memories": memories, "count": count, "message": message}

    except ValueError as ve:
        return {"success": False, "memories": [], "count": 0, "message": str(ve)}
    except Exception as e:
        return {"success": False, "memories": [], "count": 0, "message": f"Failed to recall from Hindsight: {e}"}


# ── Health check ──────────────────────────────────────────────────────────────

def check_hindsight_connection() -> dict:
    """Quick connectivity check. Returns dict(success, message)."""
    if not _api_key():
        return {"success": False, "message": "HINDSIGHT_API_KEY not configured."}
    return ensure_bank_exists()


# ── Format memories for LLM prompt ───────────────────────────────────────────

def format_memories_for_prompt(memories: list) -> str:
    """Convert Hindsight memory dicts into a clean text block for an LLM prompt."""
    if not memories:
        return "No historical incidents found in Hindsight memory."
    lines = []
    for i, mem in enumerate(memories, 1):
        lines.append(f"[Memory {i}]")
        lines.append(mem.get("text", "").strip())
        lines.append("")
    return "\n".join(lines).strip()
