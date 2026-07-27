"""
InsightPilot AI — CEO Briefing Service.

Composes outputs from existing pipeline services into an executive-level briefing.
No LLMs. No external APIs. No duplicated business logic — all data is consumed
from upstream service outputs passed in by the caller.

Services consumed (read-only, never re-called):
    BusinessClassifier  — domain / confidence
    AnalyticsService    — profile (row_count, missing, duplicates, columns …)
    KPIDetector         — raw KPIs with raw_value
    AnomalyDetector     — unusual_values, missing_data_warnings, duplicates, distributions
    ChartPlanner        — chart_plan (business questions, priorities)
    BusinessContextBuilder — risks, opportunities, priority_actions
"""

from __future__ import annotations

from services.business_context import BusinessContextBuilder

# ---------------------------------------------------------------------------
# Internal registries (domain-specific language, no LLM)
# ---------------------------------------------------------------------------

_DOMAIN_LABEL: dict[str, str] = {
    "sales": "Sales & Revenue",
    "marketing": "Marketing & Growth",
    "hr": "Human Resources",
    "finance": "Finance & Accounting",
    "inventory": "Inventory & Supply Chain",
    "customer_support": "Customer Support",
    "operations": "Operations",
    "healthcare": "Healthcare",
    "education": "Education",
    "telecommunications": "Telecommunications",
    "banking": "Banking & Financial Services",
    "insurance": "Insurance",
    "retail": "Retail",
    "ecommerce": "E-Commerce",
    "manufacturing": "Manufacturing",
    "supply_chain": "Supply Chain & Logistics",
    "hospitality": "Hospitality & Travel",
    "real_estate": "Real Estate",
    "energy": "Energy & Utilities",
    "government": "Government & Public Sector",
    "saas": "SaaS & Technology",
    "generic": "General Business",
}

_DOMAIN_PRIMARY_CONCERN: dict[str, str] = {
    "sales": "revenue performance and customer retention",
    "marketing": "campaign effectiveness and lead quality",
    "hr": "employee attrition and workforce planning",
    "finance": "cost variance and cash flow predictability",
    "inventory": "stockout risk and supplier reliability",
    "customer_support": "ticket resolution time and SLA compliance",
    "operations": "throughput efficiency and downtime",
    "healthcare": "patient outcomes and readmission rates",
    "education": "student retention and completion rates",
    "telecommunications": "subscriber churn and network service quality",
    "banking": "credit risk and regulatory compliance",
    "insurance": "claims accuracy and loss ratio management",
    "retail": "sales velocity and inventory turnover",
    "ecommerce": "conversion rate and cart abandonment",
    "manufacturing": "yield rate and production downtime",
    "supply_chain": "on-time delivery and supplier lead times",
    "hospitality": "occupancy rate and guest satisfaction",
    "real_estate": "occupancy and property yield",
    "energy": "consumption efficiency and grid reliability",
    "government": "service delivery performance and compliance",
    "saas": "churn rate and monthly recurring revenue growth",
    "generic": "data quality and key performance drivers",
}

_URGENCY_VERBS: dict[str, str] = {
    "Critical": "Immediate executive attention is required.",
    "High": "Priority review is recommended this week.",
    "Medium": "Action should be planned within the next sprint.",
    "Low": "No immediate action required — monitor trends.",
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class CEOBriefingService:
    """
    Builds a CEO Briefing from pre-computed analytics pipeline outputs.

    All methods are pure and deterministic — same inputs always produce
    the same output. Never modifies the passed-in dicts.
    """

    _context_builder = BusinessContextBuilder()

    def build(
        self,
        profile: dict,
        classification: dict,
        kpis: list[dict],
        anomalies: dict,
        chart_plan: list[dict],
    ) -> dict:
        """
        Return a CEO Briefing dict.

        Parameters
        ----------
        profile        : AnalyticsService.profile_dataset() output
        classification : BusinessClassifier.classify() output
        kpis           : KPIDetector.detect() output (list of dicts with raw_value)
        anomalies      : AnomalyDetector.detect() output
        chart_plan     : ChartPlanner.plan() output

        Returns
        -------
        dict matching the CeoBriefing schema
        """
        domain = classification.get("domain", "generic")
        confidence = int(round(classification.get("confidence", 0)))

        # Pull reusable outputs from BusinessContextBuilder (avoids duplication)
        ctx = self._context_builder.build(
            profile=profile,
            domain=domain,
            classification=classification,
            kpis=kpis,
            anomalies=anomalies,
            chart_plan=chart_plan,
        )
        risks: list[str] = ctx["risks"]
        opportunities: list[str] = ctx["opportunities"]
        priority_actions: list[dict] = ctx["priority_actions"]
        quality_score: int = ctx["dataset_quality_score"]

        health = self._overall_health(profile, anomalies, kpis)
        urgency = self._urgency(health["score"], profile, anomalies, kpis)
        biggest_risk = self._biggest_risk(domain, risks, anomalies, profile)
        top_opportunity = self._top_opportunity(domain, opportunities, kpis, chart_plan)
        priority_action = self._priority_action(priority_actions, anomalies, profile, domain)
        executive_summary = self._executive_summary(
            profile, domain, classification, kpis, anomalies, health, urgency
        )
        key_takeaways = self._key_takeaways(
            domain, health, kpis, anomalies, biggest_risk, top_opportunity, urgency
        )

        return {
            "business_domain": _DOMAIN_LABEL.get(domain, domain.replace("_", " ").title()),
            "confidence": confidence,
            "overall_health": health,
            "urgency": urgency,
            "biggest_risk": biggest_risk,
            "top_opportunity": top_opportunity,
            "priority_action": priority_action,
            "executive_summary": executive_summary,
            "key_takeaways": key_takeaways,
        }

    # ------------------------------------------------------------------
    # 1. Overall health score (0-100) with weighted factors
    # ------------------------------------------------------------------

    def _overall_health(self, profile: dict, anomalies: dict, kpis: list[dict]) -> dict:
        """
        Weighted health score:
          25%  Missing values
          20%  Duplicate rows
          20%  Anomaly severity
          20%  Data completeness (numeric column coverage)
          15%  Business KPI quality
        """
        rows = max(profile.get("row_count", 1), 1)
        total_cols = max(profile.get("column_count", 1), 1)
        numeric_cols = profile.get("numeric_columns", [])
        total_cells = rows * total_cols

        # --- 25%: Missing values (lower missing → higher score) ---
        missing_pct = profile.get("total_missing_values", 0) / max(total_cells, 1)
        missing_score = max(0.0, 1.0 - missing_pct * 4)  # 25% missing → score=0
        missing_component = 25.0 * missing_score

        # --- 20%: Duplicate rows (fewer dupes → higher score) ---
        dup_rate = profile.get("duplicate_rows", 0) / rows
        dup_score = max(0.0, 1.0 - dup_rate * 5)  # 20% dupes → score=0
        dup_component = 20.0 * dup_score

        # --- 20%: Anomaly severity (fewer/lower severity → higher score) ---
        unusual = anomalies.get("unusual_values", [])
        high_count = sum(1 for u in unusual if u.get("severity") == "high")
        med_count = sum(1 for u in unusual if u.get("severity") == "medium")
        anomaly_penalty = min(1.0, (high_count * 0.15 + med_count * 0.06))
        anomaly_score = max(0.0, 1.0 - anomaly_penalty)
        anomaly_component = 20.0 * anomaly_score

        # --- 20%: Data completeness (numeric column coverage) ---
        numeric_ratio = len(numeric_cols) / total_cols
        # Penalise for very small datasets too
        size_factor = min(1.0, rows / 100) if rows < 100 else 1.0
        completeness_score = numeric_ratio * size_factor
        completeness_component = 20.0 * min(1.0, completeness_score * 2)

        # --- 15%: Business KPI quality (non-zero KPI hit rate) ---
        if kpis:
            kpi_hits = sum(1 for k in kpis if k.get("raw_value", 0) > 0)
            kpi_rate = kpi_hits / len(kpis)
        else:
            kpi_rate = 0.0
        kpi_component = 15.0 * kpi_rate

        raw = missing_component + dup_component + anomaly_component + completeness_component + kpi_component
        score = max(0, min(100, round(raw)))

        # Map score to status
        if score >= 90:
            status = "Excellent"
        elif score >= 75:
            status = "Healthy"
        elif score >= 60:
            status = "Needs Attention"
        elif score >= 40:
            status = "At Risk"
        else:
            status = "Critical"

        return {"score": score, "status": status}

    # ------------------------------------------------------------------
    # 2. Urgency
    # ------------------------------------------------------------------

    def _urgency(
        self,
        health_score: int,
        profile: dict,
        anomalies: dict,
        kpis: list[dict],
    ) -> str:
        rows = max(profile.get("row_count", 1), 1)
        total_cells = rows * max(profile.get("column_count", 1), 1)
        missing_pct = profile.get("total_missing_values", 0) / max(total_cells, 1) * 100
        dup_pct = profile.get("duplicate_rows", 0) / rows * 100

        unusual = anomalies.get("unusual_values", [])
        high_outliers = sum(1 for u in unusual if u.get("severity") == "high")
        missing_warnings = anomalies.get("missing_data_warnings", [])
        high_missing_cols = sum(1 for w in missing_warnings if w.get("severity") == "high")

        # Critical
        if health_score < 40 or missing_pct > 30 or high_outliers >= 4:
            return "Critical"

        # High
        if (
            health_score < 60
            or missing_pct > 15
            or dup_pct > 15
            or high_outliers >= 2
            or high_missing_cols >= 2
        ):
            return "High"

        # Medium
        if (
            health_score < 75
            or missing_pct > 5
            or dup_pct > 5
            or high_outliers >= 1
            or high_missing_cols >= 1
        ):
            return "Medium"

        return "Low"

    # ------------------------------------------------------------------
    # 3. Biggest risk (one sentence, plain language)
    # ------------------------------------------------------------------

    def _biggest_risk(
        self,
        domain: str,
        risks: list[str],
        anomalies: dict,
        profile: dict,
    ) -> str:
        # Prefer a risk that's grounded in detected anomalies
        rows = max(profile.get("row_count", 1), 1)
        total_cells = rows * max(profile.get("column_count", 1), 1)
        missing_pct = profile.get("total_missing_values", 0) / max(total_cells, 1) * 100
        dup_count = profile.get("duplicate_rows", 0)
        dup_pct = dup_count / rows * 100

        unusual = anomalies.get("unusual_values", [])
        high_outliers = [u for u in unusual if u.get("severity") == "high"]
        missing_warnings = anomalies.get("missing_data_warnings", [])
        high_missing = [w for w in missing_warnings if w.get("severity") == "high"]

        # Most severe issue first
        if missing_pct > 20:
            return (
                f"Severe data gaps ({missing_pct:.0f}% of cells missing) risk producing "
                "misleading conclusions that could drive poor decisions."
            )

        if dup_pct > 15:
            return (
                f"Duplicate records ({dup_pct:.0f}% of rows) will inflate aggregates "
                "and distort any KPI or trend analysis derived from this dataset."
            )

        if high_outliers:
            cols = " and ".join(u["column"] for u in high_outliers[:2])
            return (
                f"Extreme outliers in {cols} are likely to skew averages, "
                "masking true business performance from decision-makers."
            )

        if high_missing:
            col = high_missing[0]["column"]
            rate = high_missing[0].get("missing_rate", "?")
            return (
                f"The '{col}' column ({rate}% missing) is a key dimension with "
                "insufficient data to support reliable analysis."
            )

        # Fall back to the first risk from BusinessContextBuilder
        if risks:
            # Trim technical language for executive reading
            r = risks[0]
            # Remove trailing parenthetical technical phrases
            if " — " in r:
                r = r.split(" — ")[0] + "."
            return r

        return "No material data risks were detected in this dataset."

    # ------------------------------------------------------------------
    # 4. Top opportunity (one actionable sentence)
    # ------------------------------------------------------------------

    def _top_opportunity(
        self,
        domain: str,
        opportunities: list[str],
        kpis: list[dict],
        chart_plan: list[dict],
    ) -> str:
        # If we have chart-plan business questions, surface the highest-priority one
        if chart_plan:
            top_chart = sorted(chart_plan, key=lambda c: c.get("priority", 0), reverse=True)
            best = top_chart[0]
            bq = best.get("business_question", "")
            if bq:
                # Convert question to opportunity statement
                action = _question_to_opportunity(bq, domain)
                if action:
                    return action

        # Fall back to domain opportunity list
        if opportunities:
            return opportunities[0]

        return "Establish baseline KPI benchmarks to enable data-driven performance tracking."

    # ------------------------------------------------------------------
    # 5. Priority action (exactly one, begins with action verb)
    # ------------------------------------------------------------------

    def _priority_action(
        self,
        priority_actions: list[dict],
        anomalies: dict,
        profile: dict,
        domain: str,
    ) -> str:
        # Use highest-priority action from BusinessContextBuilder
        if priority_actions:
            high = [a for a in priority_actions if a.get("priority") == "High"]
            chosen = (high or priority_actions)[0]
            title = chosen.get("title", "")
            # Ensure it starts with an action verb
            if title and not _starts_with_verb(title):
                title = "Review " + title[0].lower() + title[1:]
            if title:
                return title

        # Construct from anomalies
        missing_warnings = anomalies.get("missing_data_warnings", [])
        unusual = anomalies.get("unusual_values", [])
        dup_count = profile.get("duplicate_rows", 0)

        if dup_count > 0:
            return f"Deduplicate the dataset to ensure accurate reporting across all KPIs."
        if missing_warnings:
            col = missing_warnings[0]["column"]
            return f"Investigate and remediate missing values in '{col}' before drawing conclusions."
        if unusual:
            col = unusual[0]["column"]
            return f"Investigate outliers in '{col}' to confirm whether they represent data errors."

        concern = _DOMAIN_PRIMARY_CONCERN.get(domain, "key performance drivers")
        return f"Establish a regular review cadence for {concern} to track progress over time."

    # ------------------------------------------------------------------
    # 6. Executive summary (3-5 sentences)
    # ------------------------------------------------------------------

    def _executive_summary(
        self,
        profile: dict,
        domain: str,
        classification: dict,
        kpis: list[dict],
        anomalies: dict,
        health: dict,
        urgency: str,
    ) -> str:
        domain_label = _DOMAIN_LABEL.get(domain, domain.replace("_", " ").title())
        rows = profile.get("row_count", 0)
        cols = profile.get("column_count", 0)
        confidence = int(round(classification.get("confidence", 0)))
        health_score = health["score"]
        health_status = health["status"]

        parts: list[str] = []

        # Sentence 1: domain + scale
        parts.append(
            f"This dataset represents a {domain_label} operation, "
            f"comprising {rows:,} records across {cols} dimensions "
            f"(classified with {confidence}% confidence)."
        )

        # Sentence 2: health verdict
        parts.append(
            f"Overall data quality scores {health_score}/100, rated {health_status}."
        )

        # Sentence 3: KPI highlight or data gap
        healthy_kpis = [k for k in kpis if k.get("raw_value", 0) > 0]
        if healthy_kpis:
            top = healthy_kpis[0]
            parts.append(
                f"Key business metrics are measurable, with {top['label']} "
                f"recorded at {top['value']}."
            )
        else:
            total_cells = rows * max(cols, 1)
            missing_pct = profile.get("total_missing_values", 0) / max(total_cells, 1) * 100
            if missing_pct > 5:
                parts.append(
                    f"Data completeness constraints ({missing_pct:.0f}% of values missing) "
                    "limit the reliability of quantitative KPI computation."
                )
            else:
                parts.append(
                    "The dataset's column structure does not align strongly with "
                    f"standard {domain_label.lower()} KPIs — custom metric definitions may be required."
                )

        # Sentence 4: urgency framing
        parts.append(_URGENCY_VERBS.get(urgency, "Monitor the dataset for emerging issues."))

        # Sentence 5: forward-looking (only if space and health isn't perfect)
        concern = _DOMAIN_PRIMARY_CONCERN.get(domain, "performance")
        parts.append(
            f"Management should prioritise {concern} as the primary focus area "
            "for the next analytical cycle."
        )

        return " ".join(parts)

    # ------------------------------------------------------------------
    # 7. Key takeaways (exactly 3)
    # ------------------------------------------------------------------

    def _key_takeaways(
        self,
        domain: str,
        health: dict,
        kpis: list[dict],
        anomalies: dict,
        biggest_risk: str,
        top_opportunity: str,
        urgency: str,
    ) -> list[str]:
        takeaways: list[str] = []

        # Takeaway 1: health + urgency
        score = health["score"]
        status = health["status"]
        if score >= 75:
            takeaways.append(
                f"Data health is {status.lower()} ({score}/100) — analytics findings are reliable."
            )
        else:
            takeaways.append(
                f"Data health is {status.lower()} ({score}/100) — address quality issues before acting on findings."
            )

        # Takeaway 2: biggest risk (shortened)
        risk_short = biggest_risk.split(".")[0] + "."
        if len(risk_short) > 100:
            risk_short = risk_short[:97] + "…"
        takeaways.append(f"Top risk: {risk_short}")

        # Takeaway 3: top opportunity (shortened)
        opp_short = top_opportunity.split(".")[0] + "."
        if len(opp_short) > 100:
            opp_short = opp_short[:97] + "…"
        takeaways.append(f"Best opportunity: {opp_short}")

        return takeaways[:3]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ACTION_VERBS = {
    "investigate", "increase", "reduce", "optimise", "optimize", "review",
    "deduplicate", "address", "improve", "expand", "focus", "build",
    "identify", "implement", "establish", "define", "resolve", "monitor",
}


def _starts_with_verb(text: str) -> bool:
    first = text.split()[0].lower().rstrip(".,;:") if text.split() else ""
    return first in _ACTION_VERBS


def _question_to_opportunity(question: str, domain: str) -> str:
    """Convert a chart business question into an opportunity statement."""
    q = question.strip().rstrip("?")
    # Common transforms
    replacements = [
        ("Which ", "Focus on "),
        ("What is the trend in ", "Track trends in "),
        ("Where are ", "Investigate "),
        ("What drives ", "Understand what drives "),
        ("How does ", "Analyse how "),
        ("Who has ", "Identify who has "),
    ]
    for prefix, replacement in replacements:
        if q.startswith(prefix):
            transformed = replacement + q[len(prefix):].lower()
            return transformed.rstrip(".") + "."
    # Generic fallback
    return f"Explore: {q.lower()}."
