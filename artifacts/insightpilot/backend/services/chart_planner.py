"""
InsightPilot AI — Chart Planner (domain-aware, semantically scored).

Recommends up to four high-value charts based on the detected business domain
and the actual columns present in the DataFrame.  Each recommendation includes:
  type, x, y, title, priority, confidence, reason, business_question, aggregation

Public API (unchanged):
    plan(df: pd.DataFrame, domain: str) -> list[dict]

Architecture
------------
1. Filter out ID columns and high-cardinality categoricals (>30 unique values).
2. Per-domain *registry* declares preferred metrics, dimensions, chart types,
   titles, business questions, and aggregations — ordered by analytic importance.
3. Column selection uses *semantic scoring*: every candidate column is scored
   against keyword groups and the highest-scoring column wins (not first-match).
4. If a registry entry cannot be satisfied, it is skipped.
5. Generic heuristics fill remaining slots up to the four-chart limit.
6. Duplicate (x, y) pairs are suppressed across domain + fallback phases.
"""

from __future__ import annotations

import logging
import re
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_CHARTS = 4
MAX_CARDINALITY = 30          # categoricals with more unique values are dropped
ID_UNIQUENESS_THRESHOLD = 0.9 # fraction of unique values that marks a column as an ID

# ---------------------------------------------------------------------------
# Column-name helpers
# ---------------------------------------------------------------------------

def _tokens(col: str) -> set[str]:
    """Split a column name into lowercase word tokens."""
    return set(re.split(r"[\s_\-./|]+", col.lower()))


def _label(col_name: str) -> str:
    """Convert snake_case / camelCase column name to a readable title."""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", col_name)
    return re.sub(r"[\s_\-./|]+", " ", spaced).title()


def _is_temporal(col: str, dtype) -> bool:
    """Return True if the column looks like a time/date axis."""
    if hasattr(dtype, "kind") and dtype.kind == "M":
        return True
    time_words = {"date", "time", "month", "year", "week", "quarter",
                  "period", "day", "timestamp", "created", "updated"}
    return bool(_tokens(col) & time_words)


def _is_id_col(col: str, series: pd.Series) -> bool:
    """
    Return True if the column looks like a row identifier (should be ignored
    for charting).  Two conditions must both hold:
      1. The column name contains an ID marker token.
      2. The column has very high cardinality (>90 % unique values).
    """
    id_markers = {"id", "identifier", "key", "code", "num", "number",
                  "no", "index", "idx", "uuid", "guid", "ref", "pk"}
    if not (_tokens(col) & id_markers):
        return False
    n = len(series)
    if n == 0:
        return False
    return series.nunique() / n >= ID_UNIQUENESS_THRESHOLD


# ---------------------------------------------------------------------------
# Semantic scoring
# ---------------------------------------------------------------------------

def _score_column(col: str, keyword_groups: list[list[str]]) -> tuple[float, str]:
    """
    Score a column name against ordered keyword groups.

    Each group is a list of synonyms.  The first group has weight 1.0, the
    second 0.9, etc.  Matching *any* keyword in a group earns the full group
    weight — group size does not penalise the score.  This preserves the
    intended priority ordering: group 0 always beats group 1, group 1 always
    beats group 2, and so on.

    Returns (score, best_matched_keyword).  Score 0.0 means no match.
    """
    tokens = _tokens(col)
    best_score = 0.0
    best_kw = ""
    for i, group in enumerate(keyword_groups):
        weight = max(1.0 - i * 0.1, 0.1)
        for kw in group:
            if kw in tokens and weight > best_score:
                best_score = weight
                best_kw = kw
                break  # one match per group is enough
    return best_score, best_kw


def _best_scored_match(
    candidates: list[str],
    keyword_groups: list[list[str]],
) -> tuple[str | None, float, str]:
    """
    Return (best_column, score, matched_keyword) — the candidate with the
    highest semantic score against the keyword groups.
    """
    best_col: str | None = None
    best_score = 0.0
    best_kw = ""
    for col in candidates:
        score, kw = _score_column(col, keyword_groups)
        if score > best_score:
            best_score = score
            best_col = col
            best_kw = kw
    return best_col, best_score, best_kw


# ---------------------------------------------------------------------------
# Column filtering
# ---------------------------------------------------------------------------

def _usable_categoricals(cat_cols: list[str], df: pd.DataFrame) -> list[str]:
    """
    Remove ID columns and high-cardinality columns from the categorical list.
    These are almost never useful as chart dimensions.
    """
    result = []
    for col in cat_cols:
        if _is_id_col(col, df[col]):
            continue
        if df[col].nunique() > MAX_CARDINALITY:
            continue
        result.append(col)
    return result


def _usable_numerics(num_cols: list[str], df: pd.DataFrame) -> list[str]:
    """Remove numeric columns that look like IDs."""
    return [c for c in num_cols if not _is_id_col(c, df[c])]


# ---------------------------------------------------------------------------
# Domain registry
# ---------------------------------------------------------------------------

# Each entry:
#   metric_keywords  : list[list[str]]  — synonym groups, ordered by preference
#   dim_keywords     : list[list[str]]  — synonym groups for x/category column
#   chart_type       : str
#   title_template   : str
#   business_question: str
#   aggregation      : str              — "sum" | "mean" | "count"
#   requires_temporal: bool

_DOMAIN_REGISTRY: dict[str, list[dict]] = {

    "sales": [
        {
            "metric_keywords":    [["revenue", "sales", "income", "turnover"], ["amount", "total", "value"]],
            "dim_keywords":       [["date", "month", "year", "week", "quarter", "period", "time", "day"]],
            "chart_type":         "line",
            "title_template":     "Revenue Trend",
            "business_question":  "How is revenue changing over time?",
            "aggregation":        "sum",
            "requires_temporal":  True,
        },
        {
            "metric_keywords":    [["profit", "margin", "net", "earnings"], ["revenue", "sales"]],
            "dim_keywords":       [["product", "item", "sku", "category", "line", "brand"]],
            "chart_type":         "bar",
            "title_template":     "Profit by Product",
            "business_question":  "Which products are most profitable?",
            "aggregation":        "sum",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["orders", "quantity", "qty", "units", "count", "volume"]],
            "dim_keywords":       [["region", "territory", "area", "location", "country", "city", "state"]],
            "chart_type":         "bar",
            "title_template":     "Orders by Region",
            "business_question":  "Which regions drive the most orders?",
            "aggregation":        "sum",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["revenue", "sales", "amount", "total"]],
            "dim_keywords":       [["segment", "tier", "customer", "client", "account", "type", "category"]],
            "chart_type":         "bar",
            "title_template":     "Revenue by Customer Segment",
            "business_question":  "Which customer segments generate the most revenue?",
            "aggregation":        "sum",
            "requires_temporal":  False,
        },
    ],

    "marketing": [
        {
            "metric_keywords":    [["conversions", "converted", "leads", "signups", "acquisitions"]],
            "dim_keywords":       [["campaign", "ad", "creative", "name", "title"]],
            "chart_type":         "bar",
            "title_template":     "Campaign Performance",
            "business_question":  "Which campaigns drive the most conversions?",
            "aggregation":        "sum",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["spend", "cost", "budget", "expenditure"]],
            "dim_keywords":       [["conversions", "converted", "leads", "signups"]],
            "chart_type":         "scatter",
            "title_template":     "Spend vs Conversions",
            "business_question":  "Is marketing spend converting to leads?",
            "aggregation":        "sum",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["ctr", "clickthrough", "click", "rate", "open"]],
            "dim_keywords":       [["campaign", "ad", "creative", "channel", "source", "medium"]],
            "chart_type":         "bar",
            "title_template":     "CTR by Campaign",
            "business_question":  "Which campaigns achieve the best click-through rates?",
            "aggregation":        "mean",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["revenue", "sales", "conversions", "leads", "value"]],
            "dim_keywords":       [["channel", "source", "medium", "platform", "network"]],
            "chart_type":         "bar",
            "title_template":     "Channel Performance",
            "business_question":  "Which marketing channels deliver the most value?",
            "aggregation":        "sum",
            "requires_temporal":  False,
        },
    ],

    "finance": [
        {
            "metric_keywords":    [["revenue", "income", "sales", "turnover"]],
            "dim_keywords":       [["expenses", "costs", "expenditure", "opex", "spend"]],
            "chart_type":         "bar",
            "title_template":     "Revenue vs Expenses",
            "business_question":  "Are revenues outpacing expenses?",
            "aggregation":        "sum",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["actual", "actuals", "spent", "realized"]],
            "dim_keywords":       [["budget", "planned", "forecast", "target"]],
            "chart_type":         "bar",
            "title_template":     "Budget vs Actual",
            "business_question":  "How does actual spending compare to budget?",
            "aggregation":        "sum",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["expense", "cost", "expenditure", "spend", "opex"]],
            "dim_keywords":       [["category", "type", "account", "department", "line", "class"]],
            "chart_type":         "pie",
            "title_template":     "Expense Breakdown",
            "business_question":  "Where is money being spent?",
            "aggregation":        "sum",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["cash", "cashflow", "net", "balance", "flow", "liquidity"]],
            "dim_keywords":       [["date", "month", "year", "quarter", "period", "week"]],
            "chart_type":         "line",
            "title_template":     "Cash Flow Trend",
            "business_question":  "How is cash flow evolving over time?",
            "aggregation":        "sum",
            "requires_temporal":  True,
        },
    ],

    "hr": [
        {
            "metric_keywords":    [["headcount", "employees", "staff", "count", "fte", "workers", "people"]],
            "dim_keywords":       [["department", "dept", "team", "division", "unit", "group"]],
            "chart_type":         "bar",
            "title_template":     "Headcount by Department",
            "business_question":  "How is headcount distributed across departments?",
            "aggregation":        "count",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["salary", "compensation", "pay", "wage", "income", "ctc"]],
            "dim_keywords":       [["salary", "compensation", "pay", "wage", "income"]],
            "chart_type":         "histogram",
            "title_template":     "Salary Distribution",
            "business_question":  "What does the salary distribution look like?",
            "aggregation":        "count",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["attrition", "turnover", "churn", "resignation", "termination", "left"]],
            "dim_keywords":       [["department", "dept", "team", "division", "unit"]],
            "chart_type":         "bar",
            "title_template":     "Attrition by Department",
            "business_question":  "Which departments have the highest attrition?",
            "aggregation":        "sum",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["tenure", "years", "experience", "seniority", "duration", "service"]],
            "dim_keywords":       [["tenure", "years", "experience", "seniority", "duration"]],
            "chart_type":         "histogram",
            "title_template":     "Employee Tenure Distribution",
            "business_question":  "How long have employees been with the company?",
            "aggregation":        "count",
            "requires_temporal":  False,
        },
    ],

    "inventory": [
        {
            "metric_keywords":    [["stock", "quantity", "qty", "units", "on_hand", "inventory", "level"]],
            "dim_keywords":       [["warehouse", "location", "site", "facility", "depot", "store"]],
            "chart_type":         "bar",
            "title_template":     "Stock by Warehouse",
            "business_question":  "How is stock distributed across warehouses?",
            "aggregation":        "sum",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["stock", "quantity", "qty", "units", "inventory", "level", "available"]],
            "dim_keywords":       [["product", "item", "sku", "part", "name", "description"]],
            "chart_type":         "bar",
            "title_template":     "Inventory by Product",
            "business_question":  "Which products have the most inventory?",
            "aggregation":        "sum",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["lead_time", "lead", "delivery", "days", "time", "duration"]],
            "dim_keywords":       [["supplier", "vendor", "partner", "source", "provider"]],
            "chart_type":         "bar",
            "title_template":     "Supplier Performance",
            "business_question":  "Which suppliers have the shortest lead times?",
            "aggregation":        "mean",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["reorder", "safety", "min", "threshold", "shortage", "stockout", "below"]],
            "dim_keywords":       [["product", "item", "sku", "part", "category"]],
            "chart_type":         "bar",
            "title_template":     "Reorder Risk",
            "business_question":  "Which products are at risk of stockout?",
            "aggregation":        "sum",
            "requires_temporal":  False,
        },
    ],

    "operations": [
        {
            "metric_keywords":    [["throughput", "output", "units", "volume", "produced", "completed"]],
            "dim_keywords":       [["date", "week", "month", "shift", "period", "day", "time"]],
            "chart_type":         "line",
            "title_template":     "Throughput Over Time",
            "business_question":  "How is operational throughput trending?",
            "aggregation":        "sum",
            "requires_temporal":  True,
        },
        {
            "metric_keywords":    [["downtime", "failure", "defect", "error", "issue", "fault", "incident"]],
            "dim_keywords":       [["machine", "line", "process", "station", "equipment", "asset"]],
            "chart_type":         "bar",
            "title_template":     "Downtime by Equipment",
            "business_question":  "Which equipment causes the most downtime?",
            "aggregation":        "sum",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["cycle_time", "duration", "time", "hours", "lead", "takt"]],
            "dim_keywords":       [["process", "step", "stage", "operation", "task", "activity"]],
            "chart_type":         "bar",
            "title_template":     "Cycle Time by Process",
            "business_question":  "Which processes have the longest cycle times?",
            "aggregation":        "mean",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["efficiency", "utilization", "oee", "performance", "rate", "yield"]],
            "dim_keywords":       [["machine", "line", "shift", "team", "station", "plant"]],
            "chart_type":         "bar",
            "title_template":     "Efficiency by Line",
            "business_question":  "Which production lines are most efficient?",
            "aggregation":        "mean",
            "requires_temporal":  False,
        },
    ],

    "customer_support": [
        {
            "metric_keywords":    [["tickets", "cases", "issues", "requests", "incidents", "count", "volume"]],
            "dim_keywords":       [["date", "week", "month", "day", "period", "time"]],
            "chart_type":         "line",
            "title_template":     "Ticket Volume Over Time",
            "business_question":  "How is support ticket volume trending?",
            "aggregation":        "count",
            "requires_temporal":  True,
        },
        {
            "metric_keywords":    [["resolution_time", "handle_time", "response_time", "duration", "hours", "minutes"]],
            "dim_keywords":       [["category", "type", "issue", "topic", "priority", "reason"]],
            "chart_type":         "bar",
            "title_template":     "Resolution Time by Category",
            "business_question":  "Which issue categories take longest to resolve?",
            "aggregation":        "mean",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["csat", "satisfaction", "rating", "score", "nps", "feedback"]],
            "dim_keywords":       [["agent", "team", "representative", "staff", "assignee"]],
            "chart_type":         "bar",
            "title_template":     "Customer Satisfaction by Agent",
            "business_question":  "Which agents achieve the highest satisfaction scores?",
            "aggregation":        "mean",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["tickets", "cases", "count", "volume", "issues"]],
            "dim_keywords":       [["channel", "source", "contact", "medium", "type", "origin"]],
            "chart_type":         "pie",
            "title_template":     "Cases by Channel",
            "business_question":  "Which support channels receive the most cases?",
            "aggregation":        "count",
            "requires_temporal":  False,
        },
    ],

    "healthcare": [
        {
            "metric_keywords":    [["admissions", "patients", "visits", "encounters", "count", "cases"]],
            "dim_keywords":       [["date", "month", "week", "day", "period", "year", "time"]],
            "chart_type":         "line",
            "title_template":     "Admissions Over Time",
            "business_question":  "How are patient admissions trending?",
            "aggregation":        "count",
            "requires_temporal":  True,
        },
        {
            "metric_keywords":    [["patients", "count", "cases", "admissions", "volume"]],
            "dim_keywords":       [["diagnosis", "condition", "icd", "disease", "category", "type"]],
            "chart_type":         "bar",
            "title_template":     "Patients by Diagnosis",
            "business_question":  "What are the most common diagnoses?",
            "aggregation":        "count",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["los", "length_of_stay", "stay", "duration", "days", "nights"]],
            "dim_keywords":       [["los", "length_of_stay", "stay", "days", "duration"]],
            "chart_type":         "histogram",
            "title_template":     "Length of Stay Distribution",
            "business_question":  "What is the typical patient length of stay?",
            "aggregation":        "count",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["readmission", "readmitted", "return", "rehospitalization", "bounce"]],
            "dim_keywords":       [["date", "month", "week", "period", "year", "quarter"]],
            "chart_type":         "line",
            "title_template":     "Readmission Trend",
            "business_question":  "Is the readmission rate improving over time?",
            "aggregation":        "sum",
            "requires_temporal":  True,
        },
    ],

    "education": [
        {
            "metric_keywords":    [["score", "grade", "marks", "gpa", "result", "performance", "points"]],
            "dim_keywords":       [["student", "name", "learner", "pupil", "class", "group", "cohort"]],
            "chart_type":         "bar",
            "title_template":     "Student Performance",
            "business_question":  "How are students performing?",
            "aggregation":        "mean",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["attendance", "present", "absent", "rate", "days", "sessions"]],
            "dim_keywords":       [["date", "week", "month", "period", "term", "semester"]],
            "chart_type":         "line",
            "title_template":     "Attendance Trend",
            "business_question":  "How is student attendance trending?",
            "aggregation":        "mean",
            "requires_temporal":  True,
        },
        {
            "metric_keywords":    [["enrollment", "enrolled", "students", "count", "registered", "total"]],
            "dim_keywords":       [["course", "subject", "class", "module", "program", "department"]],
            "chart_type":         "bar",
            "title_template":     "Enrollment by Course",
            "business_question":  "Which courses have the highest enrollment?",
            "aggregation":        "count",
            "requires_temporal":  False,
        },
        {
            "metric_keywords":    [["grade", "score", "marks", "gpa", "result", "band", "level"]],
            "dim_keywords":       [["grade", "score", "marks", "band", "level", "category"]],
            "chart_type":         "histogram",
            "title_template":     "Grade Distribution",
            "business_question":  "How are grades distributed across the student population?",
            "aggregation":        "count",
            "requires_temporal":  False,
        },
    ],

    # Catch-all — used when domain is "generic" or unrecognised
    "generic": [],
}


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------


class ChartPlanner:
    """
    Produces up to four chart recommendations for a given dataset and domain.

    Improvements over the previous version:
    - Semantic scoring: picks the best-scoring column, not the first keyword match.
    - ID-column filtering: ignores CustomerID, OrderID, EmployeeID, etc.
    - High-cardinality filtering: ignores categorical columns with >30 unique values.
    - Rich metadata: priority, confidence, reason, business_question, aggregation.
    - Duplicate suppression: same (x, y) pair cannot appear twice.
    """

    def plan(self, df: pd.DataFrame, domain: str) -> list[dict]:
        """
        Produce an ordered list of chart recommendations.

        Parameters
        ----------
        df     : pd.DataFrame  — the uploaded dataset.
        domain : str           — detected business domain (from BusinessClassifier).

        Returns
        -------
        list[dict] with keys:
            type, x, y, title, priority, confidence, reason,
            business_question, aggregation
        """
        # --- Classify columns ---
        all_cols = df.columns.tolist()
        raw_numeric = df.select_dtypes(include="number").columns.tolist()
        raw_categorical = df.select_dtypes(include=["object", "category"]).columns.tolist()

        temporal_cols = [c for c in all_cols if _is_temporal(c, df[c].dtype)]
        numeric_cols = _usable_numerics(raw_numeric, df)
        cat_cols = _usable_categoricals(
            [c for c in raw_categorical if c not in temporal_cols], df
        )

        # --- Logging (satisfies debug requirement) ---
        logger.info(
            "ChartPlanner.plan | domain=%s | numeric=%s | categorical=%s | temporal=%s",
            domain, numeric_cols, cat_cols, temporal_cols,
        )

        charts: list[dict] = []

        # --- Phase 1: domain-specific charts ---
        registry = _DOMAIN_REGISTRY.get(domain, _DOMAIN_REGISTRY["generic"])
        charts.extend(
            self._from_registry(registry, numeric_cols, cat_cols, temporal_cols)
        )

        # --- Phase 2: generic fallback ---
        if len(charts) < MAX_CHARTS:
            charts.extend(
                self._generic_fallback(numeric_cols, cat_cols, temporal_cols, charts)
            )

        result = charts[:MAX_CHARTS]

        logger.info(
            "ChartPlanner.plan | final charts=%s",
            [c["title"] for c in result],
        )
        return result

    # ------------------------------------------------------------------
    # Domain-specific phase
    # ------------------------------------------------------------------

    def _from_registry(
        self,
        registry: list[dict],
        numeric_cols: list[str],
        cat_cols: list[str],
        temporal_cols: list[str],
    ) -> list[dict]:
        charts: list[dict] = []
        seen_pairs: set[tuple[str, str]] = set()

        for position, entry in enumerate(registry):
            if len(charts) >= MAX_CHARTS:
                break

            chart_type = entry["chart_type"]
            requires_temporal = entry.get("requires_temporal", False)
            metric_kws = entry["metric_keywords"]
            dim_kws = entry["dim_keywords"]
            title = entry["title_template"]
            bq = entry["business_question"]
            agg = entry["aggregation"]

            # --- Resolve x column ---
            x_conf = 0.0
            x_reason = ""
            if chart_type == "histogram":
                # x = the metric column (we're plotting its distribution)
                x_col, x_conf, x_kw = _best_scored_match(numeric_cols, metric_kws)
                if x_col is None:
                    continue
                x_reason = f"'{x_col}' matched '{x_kw}' as the distribution metric"

            elif chart_type == "scatter":
                # x = a numeric dimension column (first metric_keywords are the y)
                x_col, x_conf, x_kw = _best_scored_match(numeric_cols, dim_kws)
                if x_col is None:
                    x_col = numeric_cols[0] if numeric_cols else None
                    x_conf = 0.3
                    x_reason = f"'{x_col}' used as fallback scatter x-axis" if x_col else ""
                else:
                    x_reason = f"'{x_col}' matched '{x_kw}' as scatter dimension"
                if x_col is None:
                    continue

            elif requires_temporal:
                # x = best temporal column
                if not temporal_cols:
                    continue
                x_col, x_conf, x_kw = _best_scored_match(temporal_cols, dim_kws)
                if x_col is None:
                    x_col = temporal_cols[0]
                    x_conf = 0.5
                    x_reason = f"'{x_col}' used as fallback time axis"
                else:
                    x_reason = f"'{x_col}' matched '{x_kw}' as time axis"

            else:
                # x = best categorical dimension
                x_col, x_conf, x_kw = _best_scored_match(cat_cols, dim_kws)
                if x_col is None:
                    continue
                x_reason = f"'{x_col}' matched '{x_kw}' as category dimension"

            # --- Resolve y column ---
            y_conf = 0.0
            y_reason = ""
            if chart_type == "histogram":
                y_col = "frequency"
                y_conf = 1.0
                y_reason = "frequency bins computed from distribution"

            elif chart_type == "pie":
                y_col = "count"
                y_conf = 1.0
                y_reason = "frequency count of category values"

            elif chart_type == "scatter":
                # y = metric column, different from x
                remaining = [c for c in numeric_cols if c != x_col]
                y_col, y_conf, y_kw = _best_scored_match(remaining, metric_kws)
                if y_col is None:
                    y_col = remaining[0] if remaining else None
                    y_conf = 0.3
                    y_reason = f"'{y_col}' used as fallback scatter y-axis" if y_col else ""
                else:
                    y_reason = f"'{y_col}' matched '{y_kw}' as scatter metric"
                if y_col is None:
                    continue

            else:
                # y = best numeric metric
                y_col, y_conf, y_kw = _best_scored_match(numeric_cols, metric_kws)
                if y_col is None:
                    continue
                y_reason = f"'{y_col}' matched '{y_kw}' as value metric"

            pair = (x_col, y_col)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            confidence = round((x_conf + y_conf) / 2, 2)
            priority = max(95 - position * 10, 20)

            charts.append({
                "type": chart_type,
                "x": x_col,
                "y": y_col,
                "title": title,
                "priority": priority,
                "confidence": confidence,
                "reason": f"{x_reason}; {y_reason}",
                "business_question": bq,
                "aggregation": agg,
            })

        return charts

    # ------------------------------------------------------------------
    # Generic fallback phase
    # ------------------------------------------------------------------

    _GENERIC_METRIC_KWS: list[list[str]] = [
        ["revenue", "sales", "income"],
        ["amount", "total", "value"],
        ["profit", "margin", "earnings"],
        ["spend", "cost", "expense"],
        ["salary", "compensation"],
        ["score", "rating", "rate"],
        ["quantity", "qty", "count", "units"],
        ["price"],
    ]

    _GENERIC_CATEGORY_KWS: list[list[str]] = [
        ["region", "territory", "area", "country"],
        ["department", "dept", "division"],
        ["channel", "source", "medium"],
        ["category", "type", "segment"],
        ["product", "item", "sku"],
        ["status"],
        ["team"],
    ]

    def _generic_fallback(
        self,
        numeric_cols: list[str],
        cat_cols: list[str],
        temporal_cols: list[str],
        existing: list[dict],
    ) -> list[dict]:
        charts: list[dict] = []
        seen_pairs: set[tuple[str, str]] = {(c["x"], c["y"]) for c in existing}
        remaining = MAX_CHARTS - len(existing)
        fallback_pos = 0

        def _priority() -> int:
            return max(50 - fallback_pos * 10, 10)

        def _add(spec: dict) -> bool:
            nonlocal fallback_pos
            pair = (spec["x"], spec["y"])
            if pair not in seen_pairs and len(charts) < remaining:
                seen_pairs.add(pair)
                charts.append(spec)
                fallback_pos += 1
                return True
            return False

        # Line: time + best numeric
        if temporal_cols and numeric_cols:
            x = temporal_cols[0]
            y_col, y_score, y_kw = _best_scored_match(numeric_cols, self._GENERIC_METRIC_KWS)
            y = y_col or numeric_cols[0]
            conf = round(y_score, 2) if y_col else 0.3
            _add({
                "type": "line", "x": x, "y": y,
                "title": f"{_label(y)} over {_label(x)}",
                "priority": _priority(), "confidence": conf,
                "reason": f"Time-series trend using '{x}' and '{y}'",
                "business_question": f"How does {_label(y)} change over time?",
                "aggregation": "sum",
            })

        # Second line with a different numeric
        if temporal_cols and len(numeric_cols) > 1 and len(charts) < remaining:
            x = temporal_cols[0]
            used_y = {c["y"] for c in existing + charts}
            extras = [c for c in numeric_cols if c not in used_y]
            if extras:
                _add({
                    "type": "line", "x": x, "y": extras[0],
                    "title": f"{_label(extras[0])} Trend",
                    "priority": _priority(), "confidence": 0.4,
                    "reason": f"Secondary trend for '{extras[0]}'",
                    "business_question": f"How does {_label(extras[0])} evolve over time?",
                    "aggregation": "sum",
                })

        # Bar: best category + best numeric
        if cat_cols and numeric_cols and len(charts) < remaining:
            x_col, x_score, x_kw = _best_scored_match(cat_cols, self._GENERIC_CATEGORY_KWS)
            x = x_col or cat_cols[0]
            y_col, y_score, y_kw = _best_scored_match(numeric_cols, self._GENERIC_METRIC_KWS)
            y = y_col or numeric_cols[0]
            conf = round((x_score + y_score) / 2, 2)
            _add({
                "type": "bar", "x": x, "y": y,
                "title": f"{_label(y)} by {_label(x)}",
                "priority": _priority(), "confidence": conf,
                "reason": f"Group '{y}' by '{x}'",
                "business_question": f"How does {_label(y)} vary by {_label(x)}?",
                "aggregation": "sum",
            })

        # Second bar with a different category
        if len(cat_cols) > 1 and numeric_cols and len(charts) < remaining:
            used_x = {c["x"] for c in existing + charts}
            alt_cats = [c for c in cat_cols if c not in used_x]
            if alt_cats:
                y_col, y_score, _ = _best_scored_match(numeric_cols, self._GENERIC_METRIC_KWS)
                y = y_col or numeric_cols[0]
                _add({
                    "type": "bar", "x": alt_cats[0], "y": y,
                    "title": f"{_label(y)} by {_label(alt_cats[0])}",
                    "priority": _priority(), "confidence": 0.4,
                    "reason": f"Alternative grouping by '{alt_cats[0]}'",
                    "business_question": f"How does {_label(y)} differ by {_label(alt_cats[0])}?",
                    "aggregation": "sum",
                })

        # Pie: only categoricals, no numeric
        if cat_cols and not numeric_cols and len(charts) < remaining:
            _add({
                "type": "pie", "x": cat_cols[0], "y": "count",
                "title": f"Distribution of {_label(cat_cols[0])}",
                "priority": _priority(), "confidence": 0.5,
                "reason": f"Category frequency for '{cat_cols[0]}'",
                "business_question": f"How is {_label(cat_cols[0])} distributed?",
                "aggregation": "count",
            })

        # Histogram: multiple numeric columns available
        if len(numeric_cols) >= 2 and len(charts) < remaining:
            used_x = {c["x"] for c in existing + charts}
            for col in numeric_cols:
                if len(charts) >= remaining:
                    break
                if col not in used_x:
                    _add({
                        "type": "histogram", "x": col, "y": "frequency",
                        "title": f"Distribution of {_label(col)}",
                        "priority": _priority(), "confidence": 0.5,
                        "reason": f"Value distribution for '{col}'",
                        "business_question": f"What is the distribution of {_label(col)}?",
                        "aggregation": "count",
                    })

        # Scatter: exactly two numeric columns
        if len(numeric_cols) == 2 and len(charts) < remaining:
            _add({
                "type": "scatter", "x": numeric_cols[0], "y": numeric_cols[1],
                "title": f"{_label(numeric_cols[0])} vs {_label(numeric_cols[1])}",
                "priority": _priority(), "confidence": 0.6,
                "reason": f"Correlation between '{numeric_cols[0]}' and '{numeric_cols[1]}'",
                "business_question": f"Is there a relationship between {_label(numeric_cols[0])} and {_label(numeric_cols[1])}?",
                "aggregation": "sum",
            })

        return charts
