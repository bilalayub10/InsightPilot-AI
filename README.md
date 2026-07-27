# InsightPilot AI

**Autonomous business analytics platform — upload a spreadsheet, get an executive-level intelligence report in under 30 seconds, with zero configuration.**

🔗 **Live App:** [https://insight-pilot-ai--bilalayub0010.replit.app](https://insight-pilot-ai--bilalayub0010.replit.app)

---

## Table of Contents

- [What It Does & Why](#what-it-does--why)
- [Live Demo](#live-demo)
- [Features](#features)
- [The AI Feature](#the-ai-feature)
- [Screenshots](#screenshots)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [How to Run It Locally](#how-to-run-it-locally)
- [API Reference](#api-reference)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)
- [License](#license)

---

## What It Does & Why

Every business generates data. Almost none of them can turn that data into a decision quickly. Getting from a raw CSV export to something a CEO can act on normally takes an analyst 1–5 days: profiling the file, building charts by hand, writing an executive summary, going through review rounds.

**InsightPilot AI compresses that entire pipeline into under 30 seconds.** You upload a CSV or Excel file. The platform automatically:

1. Detects what kind of business data it is (sales, HR, finance, healthcare, and 17 other domains) — from the column names alone
2. Extracts the KPIs that actually matter for that domain
3. Picks and renders the 4 highest-value charts, each with a business question attached
4. Flags statistical anomalies and data quality issues (outliers, missing data, duplicates, skew)
5. Writes an AI-generated executive summary, a CEO briefing with a health score, and a plain-English explanation for every chart
6. Answers natural-language follow-up questions about the data through a conversational Copilot
7. Packages the whole thing into a downloadable, board-ready PDF report

**Who it's for:** executives who need a decision without waiting on an analyst; business/data/BI analysts who are tired of spending 60–80% of their time on mechanical profiling and charting instead of interpretation; operations managers who rebuild the same monthly report from a spreadsheet every cycle.

**Why it's different from Excel/Power BI:** those tools have zero business-domain awareness and require manual setup — schema mapping, DAX, dashboard configuration, hours to days before you see anything. InsightPilot needs none of that. Upload and go.

---

## Live Demo

**URL:** [https://insight-pilot-ai--bilalayub0010.replit.app](https://insight-pilot-ai--bilalayub0010.replit.app)

> Open the link, upload any CSV or Excel file (a sample sales/HR/finance file works well), and the dashboard, KPIs, charts, CEO briefing, and AI Copilot will populate automatically. No login required.

---

## Features

- 🧠 **Autonomous domain classification** — detects 1 of 21 business domains (Sales, Marketing, Finance, HR, Operations, Inventory, Customer Support, Healthcare, Education, Telecom, Banking, Insurance, Retail, E-commerce, Manufacturing, Supply Chain, Hospitality, Real Estate, Energy, Government, SaaS) from column names alone, using a four-tier weighted keyword classifier — no ML model, no LLM call, sub-millisecond
- 📊 **Domain-aware KPI detection** — computes 4 relevant KPIs (e.g. Total Revenue, Avg Order Value for Sales; Headcount, Attrition for HR) directly from real data values, with correct currency/percent/integer formatting
- 📈 **Intelligent chart planning** — selects up to 4 charts (line, bar, pie, histogram, scatter) using semantic column scoring, each labeled with the business question it answers
- 🚨 **Data quality / anomaly detection** — IQR and Z-score outlier detection, missing-value severity scoring, duplicate-row detection, skewness analysis with severity ratings (low/medium/high)
- 💼 **CEO Briefing** — a fully deterministic (no-LLM) one-pager: 0–100 business health score, urgency level, biggest risk, top opportunity, priority action, and a 4–5 sentence executive summary
- 🤖 **AI Chart Insights** — every chart gets a 4-part AI-written explanation (title, summary, business impact, recommendation)
- 🗣️ **AI Copilot** — ask natural-language questions about your specific dataset ("why did revenue drop in Q3?") and get an evidence-grounded answer with a confidence score and 3 suggested follow-ups
- 📄 **Executive PDF Report** — a professionally designed, downloadable A4 report (cover page, KPI dashboard, rendered charts with AI insight, data quality section, business context) suitable for a board meeting
- 🔄 **4-tier AI fallback** — Gemini → OpenRouter → Groq → deterministic pattern-based logic, so the app never fails even if all three AI providers are down

---

## The AI Feature

InsightPilot's core AI design decision: **raw spreadsheet data is never sent to any LLM.** Every KPI, chart data point, and anomaly is pre-computed deterministically with pandas first. The LLM only ever receives a structured JSON summary (KPI labels/values, chart titles and business questions, anomaly descriptions, domain classification) — never raw rows. Its job is interpretation and language, not calculation, which is what stops it from hallucinating numbers.

**Provider chain:** Google Gemini (`gemini-2.0-flash`) is tried first. On failure, it falls back to OpenRouter (`google/gemini-2.5-flash`), then to Groq as a third layer. If all three fail, a deterministic, pattern-based fallback (trend direction, concentration %, distribution shape, etc., computed from the real data) takes over — the app degrades gracefully instead of breaking.

The AI is used for three tasks, each with its own instructions:

**1. Chart Insights** — writes a title, summary, business impact, and one actionable recommendation per chart.
> Key rules given to the model: every sentence must be traceable to the supplied data; never invent a statistic not present in the JSON; never mention AI, Gemini, or OpenRouter by name; write in executive prose.

**2. Business Context (executive summary)** — synthesizes strengths, risks, opportunities, and priority actions from the KPI/anomaly/chart JSON.
> Key rules: "Never invent statistics, KPIs, trends, or anomalies not present in the supplied JSON." "Write like a senior McKinsey or Bain consultant." "Return VALID JSON ONLY. No markdown. No code fences."

**3. AI Copilot** — answers free-text questions about the uploaded dataset.
> System prompt persona: *"Senior Business Intelligence Consultant advising C-suite executives."*
> Key rules: answer in 3–5 sentences maximum; never invent numbers, metrics, or trends not present in the supplied context; if the information isn't available, say so explicitly; temperature 0.3 to prioritize accuracy over creativity.

Every LLM response is parsed as JSON with required keys validated; on a parse failure it's retried once per provider before falling back to the deterministic path — so a malformed AI response is never shown to the user.

---

## Screenshots

*(Add at least 3 screenshots below — recommended: the upload screen, the main dashboard with KPIs/charts, the CEO Briefing card, the AI Copilot in conversation, and a page of the generated PDF report.)*

| | |
|---|---|
| ![Upload screen](ADD_SCREENSHOT_PATH_1) *Upload screen* | ![Dashboard](ADD_SCREENSHOT_PATH_2) *KPI & chart dashboard* |
| ![CEO Briefing](ADD_SCREENSHOT_PATH_3) *CEO Briefing* | ![AI Copilot](ADD_SCREENSHOT_PATH_4) *AI Copilot Q&A* |

---

## Tech Stack

**Frontend:** React 18, TypeScript, Vite 7, Tailwind CSS 4, shadcn/ui (Radix primitives), Wouter (routing), TanStack Query, Recharts, Framer Motion

**Backend:** Python 3.12, FastAPI, Pydantic 2.10, pandas 2.2, NumPy 2.1, uvicorn, httpx

**AI:** Google Gemini (`gemini-2.0-flash`) as primary provider, OpenRouter (`google/gemini-2.5-flash`) as second fallback, Groq as third fallback, via the `google-genai` SDK

**Reporting:** ReportLab (PDF generation), matplotlib (Agg backend, chart rendering for the PDF)

**Tooling:** OpenAPI-first design with auto-generated TypeScript client via Orval, pnpm workspace monorepo

---

## Architecture

```
React (Vite frontend)  →  FastAPI backend  →  Gemini → OpenRouter → Groq → Deterministic fallback
```

**Pipeline on upload → analyze:**
1. File parsed and profiled with pandas (row/column counts, types, missing values, duplicates)
2. Business domain classified from column names (21-domain keyword scorer)
3. KPIs computed and charts planned/pre-rendered server-side for the detected domain
4. Anomalies detected (IQR/Z-score outliers, missing data, duplicates, skew)
5. All 4 chart insights generated concurrently (`asyncio.gather`) via the AI provider chain
6. CEO Briefing built deterministically from the pipeline output (no LLM)
7. Result cached; PDF report and Copilot both read from this cached analysis

---

## How to Run It Locally

**Prerequisites:** Node.js 20, Python 3.12, pnpm

```bash
# Clone the repository
git clone [ADD_YOUR_REPO_URL_HERE]
cd InsightPilot-AI

# Install JavaScript dependencies
pnpm install

# Install Python dependencies
pip install -r artifacts/insightpilot/backend/requirements.txt

# Set environment variables (create a .env file or export directly — never commit these)
export GEMINI_API_KEY=your_gemini_key
export OPENROUTER_API_KEY=your_openrouter_key   # optional fallback
export GROQ_API_KEY=your_groq_key               # optional third-tier fallback
```

**Start the backend:**
```bash
cd artifacts/insightpilot/backend
PORT=8000 uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Start the frontend (separate terminal):**
```bash
cd InsightPilot-AI
PORT=5000 BASE_PATH=/ pnpm --filter @workspace/insightpilot run dev
```

Open **http://localhost:5000**, upload a CSV or Excel file, and the analysis pipeline runs automatically.

---

## API Reference

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/healthz` | GET | Infrastructure health check |
| `/api/upload` | POST | Upload a CSV/Excel file, get dataset metadata + pre-classified domain |
| `/api/analyze` | POST | Run the full pipeline (KPIs, charts, anomalies, CEO briefing, AI insights) for a `datasetId` |
| `/api/copilot` | POST | Ask a natural-language question about a `datasetId` |
| `/api/report/{datasetId}` | GET | Download the generated PDF executive report |

Full request/response schemas are documented in the codebase (`models/schemas.py`, `lib/api-spec/openapi.yaml`).

---

## Known Limitations

- No user authentication in this version — datasets are accessible via UUID, suitable for single-user/trusted-team use, not multi-tenant production
- Uploaded files are stored on local disk with no automated cleanup/TTL
- Large datasets held in memory per-request; no persistence layer between requests

---

## Roadmap

- **v2.0:** Multi-file analysis, time-series intelligence (YoY/MoM), custom KPI definitions
- **v3.0:** Live database connectors, enterprise SSO, team workspaces
- **Long-term:** Automated recurring briefings — weekly insight delivery without a manual upload

---

## License

MIT License.

---

*Built as an individual final project — original idea, built and shipped end-to-end.*
