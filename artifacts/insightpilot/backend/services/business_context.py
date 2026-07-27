"""
InsightPilot AI — Business Context Builder.

Converts raw analytical results (profile, domain, KPIs, anomalies, charts)
into structured business intelligence using purely deterministic, rule-based
logic.  No LLMs.  No external APIs.  Pure Python.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Domain opportunity registry
# ---------------------------------------------------------------------------

_DOMAIN_OPPORTUNITIES: dict[str, list[str]] = {
    "sales": [
        "Investigate top-performing products to replicate success factors.",
        "Optimise underperforming regions with targeted campaigns or incentives.",
        "Improve conversion rates by analysing the sales funnel drop-off points.",
        "Identify high-value customer segments for upsell and cross-sell motions.",
        "Forecast demand to reduce stockouts and improve fulfilment speed.",
    ],
    "marketing": [
        "Improve campaign ROI by reallocating budget to highest-performing channels.",
        "Optimise acquisition channels using attribution analysis.",
        "A/B test ad creatives and landing pages to lift conversion rates.",
        "Reduce cost-per-lead through audience segmentation and targeting refinement.",
        "Build a retention loop by identifying users who churn early.",
    ],
    "hr": [
        "Reduce attrition by identifying at-risk employees through tenure and engagement signals.",
        "Improve retention programmes by benchmarking salary against industry data.",
        "Identify high-potential talent early to accelerate development plans.",
        "Optimise workforce planning using headcount and capacity trend data.",
        "Investigate diversity and inclusion metrics to surface structural gaps.",
    ],
    "finance": [
        "Reduce operating expenses by identifying cost categories with high variance.",
        "Improve cash flow forecasting using seasonal revenue patterns.",
        "Optimise budget allocation by comparing actuals vs. forecast by department.",
        "Identify revenue leakage through anomaly detection in transaction data.",
        "Benchmark margins against industry standards to set improvement targets.",
    ],
    "inventory": [
        "Reduce stockouts by tightening reorder-point calculations.",
        "Optimise supplier lead times to lower safety-stock requirements.",
        "Identify slow-moving SKUs for clearance or discontinuation.",
        "Improve demand forecasting accuracy to reduce overstock costs.",
        "Consolidate supplier base to negotiate better volume pricing.",
    ],
    "customer_support": [
        "Improve first-contact resolution rate to reduce ticket reopens.",
        "Reduce backlog by identifying high-volume, repetitive issue categories.",
        "Use sentiment patterns to prioritise escalation workflows.",
        "Build a self-service knowledge base for the top 10 recurring issues.",
        "Correlate SLA breaches with agent workload to optimise scheduling.",
    ],
    "operations": [
        "Improve overall equipment effectiveness (OEE) by targeting downtime root causes.",
        "Optimise throughput by identifying bottleneck stages in the process flow.",
        "Reduce cycle time through lean analysis of value-added vs. non-value-added steps.",
        "Predictively schedule maintenance using anomaly patterns in operational data.",
        "Increase capacity utilisation by balancing workload across shifts or lines.",
    ],
    "healthcare": [
        "Reduce readmission rates by identifying high-risk patient cohorts.",
        "Improve patient outcomes through early detection of deterioration signals.",
        "Optimise resource allocation by matching staffing to admission volume patterns.",
        "Streamline discharge planning to reduce average length of stay.",
        "Identify diagnosis clusters driving the highest cost of care.",
    ],
    "education": [
        "Improve student retention by identifying at-risk learners early.",
        "Optimise course offerings based on enrolment trends and completion rates.",
        "Personalise learning paths using score and attendance patterns.",
        "Benchmark grade distributions to ensure assessment fairness.",
        "Identify faculty or course factors correlated with high student performance.",
    ],
    "telecommunications": [
        "Reduce subscriber churn by identifying at-risk customer cohorts early.",
        "Improve network quality scores to drive ARPU growth.",
        "Optimise plan mix to shift customers toward higher-margin offerings.",
        "Identify geographic coverage gaps driving churn in specific regions.",
        "Reduce customer acquisition cost through targeted retention offers.",
    ],
    "banking": [
        "Reduce credit default rates through improved risk scoring models.",
        "Improve cross-sell rates by analysing product holding patterns.",
        "Identify high-value customer segments for premium product targeting.",
        "Optimise branch and digital channel mix to reduce cost-to-serve.",
        "Strengthen regulatory compliance monitoring using transaction anomaly detection.",
    ],
    "insurance": [
        "Reduce loss ratio by identifying high-risk policy segments.",
        "Improve claims processing efficiency to lower operational costs.",
        "Detect fraudulent claims using anomaly patterns in claims data.",
        "Optimise pricing by correlating risk factors with actual loss experience.",
        "Increase policy renewal rates through proactive retention outreach.",
    ],
    "retail": [
        "Increase basket size by identifying cross-category purchase patterns.",
        "Optimise store layouts using foot traffic and conversion data.",
        "Reduce markdown loss by improving demand forecasting accuracy.",
        "Identify top-performing SKUs for promotional prioritisation.",
        "Improve loyalty programme ROI by segmenting members by lifetime value.",
    ],
    "ecommerce": [
        "Reduce cart abandonment through targeted recovery campaigns.",
        "Improve product discovery by analysing search and browse patterns.",
        "Optimise pricing dynamically based on demand and competitor signals.",
        "Increase repeat purchase rate through personalised recommendations.",
        "Reduce return rates by improving product description accuracy.",
    ],
    "manufacturing": [
        "Reduce unplanned downtime through predictive maintenance scheduling.",
        "Improve overall equipment effectiveness (OEE) by targeting bottleneck stages.",
        "Reduce defect rates through statistical process control monitoring.",
        "Optimise production scheduling to improve throughput and reduce WIP.",
        "Lower material waste through yield analysis and scrap tracking.",
    ],
    "supply_chain": [
        "Improve on-time delivery rates by identifying supplier performance gaps.",
        "Reduce logistics costs through route and carrier optimisation.",
        "Shorten lead times by diversifying the supplier base for critical components.",
        "Improve demand sensing accuracy to reduce safety stock requirements.",
        "Identify high-risk single-source dependencies before disruption occurs.",
    ],
    "hospitality": [
        "Improve occupancy rates through dynamic pricing and demand forecasting.",
        "Increase guest satisfaction scores by resolving recurring service complaints.",
        "Optimise staffing levels to match seasonal demand patterns.",
        "Grow ancillary revenue by identifying upsell opportunities at check-in.",
        "Reduce no-show rates through targeted deposit and reminder strategies.",
    ],
    "real_estate": [
        "Maximise rental yield by identifying underperforming properties.",
        "Reduce vacancy rates through competitive pricing analysis.",
        "Prioritise maintenance investment using condition and cost data.",
        "Identify emerging market opportunities through transaction trend analysis.",
        "Improve tenant retention by analysing satisfaction and renewal patterns.",
    ],
    "energy": [
        "Reduce energy waste by identifying high-consumption anomalies.",
        "Improve grid reliability by predicting maintenance needs from sensor data.",
        "Optimise renewable energy output through weather-correlated scheduling.",
        "Lower cost-per-MWh by shifting demand to off-peak production windows.",
        "Improve demand forecasting accuracy to minimise reserve capacity costs.",
    ],
    "government": [
        "Improve service delivery speed by identifying process bottlenecks.",
        "Increase compliance rates through targeted enforcement prioritisation.",
        "Optimise resource allocation using demand and workload trend data.",
        "Identify underserved communities through equity analysis of service access.",
        "Reduce operational costs by automating high-volume, low-complexity workflows.",
    ],
    "saas": [
        "Reduce churn by identifying disengaged accounts before cancellation.",
        "Accelerate MRR growth by improving trial-to-paid conversion rates.",
        "Improve NPS by resolving the highest-volume product pain points.",
        "Identify expansion revenue opportunities within existing customer base.",
        "Optimise onboarding to reduce time-to-value and improve activation rates.",
    ],
    "generic": [
        "Improve data completeness to unlock richer analytical possibilities.",
        "Identify key performance drivers through correlation analysis.",
        "Establish baseline KPI benchmarks to measure future progress.",
        "Segment the dataset into meaningful groups for deeper analysis.",
        "Define data governance standards to improve long-term data quality.",
    ],
}

# ---------------------------------------------------------------------------
# Domain question registry
# ---------------------------------------------------------------------------

_DOMAIN_QUESTIONS: dict[str, list[str]] = {
    "sales": [
        "Which products generate the most revenue?",
        "Which regions are underperforming against targets?",
        "What is the trend in average order value over time?",
        "Which customer segments drive the highest lifetime value?",
        "Where are conversion rates falling below expectations?",
    ],
    "marketing": [
        "Which campaigns deliver the best return on spend?",
        "Which acquisition channels drive the most conversions?",
        "What is the average cost per lead by channel?",
        "Where is marketing budget being over-allocated?",
        "Which audience segments respond best to current messaging?",
    ],
    "hr": [
        "Which departments have the highest attrition rates?",
        "What factors correlate most strongly with employee retention?",
        "How does average salary compare across departments and tenure levels?",
        "Which teams are at risk of being critically understaffed?",
        "What is the trend in headcount over the past year?",
    ],
    "finance": [
        "Which cost categories show the highest month-over-month variance?",
        "Where is the gap between budgeted and actual expenditure largest?",
        "Which revenue streams are growing and which are declining?",
        "What is driving the change in net income this period?",
        "Which business units show the strongest margin performance?",
    ],
    "inventory": [
        "Which SKUs are at risk of stockout in the next 30 days?",
        "Which products have the highest holding cost relative to demand?",
        "Where are supplier lead times causing fulfilment delays?",
        "Which items have been static for more than 90 days?",
        "What is the optimal reorder point for high-velocity items?",
    ],
    "customer_support": [
        "Which issue categories generate the most ticket volume?",
        "Where is SLA compliance falling below agreed thresholds?",
        "Which agents or teams have the highest first-contact resolution rates?",
        "What is the average resolution time by priority level?",
        "Which customers are filing the most repeat complaints?",
    ],
    "operations": [
        "Which process stages are the primary bottlenecks?",
        "Where is downtime most concentrated across shifts or equipment?",
        "What is the trend in overall throughput over the past quarter?",
        "Which defect categories have the highest frequency?",
        "How does actual utilisation compare to planned capacity?",
    ],
    "healthcare": [
        "Which patient cohorts have the highest readmission rates?",
        "What diagnoses are associated with the longest length of stay?",
        "Where are care gaps emerging in follow-up compliance?",
        "Which departments are running above planned bed capacity?",
        "What is the trend in patient satisfaction scores over time?",
    ],
    "education": [
        "Which student cohorts are at the highest risk of dropping out?",
        "Which courses show the lowest completion and pass rates?",
        "How does attendance correlate with final assessment scores?",
        "Which faculties are producing the strongest graduate outcomes?",
        "Where are achievement gaps widest between student demographics?",
    ],
    "telecommunications": [
        "Which customer segments have the highest churn probability?",
        "What is the average revenue per user (ARPU) trend over time?",
        "Which service plans drive the highest margin?",
        "Where are network quality issues most concentrated geographically?",
        "What factors most strongly predict subscriber cancellation?",
    ],
    "banking": [
        "Which loan categories show the highest default rates?",
        "What is the distribution of credit scores across the portfolio?",
        "Which customer segments have the greatest cross-sell potential?",
        "Where are transaction anomalies most concentrated?",
        "What is the trend in net interest margin over recent periods?",
    ],
    "insurance": [
        "Which policy types have the highest claims frequency?",
        "What is the current loss ratio trend by product line?",
        "Which claims show characteristics associated with potential fraud?",
        "What risk factors are most predictive of high-cost claims?",
        "Which customer segments are most profitable after claims adjustment?",
    ],
    "retail": [
        "Which product categories drive the highest revenue per transaction?",
        "What is the trend in average basket size over time?",
        "Which stores or locations are underperforming against targets?",
        "What is the sell-through rate for seasonal inventory?",
        "Which customer segments show the highest repeat purchase frequency?",
    ],
    "ecommerce": [
        "Where in the purchase funnel do users drop off most?",
        "Which product categories have the highest cart abandonment rates?",
        "What is the trend in average order value over time?",
        "Which traffic sources convert at the highest rate?",
        "What is the return rate by product category?",
    ],
    "manufacturing": [
        "Which production lines have the lowest OEE scores?",
        "What is the trend in defect rate over the past quarter?",
        "Where is unplanned downtime most concentrated by shift or equipment?",
        "Which raw materials show the highest waste rates?",
        "How does actual output compare to planned capacity by line?",
    ],
    "supply_chain": [
        "Which suppliers have the poorest on-time delivery performance?",
        "What is the average lead time trend by supplier or region?",
        "Which SKUs are most frequently subject to stockouts?",
        "Where are logistics costs highest relative to order value?",
        "Which nodes in the supply chain introduce the most delay?",
    ],
    "hospitality": [
        "What is the occupancy rate trend by property or season?",
        "Which guest complaint categories recur most frequently?",
        "What is the relationship between pricing and booking lead time?",
        "Which channels drive the highest revenue per booking?",
        "What is the average length of stay by guest segment?",
    ],
    "real_estate": [
        "Which properties have the lowest yield relative to market comparables?",
        "What is the trend in vacancy rates across the portfolio?",
        "Which locations show the strongest capital value growth?",
        "What maintenance categories are consuming the most budget?",
        "Which tenant segments have the highest renewal rates?",
    ],
    "energy": [
        "Which assets or sites show the highest consumption anomalies?",
        "What is the trend in cost per unit of energy produced?",
        "Where is renewable generation underperforming relative to forecast?",
        "Which time periods show the greatest demand peaks?",
        "What is the relationship between weather patterns and consumption levels?",
    ],
    "government": [
        "Which service categories have the longest resolution times?",
        "Where are compliance rates falling below regulatory thresholds?",
        "Which departments are operating above budget?",
        "What is the trend in citizen satisfaction scores over time?",
        "Which regions show the greatest unmet demand for public services?",
    ],
    "saas": [
        "Which customer cohorts show the highest churn rates?",
        "What is the trend in monthly recurring revenue (MRR) growth?",
        "Which features correlate most strongly with long-term retention?",
        "What is the average time-to-value for new customers?",
        "Which account segments show the greatest expansion revenue potential?",
    ],
    "generic": [
        "Which variables show the strongest correlation with the primary outcome?",
        "Where are the largest data quality gaps in this dataset?",
        "What trends are visible in the key numeric columns over time?",
        "Which segments or groups stand out as statistical outliers?",
        "What baseline metrics should be tracked to measure improvement?",
    ],
}


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


class BusinessContextBuilder:
    """
    Converts analytical pipeline outputs into structured business intelligence.

    All logic is deterministic and rule-based — no LLMs, no external APIs.
    """

    def build(
        self,
        profile: dict,
        domain: str,
        classification: dict,
        kpis: list[dict],
        anomalies: dict,
        chart_plan: list[dict],
    ) -> dict:
        """
        Build a complete BusinessContext dictionary.

        Parameters
        ----------
        profile        : output of AnalyticsService.profile_dataset()
        domain         : detected domain string (e.g. "sales")
        classification : output of BusinessClassifier.classify()
        kpis           : output of KPIDetector.detect()
        anomalies      : output of AnomalyDetector.detect()
        chart_plan     : output of ChartPlanner.plan()

        Returns
        -------
        dict matching the BusinessContext schema
        """
        quality_score = self._dataset_quality_score(profile, anomalies)
        confidence = self._analysis_confidence(classification, kpis, quality_score, anomalies)

        return {
            "executive_summary": self._executive_summary(profile, domain, kpis, anomalies, quality_score),
            "strengths": self._strengths(profile, kpis, anomalies),
            "risks": self._risks(profile, anomalies),
            "opportunities": self._opportunities(domain),
            "recommended_questions": self._recommended_questions(domain),
            "priority_actions": self._priority_actions(profile, anomalies, quality_score),
            "analysis_confidence": confidence,
            "dataset_quality_score": quality_score,
        }

    # ------------------------------------------------------------------
    # 1. Executive summary
    # ------------------------------------------------------------------

    def _executive_summary(
        self,
        profile: dict,
        domain: str,
        kpis: list[dict],
        anomalies: dict,
        quality_score: int,
    ) -> str:
        domain_label = domain.replace("_", " ").title()
        rows = profile.get("row_count", 0)
        cols = profile.get("column_count", 0)

        # Opening: domain + scale
        parts: list[str] = [
            f"This {domain_label} dataset contains {rows:,} records across {cols} columns."
        ]

        # KPI highlight — surface the first non-zero KPI value
        kpi_highlight = next(
            (k for k in kpis if k.get("raw_value", 0) > 0),
            None,
        )
        if kpi_highlight:
            parts.append(
                f"{kpi_highlight['label']} stands at {kpi_highlight['value']}, "
                "indicating measurable business activity."
            )

        # Data quality verdict
        if quality_score >= 80:
            parts.append("Data quality is high, providing a solid foundation for reliable analysis.")
        elif quality_score >= 55:
            parts.append("Data quality is moderate; some gaps may limit the depth of certain analyses.")
        else:
            parts.append(
                "Data quality is below recommended thresholds — "
                "remediation should be prioritised before acting on findings."
            )

        # Missing-value caveat
        missing_warnings = anomalies.get("missing_data_warnings", [])
        if missing_warnings:
            affected = ", ".join(w["column"] for w in missing_warnings[:2])
            tail = f" and {len(missing_warnings) - 2} more" if len(missing_warnings) > 2 else ""
            parts.append(
                f"Missing values in {affected}{tail} may affect reporting accuracy for those dimensions."
            )

        return " ".join(parts)

    # ------------------------------------------------------------------
    # 2. Strengths
    # ------------------------------------------------------------------

    def _strengths(self, profile: dict, kpis: list[dict], anomalies: dict) -> list[str]:
        strengths: list[str] = []
        rows = profile.get("row_count", 0)
        numeric_cols = profile.get("numeric_columns", [])
        total_cols = profile.get("column_count", 1)
        missing_pct = (profile.get("total_missing_values", 0) / max(rows * total_cols, 1)) * 100
        dup_rate = profile.get("duplicate_rows", 0) / max(rows, 1)

        if rows >= 1000:
            strengths.append(f"Large dataset ({rows:,} rows) enables statistically significant findings.")
        elif rows >= 100:
            strengths.append(f"Adequate sample size ({rows:,} rows) for meaningful pattern detection.")

        if missing_pct < 2:
            strengths.append("Excellent data completeness — fewer than 2% of values are missing.")
        elif missing_pct < 5:
            strengths.append("Good data completeness — missing values are within acceptable limits.")

        if dup_rate < 0.01:
            strengths.append("Negligible duplicate rows — data integrity is clean.")

        numeric_ratio = len(numeric_cols) / total_cols if total_cols else 0
        if numeric_ratio >= 0.4:
            strengths.append(
                f"Strong numeric coverage ({len(numeric_cols)} of {total_cols} columns) "
                "enables quantitative KPI computation."
            )

        # Healthy KPIs — at least 2 non-zero
        healthy_kpis = [k for k in kpis if k.get("raw_value", 0) > 0]
        if len(healthy_kpis) >= 2:
            labels = " and ".join(k["label"] for k in healthy_kpis[:2])
            strengths.append(f"Key metrics are populated and computable: {labels}.")

        if not anomalies.get("unusual_values"):
            strengths.append("No statistical outliers detected — numeric distributions appear healthy.")

        # Guarantee at least one strength
        if not strengths:
            strengths.append("Dataset is structurally valid and ready for analysis.")

        return strengths

    # ------------------------------------------------------------------
    # 3. Risks
    # ------------------------------------------------------------------

    def _risks(self, profile: dict, anomalies: dict) -> list[str]:
        risks: list[str] = []
        rows = profile.get("row_count", 0)
        total_cells = max(rows * profile.get("column_count", 1), 1)
        missing_pct = (profile.get("total_missing_values", 0) / total_cells) * 100
        dup_count = profile.get("duplicate_rows", 0)
        numeric_cols = profile.get("numeric_columns", [])
        total_cols = profile.get("column_count", 1)

        if missing_pct >= 20:
            risks.append(
                f"Critical missing data ({missing_pct:.1f}% of cells) — "
                "analysis results may be materially distorted."
            )
        elif missing_pct >= 5:
            risks.append(
                f"Notable missing values ({missing_pct:.1f}% of cells) — "
                "imputation or exclusion strategy required before modelling."
            )

        if dup_count > 0:
            dup_rate = dup_count / max(rows, 1) * 100
            risks.append(
                f"{dup_count:,} duplicate rows detected ({dup_rate:.1f}%) — "
                "aggregations may be inflated without deduplication."
            )

        unusual = anomalies.get("unusual_values", [])
        high_outliers = [u for u in unusual if u.get("severity") in ("high", "medium")]
        if high_outliers:
            cols = ", ".join(u["column"] for u in high_outliers[:3])
            risks.append(
                f"Significant outliers in {cols} — "
                "these may skew averages and require investigation."
            )

        skewed = anomalies.get("suspicious_distributions", [])
        high_skew = [s for s in skewed if s.get("severity") == "high"]
        if high_skew:
            cols = ", ".join(s["column"] for s in high_skew[:2])
            risks.append(
                f"Highly skewed distributions in {cols} — "
                "consider log transformation before applying linear models."
            )

        numeric_ratio = len(numeric_cols) / total_cols if total_cols else 0
        if numeric_ratio < 0.2 and total_cols > 3:
            risks.append(
                "Low numeric column ratio — quantitative analysis options are limited. "
                "Consider encoding categorical variables for deeper modelling."
            )

        if rows < 50:
            risks.append(
                f"Small dataset ({rows} rows) — statistical findings may lack significance. "
                "Collect more data before drawing firm conclusions."
            )

        return risks

    # ------------------------------------------------------------------
    # 4. Opportunities
    # ------------------------------------------------------------------

    def _opportunities(self, domain: str) -> list[str]:
        return _DOMAIN_OPPORTUNITIES.get(domain, _DOMAIN_OPPORTUNITIES["generic"])

    # ------------------------------------------------------------------
    # 5. Recommended questions
    # ------------------------------------------------------------------

    def _recommended_questions(self, domain: str) -> list[str]:
        return _DOMAIN_QUESTIONS.get(domain, _DOMAIN_QUESTIONS["generic"])

    # ------------------------------------------------------------------
    # 6. Priority actions
    # ------------------------------------------------------------------

    def _priority_actions(
        self,
        profile: dict,
        anomalies: dict,
        quality_score: int,
    ) -> list[dict]:
        actions: list[dict] = []
        rows = profile.get("row_count", 0)
        dup_count = profile.get("duplicate_rows", 0)
        missing_warnings = anomalies.get("missing_data_warnings", [])
        unusual = anomalies.get("unusual_values", [])
        skewed = anomalies.get("suspicious_distributions", [])

        # Deduplication
        if dup_count > 0:
            dup_rate = dup_count / max(rows, 1)
            priority = "High" if dup_rate > 0.10 else "Medium"
            actions.append({
                "title": f"Deduplicate dataset ({dup_count:,} duplicate rows)",
                "priority": priority,
                "reason": (
                    f"{dup_rate * 100:.1f}% of rows are duplicates. "
                    "Leaving them in place inflates all aggregate metrics."
                ),
            })

        # Missing value remediation
        high_missing = [w for w in missing_warnings if w.get("severity") == "high"]
        if high_missing:
            cols = ", ".join(w["column"] for w in high_missing[:2])
            actions.append({
                "title": f"Address high missing-value rate in: {cols}",
                "priority": "High",
                "reason": (
                    "Columns with >20% missing values degrade model accuracy "
                    "and may introduce systematic bias if ignored."
                ),
            })
        elif missing_warnings:
            cols = missing_warnings[0]["column"]
            actions.append({
                "title": f"Impute or document missing values in '{cols}'",
                "priority": "Medium",
                "reason": (
                    f"'{cols}' has {missing_warnings[0]['missing_rate']}% missing values. "
                    "An explicit imputation strategy improves downstream reliability."
                ),
            })

        # Outlier review
        high_outlier_cols = [u for u in unusual if u.get("severity") in ("high", "medium")]
        if high_outlier_cols:
            cols = ", ".join(u["column"] for u in high_outlier_cols[:2])
            actions.append({
                "title": f"Investigate outliers in: {cols}",
                "priority": "Medium",
                "reason": (
                    "Statistical outliers distort averages and can mislead KPI calculations. "
                    "Determine whether they are data errors or genuine edge cases."
                ),
            })

        # Skewness
        if skewed:
            col = skewed[0]["column"]
            actions.append({
                "title": f"Apply log transformation to '{col}'",
                "priority": "Low",
                "reason": (
                    f"'{col}' is heavily skewed (skewness={skewed[0].get('skewness', '?')}). "
                    "Normalising the distribution will improve model performance."
                ),
            })

        # Low quality fallback
        if quality_score < 50:
            actions.append({
                "title": "Remediate data quality before proceeding with analysis",
                "priority": "High",
                "reason": (
                    f"Overall dataset quality score is {quality_score}/100. "
                    "At this level, analytical findings may be unreliable. "
                    "Prioritise cleaning before drawing business conclusions."
                ),
            })

        # Always include a forward-looking action
        if len(actions) < 3:
            actions.append({
                "title": "Define and track baseline KPIs over time",
                "priority": "Medium",
                "reason": (
                    "Establishing baseline metrics now enables trend analysis "
                    "and performance benchmarking in future reporting periods."
                ),
            })

        return actions[:5]

    # ------------------------------------------------------------------
    # 7. Dataset quality score (0-100)
    # ------------------------------------------------------------------

    def _dataset_quality_score(self, profile: dict, anomalies: dict) -> int:
        score = 100.0
        rows = profile.get("row_count", 0)
        total_cols = profile.get("column_count", 1)
        numeric_cols = profile.get("numeric_columns", [])
        total_cells = max(rows * total_cols, 1)

        # Missing values — up to -30 points
        missing_pct = profile.get("total_missing_values", 0) / total_cells
        score -= min(30, missing_pct * 150)

        # Duplicates — up to -20 points
        dup_rate = profile.get("duplicate_rows", 0) / max(rows, 1)
        score -= min(20, dup_rate * 100)

        # Row count — up to -15 points for very small datasets
        if rows < 10:
            score -= 15
        elif rows < 50:
            score -= 10
        elif rows < 100:
            score -= 5

        # Column diversity — up to -10 points for low numeric coverage
        numeric_ratio = len(numeric_cols) / total_cols if total_cols else 0
        if numeric_ratio < 0.15:
            score -= 10
        elif numeric_ratio < 0.30:
            score -= 5

        # Outlier severity — up to -10 points
        unusual = anomalies.get("unusual_values", [])
        high_outlier_count = sum(1 for u in unusual if u.get("severity") == "high")
        score -= min(10, high_outlier_count * 5)

        # Skewed distributions — up to -5 points
        skewed = anomalies.get("suspicious_distributions", [])
        score -= min(5, len(skewed) * 2)

        return max(0, min(100, round(score)))

    # ------------------------------------------------------------------
    # 8. Analysis confidence (0-100)
    # ------------------------------------------------------------------

    def _analysis_confidence(
        self,
        classification: dict,
        kpis: list[dict],
        quality_score: int,
        anomalies: dict,
    ) -> int:
        # Base: classifier confidence (0-95)
        classifier_conf = classification.get("confidence", 0)  # already 0-95
        base = classifier_conf * 0.40  # up to 38 points

        # KPI hit rate — how many KPIs have non-zero raw values
        kpi_hit = sum(1 for k in kpis if k.get("raw_value", 0) > 0)
        kpi_score = min(25, kpi_hit * 8)  # up to 25 points

        # Dataset quality contribution — up to 25 points
        quality_contribution = quality_score * 0.25  # up to 25 points

        # Anomaly penalty — severe issues reduce confidence
        unusual = anomalies.get("unusual_values", [])
        high_severity = sum(1 for u in unusual if u.get("severity") == "high")
        anomaly_penalty = min(12, high_severity * 4)

        raw = base + kpi_score + quality_contribution - anomaly_penalty
        return max(0, min(100, round(raw)))
