"""
hindsight_service.py
--------------------
Handles all interactions with the Hindsight persistent memory API.

Hindsight gives IncidentMind AI its long-term memory:
  - RETAIN: Store resolved incident postmortems so future incidents can learn from them.
  - RECALL: Retrieve relevant historical incidents when a new incident is reported.

SDK: hindsight-client
Docs: https://docs.hindsight.vectorize.io/python-sdk/
"""

import os
from typing import Optional
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────

HINDSIGHT_API_KEY  = os.getenv("HINDSIGHT_API_KEY", "")
HINDSIGHT_BASE_URL = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io")
HINDSIGHT_BANK_ID  = os.getenv("HINDSIGHT_BANK_ID", "incidentmind-ai")

# ── Client factory ────────────────────────────────────────────────────────────

def get_hindsight_client() -> Hindsight:
    """
    Create and return a Hindsight client instance.
    Raises ValueError if the API key is not configured.
    """
    if not HINDSIGHT_API_KEY:
        raise ValueError(
            "HINDSIGHT_API_KEY is not set. "
            "Copy .env.example to .env and add your Hindsight API key."
        )
    return Hindsight(
        base_url=HINDSIGHT_BASE_URL,
        api_key=HINDSIGHT_API_KEY,
        timeout=60.0,
    )


# ── Bank initialisation ───────────────────────────────────────────────────────

def ensure_bank_exists() -> dict:
    """
    Make sure the IncidentMind memory bank exists in Hindsight.
    Creates it on first run; subsequent calls are safe (bank already exists).

    Returns a dict with keys:
        success (bool), message (str), bank_id (str)
    """
    try:
        client = get_hindsight_client()
        try:
            bank = client.create_bank(
                bank_id=HINDSIGHT_BANK_ID,
                name="IncidentMind AI – Incident Memory",
                background=(
                    "This memory bank stores production incident postmortems for "
                    "IncidentMind AI. It contains root causes, successful resolutions, "
                    "and lessons learned so that future similar incidents can be resolved "
                    "faster using historical evidence."
                ),
            )
            client.close()
            return {
                "success": True,
                "message": f"Memory bank '{HINDSIGHT_BANK_ID}' created.",
                "bank_id": bank.bank_id,
            }
        except Exception as inner:
            # Hindsight returns an error when the bank already exists —
            # that is expected and safe to ignore.
            client.close()
            err_str = str(inner).lower()
            if "already exists" in err_str or "conflict" in err_str or "400" in err_str or "409" in err_str:
                return {
                    "success": True,
                    "message": f"Memory bank '{HINDSIGHT_BANK_ID}' already exists.",
                    "bank_id": HINDSIGHT_BANK_ID,
                }
            raise

    except ValueError as ve:
        return {"success": False, "message": str(ve), "bank_id": ""}
    except Exception as e:
        return {
            "success": False,
            "message": f"Could not connect to Hindsight: {e}",
            "bank_id": "",
        }


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

    Hindsight will extract structured facts from the postmortem text and index
    them for future semantic recall.  The next time a similar incident occurs,
    recall() will surface this postmortem as a relevant historical memory.

    Returns a dict with keys:
        success (bool), message (str)
    """
    # Build a rich, structured postmortem document so Hindsight can extract
    # meaningful facts from it.
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
            bank_id=HINDSIGHT_BANK_ID,
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
                f"Postmortem for '{service}' successfully stored in Hindsight. "
                "Future incidents can now recall this experience."
            ),
        }

    except ValueError as ve:
        return {"success": False, "message": str(ve)}
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to store postmortem in Hindsight: {e}",
        }


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

    Builds a rich semantic query from the incident details and retrieves the
    most relevant postmortems from the memory bank.

    Returns a dict with keys:
        success     (bool)
        memories    (list[dict])  – each has 'text' and 'type'
        count       (int)
        message     (str)
    """
    # Build a descriptive search query so Hindsight can find semantically
    # similar historical incidents across service names, error types, and
    # root causes.
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
            bank_id=HINDSIGHT_BANK_ID,
            query=query,
            budget="mid",      # balance speed vs. thoroughness
            max_tokens=4096,
        )
        client.close()

        memories = []
        for mem in result.results:
            memories.append({
                "text": mem.text,
                "type": getattr(mem, "type", "observation"),
            })

        count = len(memories)
        if count == 0:
            message = (
                "No relevant historical incidents were found. "
                "This may be the first occurrence of this type of incident."
            )
        else:
            message = f"{count} relevant historical memory{'s' if count != 1 else ''} retrieved from Hindsight."

        return {
            "success": True,
            "memories": memories,
            "count": count,
            "message": message,
        }

    except ValueError as ve:
        return {
            "success": False,
            "memories": [],
            "count": 0,
            "message": str(ve),
        }
    except Exception as e:
        return {
            "success": False,
            "memories": [],
            "count": 0,
            "message": f"Failed to recall memories from Hindsight: {e}",
        }


# ── Health check ──────────────────────────────────────────────────────────────

def check_hindsight_connection() -> dict:
    """
    Quick connectivity check: attempts to create/verify the memory bank.
    Returns a dict with keys: success (bool), message (str).
    """
    if not HINDSIGHT_API_KEY:
        return {
            "success": False,
            "message": "HINDSIGHT_API_KEY not configured.",
        }
    return ensure_bank_exists()


# ── Format memories for display / LLM prompt ─────────────────────────────────

def format_memories_for_prompt(memories: list) -> str:
    """
    Convert the list of Hindsight memory dicts into a clean text block
    suitable for injecting into an LLM prompt.
    """
    if not memories:
        return "No historical incidents found in Hindsight memory."

    lines = []
    for i, mem in enumerate(memories, 1):
        lines.append(f"[Memory {i}]")
        lines.append(mem.get("text", "").strip())
        lines.append("")   # blank line between memories

    return "\n".join(lines).strip()
