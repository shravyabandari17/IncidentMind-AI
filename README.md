# 🧠 IncidentMind AI

### AI-Powered Incident Response Agent with Persistent Memory

> Built with **Hindsight** (persistent memory) · **Groq** (LLM) · **Streamlit** (UI)

---

## 🚨 The Problem

Every engineering team has been here:

- A production incident fires at 2 AM
- The on-call engineer spends 45 minutes debugging — only to discover it was the **same root cause** as an incident six months ago
- That postmortem was written, shared in Slack, and then **forgotten**
- The fix was known. The knowledge was lost.

Repeated incidents waste hours, erode trust, and burn out engineers. The root cause isn't always bad code — it's **institutional amnesia**. Teams lose operational knowledge every time someone leaves, every time a postmortem gets buried in Confluence, every time an incident is resolved without being truly learned from.

---

## 💡 The Solution

**IncidentMind AI** gives your incident response workflow a **persistent, learning memory**.

When a new incident occurs, IncidentMind:
1. **Searches Hindsight** for similar historical incidents your team has resolved before
2. **Retrieves real postmortems** — root causes, resolutions, and timelines — as grounded evidence
3. **Sends everything to a Groq LLM** for a structured, evidence-based analysis
4. **Recommends specific actions** rooted in what actually worked before — not generic advice

When an incident is resolved, IncidentMind:
1. **Records the postmortem** (root cause, resolution, timeline)
2. **Stores it in Hindsight** so the next engineer facing a similar incident gets the benefit of this experience immediately

The system **gets smarter with every incident resolved**.

---

## 🏗️ Architecture

```
Engineer Reports Incident
          ↓
    Streamlit UI
          ↓
  Hindsight RECALL
  ─────────────────
  Search persistent memory
  for similar past incidents
          ↓
  Historical Incidents
  ─────────────────────
  Real postmortems with
  root causes & resolutions
          ↓
      Groq LLM
  ─────────────────
  Current incident +
  historical evidence
  → structured analysis
          ↓
  Analysis & Recommendations
  ──────────────────────────
  • Incident Summary
  • Possible Root Cause
  • Evidence from History
  • Investigation Steps
  • Recommended Resolution
  • Confidence Level
          ↓
  Engineer Resolves Incident
          ↓
  Postmortem Recorded
  ────────────────────
  Root cause, resolution,
  resolution time
          ↓
  Hindsight RETAIN
  ─────────────────
  Postmortem stored in
  persistent memory
          ↓
  Future incidents benefit
  from this experience ✅
```

---

## 🧠 How Hindsight Is Used

Hindsight is the **core memory engine** of IncidentMind AI — not an optional database. It gives the application true persistence and learning across sessions.

### RETAIN — Storing Memories

After every resolved incident, the full postmortem is stored in Hindsight:

```python
client.retain(
    bank_id="incidentmind-ai",
    content=postmortem_text,        # structured postmortem document
    context="incident postmortem",  # contextual label
    metadata={                      # structured metadata
        "service": "Payment API",
        "severity": "Critical",
        "root_cause": "Connection pool exhaustion",
        ...
    }
)
```

Hindsight extracts structured facts from the postmortem text and indexes them for semantic retrieval. The raw text is never stored verbatim — Hindsight builds a knowledge graph of the incident.

### RECALL — Retrieving Memories

When a new incident is reported, a semantic search query is built from the incident details and sent to Hindsight:

```python
result = client.recall(
    bank_id="incidentmind-ai",
    query="Service: Payment API. Error: database connection timeout. Severity: Critical...",
    budget="mid",
    max_tokens=4096,
)
for memory in result.results:
    print(memory.text)   # relevant historical postmortem facts
```

Hindsight uses multi-strategy retrieval to find semantically similar incidents — even if the exact wording differs. The retrieved memories are then passed to the LLM as grounded historical evidence.

### Why This Matters

Without Hindsight:
- Every incident is analyzed in isolation
- The LLM can only reason from generic SRE knowledge
- Recommendations are generic, not specific to your system's history

With Hindsight:
- The LLM receives **real evidence** from your team's past incidents
- Recommendations are grounded in **what actually worked before**
- The system improves with every incident resolved

---

## ✨ Features

| Feature | Description |
|---|---|
| 🚨 Incident Form | Report incidents with service, error, severity, environment, recent changes |
| 🧠 Hindsight Recall | Semantic search of historical incident memory on every analysis |
| 🤖 AI Analysis | Structured Groq LLM analysis grounded in historical evidence |
| 📝 Postmortem Recording | Capture root cause, resolution, and timeline |
| 💾 Hindsight Retain | Store postmortems persistently for future recall |
| 📚 Sample Data Loader | Load 8 realistic synthetic incidents into memory for demo |
| 🎨 SRE Dashboard UI | Professional dark-theme dashboard with cards, badges, and status indicators |
| 📊 Session Stats | Track incidents analyzed, memories retrieved, incidents resolved |
| 🔌 System Status | Live Hindsight and Groq connectivity indicators in sidebar |

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Web UI | [Streamlit](https://streamlit.io) |
| Persistent Memory | [Hindsight](https://hindsight.vectorize.io) via `hindsight-client` |
| LLM | [Groq](https://console.groq.com) — `llama-3.3-70b-versatile` |
| Language | Python 3.9+ |
| Config | `python-dotenv` |

---

## 📁 Project Structure

```
IncidentMind-AI/
│
├── app.py                  # Main Streamlit application (UI + workflow)
├── hindsight_service.py    # Hindsight RECALL and RETAIN functions
├── ai_service.py           # Groq LLM analysis and prompt engineering
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .gitignore              # Git ignore rules
├── README.md               # This file
└── sample_incidents.json   # 8 synthetic demo incidents
```

---

## ⚙️ Installation

### Prerequisites

- Python 3.9 or higher
- A [Hindsight](https://hindsight.vectorize.io) account and API key
- A [Groq](https://console.groq.com) account and API key

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/incidentmind-ai.git
cd incidentmind-ai
```

### 2. Create a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your API keys (see **Environment Variables** below).

---

## 🔑 Environment Variables

Copy `.env.example` to `.env` and set the following:

| Variable | Description | Where to Get It |
|---|---|---|
| `HINDSIGHT_API_KEY` | Your Hindsight API key | [hindsight.vectorize.io](https://hindsight.vectorize.io) → Settings → API Keys |
| `HINDSIGHT_BASE_URL` | Hindsight API base URL | Leave as `https://api.hindsight.vectorize.io` |
| `HINDSIGHT_BANK_ID` | Memory bank identifier | Leave as `incidentmind-ai` (created automatically) |
| `GROQ_API_KEY` | Your Groq API key | [console.groq.com](https://console.groq.com) → API Keys |
| `GROQ_MODEL` | Groq model to use | Leave as `llama-3.3-70b-versatile` |

```env
HINDSIGHT_API_KEY=your_hindsight_api_key_here
HINDSIGHT_BASE_URL=https://api.hindsight.vectorize.io
HINDSIGHT_BANK_ID=incidentmind-ai
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

> ⚠️ **Never commit your `.env` file.** It is listed in `.gitignore`.

---

## 🚀 Running the Application

```bash
streamlit run app.py
```

The app will open at **http://localhost:8501**

Check the sidebar for:
- 🟢 **Hindsight Memory** — connected
- 🟢 **Groq LLM** — connected

If either shows 🔴, check your `.env` file and API keys.

---

## 🧪 Testing Hindsight

### Verify RETAIN works

1. Go to **📚 Sample Data Loader** in the sidebar
2. Click **"💾 Load ALL Sample Incidents into Hindsight"**
3. Watch the progress bar — all 8 incidents should load successfully
4. You should see: _"Successfully loaded 8/8 incidents into Hindsight memory"_

### Verify RECALL works

1. Go to **🚨 New Incident**
2. Fill in:
   - Service: `Authentication API`
   - Error: `Redis connection refused, session store unavailable`
   - Severity: `High`
   - Environment: `Production`
3. Click **Analyze Incident**
4. The **🧠 Hindsight Memory** section should show at least 1 historical memory about the Redis incident (INC-002)

---

## 🎬 Demo Scenario: Learning From History

This demo shows the core value of IncidentMind AI — the before/after learning behavior.

### First Incident (no memory yet)

1. **Go to** 🚨 New Incident
2. **Fill in:**
   - Service: `Payment API`
   - Error: `Database connection timeout, too many clients already`
   - Severity: `Critical`
   - Environment: `Production`
   - Recent Changes: `Deployed v2.4.1 with new bulk payment endpoint`
3. **Click Analyze Incident**
4. **Observe:** Hindsight finds **no historical memories** (first occurrence)
5. The AI provides analysis based on general SRE knowledge only

### Record the Postmortem

6. **Scroll down** to 📝 Record Resolution
7. **Fill in:**
   - Root Cause: `Connection pool exhaustion — new bulk endpoint opened multiple concurrent DB connections without releasing them`
   - Resolution: `Increased database connection pool from 50 to 100, added connection timeout of 5s, deployed hotfix`
   - Resolution Time: `47 minutes`
8. **Click** 💾 Save Postmortem to Hindsight
9. **See:** ✅ Postmortem successfully stored in Hindsight

### Second Similar Incident (memory now available)

10. **Submit a new incident:**
    - Service: `Payment API`
    - Error: `Database connection timeout after 30000ms, connection pool exhausted`
    - Severity: `Critical`
    - Environment: `Production`
11. **Click Analyze Incident**
12. **Observe:**
    - Hindsight returns **1+ historical memory** about the connection pool exhaustion
    - The AI's **Evidence From Previous Incidents** section references the specific historical resolution
    - The recommendation explicitly suggests checking connection pool settings

This before/after behavior demonstrates that **IncidentMind gets smarter with every incident resolved**.

---

## 🔮 Future Scope

| Feature | Description |
|---|---|
| 📥 Log Ingestion | Automatically ingest logs from CloudWatch, Datadog, or ELK |
| 💬 Slack / Teams | Receive incident alerts and respond directly from chat |
| 🎫 Jira / PagerDuty | Auto-create tickets and link postmortems |
| 📋 Auto-Postmortem | Generate draft postmortems automatically after resolution |
| 📖 Runbook Integration | Attach and trigger runbooks from incident analysis |
| 👥 Multi-team Banks | Separate Hindsight memory banks per team or service |
| 📈 Trend Analysis | Identify recurring incident patterns over time |
| 🔔 Proactive Alerts | "This change pattern has caused incidents before" warnings |

---

## 🙏 Built With

- [Streamlit](https://streamlit.io) — The fastest way to build data apps in Python
- [Hindsight](https://hindsight.vectorize.io) — Agent memory that learns
- [Groq](https://groq.com) — Ultra-fast LLM inference
- [python-dotenv](https://github.com/theskumar/python-dotenv) — Environment variable management

---

*IncidentMind AI — Hackathon Demo Project. Sample incidents are synthetic and not based on real production systems.*
