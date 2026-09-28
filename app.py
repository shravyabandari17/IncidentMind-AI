"""
app.py
------
IncidentMind AI — Main Streamlit Application

AI-powered Incident Response Agent with Hindsight Persistent Memory.

Workflow:
  1. Engineer reports a new incident (service, error, severity, environment, changes)
  2. Hindsight RECALL  → retrieve similar historical incidents from memory
  3. Groq LLM          → analyze current incident + historical memories
  4. Display analysis   → root cause, evidence, investigation steps, resolution
  5. Engineer resolves  → fills in postmortem form
  6. Hindsight RETAIN  → store postmortem so future incidents can learn from it

Run:
  streamlit run app.py
"""

import json
import time
import streamlit as st
from datetime import datetime

import hindsight_service as hs
import ai_service as ai

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="IncidentMind AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS  — dark professional SRE dashboard theme
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ── Base ── */
[data-testid="stAppViewContainer"] {
    background: #0d1117;
    color: #e6edf3;
}
[data-testid="stSidebar"] {
    background: #161b22;
    border-right: 1px solid #21262d;
}
[data-testid="stHeader"] { background: transparent; }

/* ── Typography ── */
h1, h2, h3, h4 { color: #e6edf3 !important; }
p, li, label { color: #c9d1d9; }
.stMarkdown { color: #c9d1d9; }

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 16px;
}
[data-testid="metric-container"] label { color: #8b949e !important; font-size: 12px; }
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #58a6ff !important;
    font-size: 28px !important;
    font-weight: 700 !important;
}

/* ── Cards ── */
.card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.card-header {
    font-size: 15px;
    font-weight: 700;
    color: #e6edf3;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #21262d;
}

/* ── Memory card ── */
.memory-card {
    background: #0d2137;
    border: 1px solid #1f6feb;
    border-left: 4px solid #58a6ff;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 12px;
}
.memory-badge {
    display: inline-block;
    background: #1f6feb22;
    color: #58a6ff;
    border: 1px solid #1f6feb;
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.memory-text {
    color: #c9d1d9;
    font-size: 13px;
    line-height: 1.6;
    font-family: 'Courier New', monospace;
}

/* ── Severity badges ── */
.badge-critical {
    background: #ff000022; color: #ff7b72;
    border: 1px solid #ff7b72; border-radius: 12px;
    padding: 2px 12px; font-size: 12px; font-weight: 700;
}
.badge-high {
    background: #ff8c0022; color: #ffa657;
    border: 1px solid #ffa657; border-radius: 12px;
    padding: 2px 12px; font-size: 12px; font-weight: 700;
}
.badge-medium {
    background: #ffdf0022; color: #e3b341;
    border: 1px solid #e3b341; border-radius: 12px;
    padding: 2px 12px; font-size: 12px; font-weight: 700;
}
.badge-low {
    background: #23863622; color: #3fb950;
    border: 1px solid #3fb950; border-radius: 12px;
    padding: 2px 12px; font-size: 12px; font-weight: 700;
}

/* ── Status banner ── */
.hindsight-banner {
    background: linear-gradient(135deg, #0d2137 0%, #091d2e 100%);
    border: 1px solid #1f6feb;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.hindsight-banner-count {
    font-size: 32px;
    font-weight: 800;
    color: #58a6ff;
}
.hindsight-banner-label {
    font-size: 14px;
    color: #8b949e;
}

/* ── Success / error ── */
.success-box {
    background: #0f291e;
    border: 1px solid #3fb950;
    border-left: 4px solid #3fb950;
    border-radius: 8px;
    padding: 14px 18px;
    color: #3fb950;
    font-weight: 600;
    margin: 12px 0;
}
.error-box {
    background: #2d1117;
    border: 1px solid #ff7b72;
    border-left: 4px solid #ff7b72;
    border-radius: 8px;
    padding: 14px 18px;
    color: #ff7b72;
    font-weight: 600;
    margin: 12px 0;
}
.info-box {
    background: #0d2137;
    border: 1px solid #58a6ff;
    border-left: 4px solid #58a6ff;
    border-radius: 8px;
    padding: 14px 18px;
    color: #79c0ff;
    margin: 12px 0;
}

/* ── Section dividers ── */
.section-title {
    font-size: 18px;
    font-weight: 700;
    color: #e6edf3;
    margin: 28px 0 16px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #21262d;
    margin-left: 12px;
}

/* ── Inputs / textareas ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] select {
    background: #0d1117 !important;
    border: 1px solid #30363d !important;
    color: #e6edf3 !important;
    border-radius: 6px !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #58a6ff !important;
    box-shadow: 0 0 0 3px #1f6feb33 !important;
}

/* ── Buttons ── */
[data-testid="stFormSubmitButton"] button,
.stButton button {
    background: #238636 !important;
    color: #ffffff !important;
    border: 1px solid #2ea043 !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    padding: 8px 20px !important;
    transition: all 0.2s ease;
}
[data-testid="stFormSubmitButton"] button:hover,
.stButton button:hover {
    background: #2ea043 !important;
    border-color: #3fb950 !important;
    transform: translateY(-1px);
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
}

/* ── Sidebar labels ── */
.sidebar-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #8b949e;
    font-weight: 600;
    margin-bottom: 4px;
}

/* ── Analysis section ── */
.analysis-section {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.analysis-section-title {
    font-size: 13px;
    font-weight: 700;
    color: #58a6ff;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE  — persists values across Streamlit reruns
# ─────────────────────────────────────────────────────────────────────────────

def init_session_state():
    defaults = {
        # Stats counters
        "incidents_analyzed":   0,
        "memories_found":       0,
        "incidents_resolved":   0,

        # Current incident
        "current_incident":     None,

        # Hindsight recall results
        "recall_result":        None,

        # AI analysis result
        "analysis_result":      None,

        # UI flow flags
        "show_postmortem":      False,
        "postmortem_saved":     False,

        # Hindsight bank status
        "bank_ready":           False,
        "bank_error":           "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def severity_badge(severity: str) -> str:
    cls = {
        "Critical": "badge-critical",
        "High":     "badge-high",
        "Medium":   "badge-medium",
        "Low":      "badge-low",
    }.get(severity, "badge-low")
    return f'<span class="{cls}">{severity}</span>'


def ensure_bank():
    """Initialise Hindsight bank once per session."""
    if not st.session_state.bank_ready:
        result = hs.ensure_bank_exists()
        if result["success"]:
            st.session_state.bank_ready = True
            st.session_state.bank_error = ""
        else:
            st.session_state.bank_error = result["message"]
    return st.session_state.bank_ready


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 8px 0 20px 0;'>
        <div style='font-size:40px;'>🧠</div>
        <div style='font-size:18px; font-weight:800; color:#e6edf3;'>IncidentMind AI</div>
        <div style='font-size:11px; color:#8b949e; margin-top:4px;'>Powered by Hindsight + Groq</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Navigation ──────────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-label">Navigation</div>', unsafe_allow_html=True)
    page = st.radio(
        label="page",
        options=["🚨 New Incident", "📚 Sample Data Loader", "ℹ️ About"],
        label_visibility="collapsed",
    )

    st.divider()

    # ── System status ────────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-label">System Status</div>', unsafe_allow_html=True)

    # Hindsight status
    hindsight_ok = ensure_bank()
    if hindsight_ok:
        st.markdown(
            '<div style="color:#3fb950; font-size:13px;">🟢 Hindsight Memory</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="color:#ff7b72; font-size:13px;">🔴 Hindsight Memory</div>',
            unsafe_allow_html=True,
        )
        st.caption(st.session_state.bank_error)

    # Groq status
    groq_status = ai.check_groq_connection()
    if groq_status["success"]:
        st.markdown(
            '<div style="color:#3fb950; font-size:13px;">🟢 Groq LLM</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="color:#ff7b72; font-size:13px;">🔴 Groq LLM</div>',
            unsafe_allow_html=True,
        )
        st.caption(groq_status["message"])

    st.divider()

    # ── Session stats ────────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-label">Session Stats</div>', unsafe_allow_html=True)
    st.metric("Incidents Analyzed",   st.session_state.incidents_analyzed)
    st.metric("Memories Retrieved",   st.session_state.memories_found)
    st.metric("Incidents Resolved",   st.session_state.incidents_resolved)

    st.divider()
    st.markdown(
        '<div style="font-size:10px; color:#484f58; text-align:center;">'
        'IncidentMind AI — Hackathon Demo<br>'
        'Memory powered by <a href="https://hindsight.vectorize.io" '
        'style="color:#58a6ff;">Hindsight</a></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div style='padding: 8px 0 24px 0;'>
    <div style='font-size:32px; font-weight:800; color:#e6edf3; letter-spacing:-0.5px;'>
        🧠 IncidentMind AI
    </div>
    <div style='font-size:15px; color:#8b949e; margin-top:4px;'>
        AI Incident Response Assistant with Persistent Memory
    </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: NEW INCIDENT
# ─────────────────────────────────────────────────────────────────────────────

if page == "🚨 New Incident":

    # ── Stats row ────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🚨 Incidents Analyzed",  st.session_state.incidents_analyzed)
    with col2:
        st.metric("🧠 Memories Found",      st.session_state.memories_found)
    with col3:
        st.metric("✅ Incidents Resolved",  st.session_state.incidents_resolved)
    with col4:
        bank_status = "🟢 Connected" if st.session_state.bank_ready else "🔴 Disconnected"
        st.metric("Hindsight Memory", bank_status)

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 1 — INCIDENT FORM
    # ════════════════════════════════════════════════════════════════════════

    st.markdown('<div class="section-title">🚨 Report Incident</div>', unsafe_allow_html=True)

    with st.form("incident_form", clear_on_submit=False):
        col_left, col_right = st.columns([3, 2])

        with col_left:
            service = st.text_input(
                "Service Name *",
                placeholder="e.g. Payment API, Auth Service, Order Service",
                help="The name of the service experiencing the incident.",
            )
            error = st.text_area(
                "Error / Logs *",
                placeholder="Paste the error message, stack trace, or log snippet here...",
                height=160,
                help="The primary error or symptom. Include any relevant log lines.",
            )
            recent_changes = st.text_area(
                "Recent Changes",
                placeholder="What was deployed, configured, or changed before this incident? (optional)",
                height=80,
                help="Recent deployments, config changes, infrastructure changes, etc.",
            )

        with col_right:
            severity = st.selectbox(
                "Severity *",
                options=["Critical", "High", "Medium", "Low"],
                index=1,
                help="Incident severity level.",
            )
            environment = st.selectbox(
                "Environment *",
                options=["Production", "Testing", "Development"],
                index=0,
                help="The environment where the incident is occurring.",
            )

            # Severity indicator
            sev_colors = {
                "Critical": ("#ff7b72", "🔴 All hands. Service down."),
                "High":     ("#ffa657", "🟠 Significant impact."),
                "Medium":   ("#e3b341", "🟡 Partial degradation."),
                "Low":      ("#3fb950", "🟢 Minor issue."),
            }
            sev_col, sev_desc = sev_colors[severity]
            st.markdown(
                f'<div style="background:#161b22; border:1px solid #21262d; border-radius:8px; '
                f'padding:12px 16px; margin-top:12px;">'
                f'<div style="color:{sev_col}; font-weight:700; font-size:14px;">{severity}</div>'
                f'<div style="color:#8b949e; font-size:12px; margin-top:4px;">{sev_desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            st.info(
                "💡 IncidentMind will search Hindsight for similar historical incidents "
                "before generating an AI analysis.",
                icon=None,
            )

        submitted = st.form_submit_button(
            "🔍 Analyze Incident",
            use_container_width=True,
            type="primary",
        )

    # ── Form validation & pipeline ───────────────────────────────────────────
    if submitted:
        # Validate required fields
        errors = []
        if not service.strip():
            errors.append("Service Name is required.")
        if not error.strip():
            errors.append("Error / Logs are required.")

        if errors:
            for err in errors:
                st.markdown(f'<div class="error-box">⚠️ {err}</div>', unsafe_allow_html=True)
        else:
            # Reset state for new analysis
            st.session_state.recall_result   = None
            st.session_state.analysis_result = None
            st.session_state.show_postmortem = False
            st.session_state.postmortem_saved = False

            # Store incident for postmortem use
            st.session_state.current_incident = {
                "service":        service.strip(),
                "error":          error.strip(),
                "severity":       severity,
                "environment":    environment,
                "recent_changes": recent_changes.strip(),
            }

            # ── STEP 1: Hindsight RECALL ──────────────────────────────────
            st.markdown(
                '<div class="section-title">🧠 Hindsight Memory</div>',
                unsafe_allow_html=True,
            )

            with st.spinner("🧠 Searching Hindsight for similar historical incidents..."):
                recall_result = hs.recall_similar_incidents(
                    service=service.strip(),
                    error=error.strip(),
                    severity=severity,
                    environment=environment,
                    recent_changes=recent_changes.strip(),
                )
            st.session_state.recall_result = recall_result
            st.session_state.incidents_analyzed += 1

            # Display Hindsight results
            if recall_result["success"]:
                count = recall_result["count"]
                st.session_state.memories_found += count

                if count > 0:
                    st.markdown(
                        f'<div class="hindsight-banner">'
                        f'<div style="font-size:28px;">🧠</div>'
                        f'<div>'
                        f'<div class="hindsight-banner-count">{count} Historical Memory{"s" if count != 1 else ""} Found</div>'
                        f'<div class="hindsight-banner-label">Hindsight retrieved relevant past incidents from persistent memory</div>'
                        f'</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    for i, mem in enumerate(recall_result["memories"], 1):
                        mem_type = mem.get("type", "observation").title()
                        with st.expander(f"📌 Historical Memory #{i}  [{mem_type}]", expanded=(i == 1)):
                            st.markdown(
                                f'<div class="memory-card">'
                                f'<div class="memory-badge">Hindsight Memory · {mem_type}</div>'
                                f'<div class="memory-text">{mem["text"]}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                else:
                    st.markdown(
                        '<div class="info-box">🔍 No relevant historical incidents were found in Hindsight. '
                        'This may be the first occurrence of this type of incident. The AI will analyze '
                        'based on general SRE knowledge.</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    f'<div class="error-box">⚠️ Hindsight recall failed: {recall_result["message"]}</div>',
                    unsafe_allow_html=True,
                )

            # ── STEP 2: AI Analysis ───────────────────────────────────────
            st.markdown(
                '<div class="section-title">🤖 AI Analysis</div>',
                unsafe_allow_html=True,
            )

            memories = recall_result.get("memories", []) if recall_result["success"] else []

            with st.spinner(f"🤖 Analyzing incident with Groq ({ai.GROQ_MODEL})..."):
                analysis_result = ai.analyze_incident(
                    service=service.strip(),
                    error=error.strip(),
                    severity=severity,
                    environment=environment,
                    recent_changes=recent_changes.strip(),
                    historical_memories=memories,
                )
            st.session_state.analysis_result = analysis_result

            if analysis_result["success"]:
                analysis_text = analysis_result["analysis"]
                sections = ai.parse_analysis_sections(analysis_text)

                # Render each section as a styled card
                section_config = [
                    ("summary",               "📋 Incident Summary",               "#58a6ff"),
                    ("root_cause",            "🔍 Possible Root Cause",             "#ffa657"),
                    ("evidence",              "🧠 Evidence From Previous Incidents", "#1f6feb"),
                    ("investigation_steps",   "🔬 Investigation Steps",             "#3fb950"),
                    ("recommended_resolution","💊 Recommended Resolution",          "#a371f7"),
                    ("confidence",            "📊 Confidence",                      "#e3b341"),
                ]

                for key, label, color in section_config:
                    content = sections.get(key, "").strip()
                    if content:
                        st.markdown(
                            f'<div class="analysis-section">'
                            f'<div class="analysis-section-title" style="color:{color};">{label}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(content)

                # Show full raw analysis in expander for copy/paste
                with st.expander("📄 View Full Analysis (Markdown)"):
                    st.text(analysis_text)

            else:
                st.markdown(
                    f'<div class="error-box">⚠️ AI analysis failed: {analysis_result["message"]}</div>',
                    unsafe_allow_html=True,
                )

            # Show postmortem section after analysis
            st.session_state.show_postmortem = True
            st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # RECALL RESULTS (persisted after form submit)
    # ════════════════════════════════════════════════════════════════════════

    if st.session_state.recall_result and not submitted:
        recall_result = st.session_state.recall_result
        incident      = st.session_state.current_incident or {}

        # Show incident badge
        if incident:
            sev = incident.get("severity", "")
            st.markdown(
                f'<div style="margin-bottom:12px;">'
                f'Analyzing: <strong style="color:#e6edf3;">{incident.get("service","")}</strong> '
                f'— {severity_badge(sev)} '
                f'<span style="color:#8b949e; font-size:12px;">{incident.get("environment","")}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── Hindsight Memory section ──────────────────────────────────────
        st.markdown(
            '<div class="section-title">🧠 Hindsight Memory</div>',
            unsafe_allow_html=True,
        )

        if recall_result["success"]:
            count = recall_result["count"]
            if count > 0:
                st.markdown(
                    f'<div class="hindsight-banner">'
                    f'<div style="font-size:28px;">🧠</div>'
                    f'<div>'
                    f'<div class="hindsight-banner-count">{count} Historical Memory{"s" if count != 1 else ""} Found</div>'
                    f'<div class="hindsight-banner-label">Retrieved from Hindsight persistent memory</div>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                for i, mem in enumerate(recall_result["memories"], 1):
                    mem_type = mem.get("type", "observation").title()
                    with st.expander(f"📌 Historical Memory #{i}  [{mem_type}]", expanded=(i == 1)):
                        st.markdown(
                            f'<div class="memory-card">'
                            f'<div class="memory-badge">Hindsight Memory · {mem_type}</div>'
                            f'<div class="memory-text">{mem["text"]}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
            else:
                st.markdown(
                    '<div class="info-box">🔍 No relevant historical incidents found in Hindsight. '
                    'This may be the first occurrence of this type of incident.</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                f'<div class="error-box">⚠️ {recall_result["message"]}</div>',
                unsafe_allow_html=True,
            )

        # ── AI Analysis section ───────────────────────────────────────────
        if st.session_state.analysis_result:
            analysis_result = st.session_state.analysis_result
            st.markdown(
                '<div class="section-title">🤖 AI Analysis</div>',
                unsafe_allow_html=True,
            )
            if analysis_result["success"]:
                sections = ai.parse_analysis_sections(analysis_result["analysis"])
                section_config = [
                    ("summary",               "📋 Incident Summary",               "#58a6ff"),
                    ("root_cause",            "🔍 Possible Root Cause",             "#ffa657"),
                    ("evidence",              "🧠 Evidence From Previous Incidents", "#1f6feb"),
                    ("investigation_steps",   "🔬 Investigation Steps",             "#3fb950"),
                    ("recommended_resolution","💊 Recommended Resolution",          "#a371f7"),
                    ("confidence",            "📊 Confidence",                      "#e3b341"),
                ]
                for key, label, color in section_config:
                    content = sections.get(key, "").strip()
                    if content:
                        st.markdown(
                            f'<div class="analysis-section">'
                            f'<div class="analysis-section-title" style="color:{color};">{label}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(content)
                with st.expander("📄 View Full Analysis (Markdown)"):
                    st.text(analysis_result["analysis"])
            else:
                st.markdown(
                    f'<div class="error-box">⚠️ {analysis_result["message"]}</div>',
                    unsafe_allow_html=True,
                )

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 3 — POSTMORTEM / HINDSIGHT RETAIN
    # ════════════════════════════════════════════════════════════════════════

    if st.session_state.show_postmortem and st.session_state.current_incident:
        incident = st.session_state.current_incident

        st.markdown("---")
        st.markdown(
            '<div class="section-title">📝 Record Resolution & Postmortem</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="info-box">After resolving the incident, record the postmortem below. '
            'IncidentMind will store it in <strong>Hindsight memory</strong> so future similar '
            'incidents can benefit from this experience.</div>',
            unsafe_allow_html=True,
        )

        if st.session_state.postmortem_saved:
            st.markdown(
                '<div class="success-box">'
                '✅ Postmortem successfully stored in Hindsight.<br>'
                '🧠 IncidentMind has learned from this incident.'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            with st.form("postmortem_form"):
                st.markdown(
                    f'<div style="color:#8b949e; font-size:13px; margin-bottom:16px;">'
                    f'Incident: <strong style="color:#e6edf3;">{incident["service"]}</strong> — '
                    f'{severity_badge(incident["severity"])} — '
                    f'<span>{incident["environment"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                root_cause = st.text_area(
                    "Actual Root Cause *",
                    placeholder="What was the actual root cause of this incident?",
                    height=100,
                )
                resolution = st.text_area(
                    "Successful Resolution *",
                    placeholder="What steps resolved the incident? Be specific.",
                    height=100,
                )
                resolution_time = st.text_input(
                    "Resolution Time *",
                    placeholder="e.g. 45 minutes, 2 hours 15 minutes",
                )

                save_submitted = st.form_submit_button(
                    "💾 Save Postmortem to Hindsight",
                    use_container_width=True,
                    type="primary",
                )

            if save_submitted:
                pm_errors = []
                if not root_cause.strip():
                    pm_errors.append("Actual Root Cause is required.")
                if not resolution.strip():
                    pm_errors.append("Successful Resolution is required.")
                if not resolution_time.strip():
                    pm_errors.append("Resolution Time is required.")

                if pm_errors:
                    for err in pm_errors:
                        st.markdown(
                            f'<div class="error-box">⚠️ {err}</div>',
                            unsafe_allow_html=True,
                        )
                else:
                    with st.spinner("💾 Storing postmortem in Hindsight memory..."):
                        retain_result = hs.retain_postmortem(
                            service=incident["service"],
                            error=incident["error"],
                            severity=incident["severity"],
                            environment=incident["environment"],
                            recent_changes=incident["recent_changes"],
                            root_cause=root_cause.strip(),
                            resolution=resolution.strip(),
                            resolution_time=resolution_time.strip(),
                        )

                    if retain_result["success"]:
                        st.session_state.postmortem_saved  = True
                        st.session_state.incidents_resolved += 1
                        st.markdown(
                            '<div class="success-box">'
                            '✅ Postmortem successfully stored in Hindsight.<br>'
                            '🧠 IncidentMind has learned from this incident.'
                            '</div>',
                            unsafe_allow_html=True,
                        )
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.markdown(
                            f'<div class="error-box">⚠️ Failed to save postmortem: {retain_result["message"]}</div>',
                            unsafe_allow_html=True,
                        )


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: SAMPLE DATA LOADER
# ─────────────────────────────────────────────────────────────────────────────

elif page == "📚 Sample Data Loader":
    st.markdown(
        '<div class="section-title">📚 Sample Data Loader</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="info-box">'
        '⚠️ <strong>Demo data only.</strong> The incidents below are <strong>synthetic</strong> — '
        'they are not real production incidents. Load them into Hindsight memory to demonstrate '
        'the recall feature, then test it by reporting a similar incident on the New Incident page.'
        '</div>',
        unsafe_allow_html=True,
    )

    # Load the JSON
    try:
        with open("sample_incidents.json", "r") as f:
            sample_data = json.load(f)
        incidents = sample_data.get("incidents", [])
    except FileNotFoundError:
        st.error("sample_incidents.json not found.")
        st.stop()
    except json.JSONDecodeError as e:
        st.error(f"Could not parse sample_incidents.json: {e}")
        st.stop()

    st.markdown(
        f'<div style="color:#8b949e; font-size:13px; margin-bottom:20px;">'
        f'{len(incidents)} synthetic incidents available for loading into Hindsight memory.</div>',
        unsafe_allow_html=True,
    )

    # Show each incident with a load button
    for inc in incidents:
        with st.expander(
            f"🔹 {inc['id']} — {inc['service']} — {inc['severity']} — {inc['environment']}",
            expanded=False,
        ):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"**Service:** {inc['service']}")
                st.markdown(f"**Severity:** {inc['severity']} | **Environment:** {inc['environment']}")
                st.markdown(f"**Error:**")
                st.code(inc['error'], language="text")
                st.markdown(f"**Root Cause:** {inc['root_cause']}")
                st.markdown(f"**Resolution:** {inc['resolution']}")
                st.markdown(f"**Resolution Time:** {inc['resolution_time']}")
            with col_b:
                btn_key = f"load_{inc['id']}"
                if st.button(f"💾 Load into\nHindsight", key=btn_key, use_container_width=True):
                    with st.spinner(f"Storing {inc['id']} in Hindsight..."):
                        result = hs.retain_postmortem(
                            service=inc["service"],
                            error=inc["error"],
                            severity=inc["severity"],
                            environment=inc["environment"],
                            recent_changes=inc.get("recent_changes", ""),
                            root_cause=inc["root_cause"],
                            resolution=inc["resolution"],
                            resolution_time=inc["resolution_time"],
                        )
                    if result["success"]:
                        st.success(f"✅ {inc['id']} stored!")
                        st.session_state.incidents_resolved += 1
                    else:
                        st.error(f"❌ {result['message']}")

    st.markdown("---")

    # Load ALL button
    st.markdown(
        '<div class="section-title">Bulk Load</div>',
        unsafe_allow_html=True,
    )
    if st.button("💾 Load ALL Sample Incidents into Hindsight", use_container_width=True):
        progress_bar = st.progress(0)
        status_text  = st.empty()
        loaded = 0
        failed = 0
        for i, inc in enumerate(incidents):
            status_text.text(f"Loading {inc['id']} ({i+1}/{len(incidents)})...")
            result = hs.retain_postmortem(
                service=inc["service"],
                error=inc["error"],
                severity=inc["severity"],
                environment=inc["environment"],
                recent_changes=inc.get("recent_changes", ""),
                root_cause=inc["root_cause"],
                resolution=inc["resolution"],
                resolution_time=inc["resolution_time"],
            )
            if result["success"]:
                loaded += 1
            else:
                failed += 1
            progress_bar.progress((i + 1) / len(incidents))
            time.sleep(0.3)   # small delay to avoid rate limiting

        status_text.empty()
        if loaded > 0:
            st.markdown(
                f'<div class="success-box">'
                f'✅ Successfully loaded {loaded}/{len(incidents)} incidents into Hindsight memory.<br>'
                f'🧠 IncidentMind now has historical knowledge of these incident patterns.'
                f'{"<br>⚠️ " + str(failed) + " incidents failed to load." if failed else ""}'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.session_state.incidents_resolved += loaded
        else:
            st.markdown(
                f'<div class="error-box">❌ Failed to load any incidents. Check your Hindsight connection.</div>',
                unsafe_allow_html=True,
            )

    st.markdown("""
    <div style="background:#161b22; border:1px solid #21262d; border-radius:10px; padding:20px; margin-top:24px;">
    <div style="font-size:14px; font-weight:700; color:#e6edf3; margin-bottom:12px;">🎯 Demo Scenario After Loading</div>
    <div style="color:#c9d1d9; font-size:13px; line-height:1.8;">
    <strong style="color:#58a6ff;">Step 1:</strong> Load sample incidents above (or use Bulk Load)<br>
    <strong style="color:#58a6ff;">Step 2:</strong> Go to <strong>🚨 New Incident</strong><br>
    <strong style="color:#58a6ff;">Step 3:</strong> Enter:<br>
    &nbsp;&nbsp;&nbsp;• Service: <code>Payment API</code><br>
    &nbsp;&nbsp;&nbsp;• Error: <code>Database connection timeout, too many clients</code><br>
    &nbsp;&nbsp;&nbsp;• Severity: <code>Critical</code> | Environment: <code>Production</code><br>
    <strong style="color:#58a6ff;">Step 4:</strong> Click <strong>Analyze Incident</strong><br>
    <strong style="color:#3fb950;">Result:</strong> Hindsight will recall INC-001 (connection pool exhaustion) and the AI
    will use that historical evidence in its recommendation.
    </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: ABOUT
# ─────────────────────────────────────────────────────────────────────────────

elif page == "ℹ️ About":
    st.markdown(
        '<div class="section-title">ℹ️ About IncidentMind AI</div>',
        unsafe_allow_html=True,
    )

    st.markdown("""
    <div class="card">
    <div class="card-header">🎯 What Is IncidentMind AI?</div>
    <p>
    IncidentMind AI is an AI-powered incident response agent that gives software engineers
    a persistent, learning memory for production incidents. Unlike a simple chatbot, it uses
    <strong>Hindsight</strong> — a structured agent memory system — to store and recall real
    postmortems across sessions.
    </p>
    <p>
    Every time an incident is resolved, its postmortem is stored in Hindsight. The next time
    a similar incident occurs, IncidentMind retrieves the historical experience and uses it
    — together with Groq's LLM — to generate a grounded, evidence-based analysis.
    </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="card">
    <div class="card-header">🔄 Core Workflow</div>
    <pre style="color:#c9d1d9; font-size:13px; background:#0d1117; padding:16px; border-radius:6px; line-height:1.8;">
New Incident Reported
        ↓
Hindsight RECALL
→ Search persistent memory for similar past incidents
        ↓
Historical Evidence Retrieved
→ Postmortems with root causes, resolutions, timelines
        ↓
Groq LLM Analysis
→ Current incident + historical evidence → structured analysis
        ↓
Engineer Investigates & Resolves
        ↓
Postmortem Recorded
→ Root cause, resolution, timeline
        ↓
Hindsight RETAIN
→ Store postmortem in persistent memory
        ↓
Future incidents benefit from this experience
    </pre>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="card">
    <div class="card-header">🧠 How Hindsight Is Used</div>
    <table style="width:100%; border-collapse:collapse; font-size:13px;">
    <tr style="border-bottom:1px solid #21262d;">
        <td style="padding:10px 12px; color:#58a6ff; font-weight:700; width:120px;">RETAIN</td>
        <td style="padding:10px 12px; color:#c9d1d9;">
        After a resolved incident, the full postmortem (service, error, root cause, resolution,
        resolution time) is stored in Hindsight. Hindsight extracts structured facts and indexes
        them for semantic retrieval.
        </td>
    </tr>
    <tr>
        <td style="padding:10px 12px; color:#3fb950; font-weight:700;">RECALL</td>
        <td style="padding:10px 12px; color:#c9d1d9;">
        When a new incident is reported, a semantic search query is built from the incident details
        and sent to Hindsight. It returns the most relevant historical postmortems, which are then
        passed to the LLM as grounded historical evidence.
        </td>
    </tr>
    </table>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="card">
        <div class="card-header">🛠️ Tech Stack</div>
        <ul style="color:#c9d1d9; font-size:13px; line-height:2;">
            <li><strong style="color:#e6edf3;">Streamlit</strong> — Web UI</li>
            <li><strong style="color:#e6edf3;">Hindsight</strong> — Persistent memory (hindsight-client)</li>
            <li><strong style="color:#e6edf3;">Groq</strong> — LLM API (llama-3.3-70b-versatile)</li>
            <li><strong style="color:#e6edf3;">Python</strong> — Backend logic</li>
            <li><strong style="color:#e6edf3;">python-dotenv</strong> — Environment config</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="card">
        <div class="card-header">🚀 Future Scope</div>
        <ul style="color:#c9d1d9; font-size:13px; line-height:2;">
            <li>Automatic log ingestion from CloudWatch / Datadog</li>
            <li>Slack / Teams alert integration</li>
            <li>Jira / PagerDuty ticket creation</li>
            <li>Automatic postmortem generation</li>
            <li>Runbook integration and auto-remediation</li>
            <li>Multi-team memory banks</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
