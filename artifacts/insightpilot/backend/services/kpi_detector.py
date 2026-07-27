"""
InsightPilot AI — KPI Detector.

Given a Pandas DataFrame and a detected business domain, automatically identifies
and computes the most meaningful KPIs from the actual data.

No values are hardcoded — every KPI is derived from the DataFrame at runtime.
"""

import re
import math
import pandas as pd
from typing import Any


# ---------------------------------------------------------------------------
# KPI configuration registry
# ---------------------------------------------------------------------------
# Each entry describes one potential KPI:
#   patterns  — substrings to look for in column names (lower-cased, tokenised)
#   agg       — aggregation to apply: "sum" | "mean" | "count_rows" | "max" | "min" | "nunique"
#   format    — how to display the result: "currency" | "integer" | "decimal" | "percent"
#   description_tpl — short description; {col} is replaced with the matched column name

_DOMAIN_KPI_CONFIGS: dict[str, list[dict]] = {
    "sales": [
        {"label": "Total Revenue",      "patterns": ["revenue", "sales", "amount", "total_sales"], "agg": "sum",       "format": "currency",    "description_tpl": "Sum of {col}"},
        {"label": "Total Orders",        "patterns": ["order_id", "order", "transaction_id"],       "agg": "count_rows","format": "integer",     "description_tpl": "Number of records in {col}"},
        {"label": "Avg Order Value",     "patterns": ["revenue", "amount", "sales"],                "agg": "mean",      "format": "currency",    "description_tpl": "Average of {col}"},
        {"label": "Total Profit",        "patterns": ["profit", "margin", "net_profit"],            "agg": "sum",       "format": "currency",    "description_tpl": "Sum of {col}"},
    ],
    "marketing": [
        {"label": "Total Spend",         "patterns": ["spend", "cost", "budget"],                   "agg": "sum",       "format": "currency",    "description_tpl": "Total spend across {col}"},
        {"label": "Total Clicks",        "patterns": ["clicks", "click"],                           "agg": "sum",       "format": "integer",     "description_tpl": "Sum of {col}"},
        {"label": "Avg CTR",             "patterns": ["ctr", "click_through_rate", "rate"],        "agg": "mean",      "format": "percent",     "description_tpl": "Average click-through rate from {col}"},
        {"label": "Total Conversions",   "patterns": ["conversion", "conversions", "leads"],        "agg": "sum",       "format": "integer",     "description_tpl": "Sum of {col}"},
    ],
    "hr": [
        {"label": "Total Employees",     "patterns": ["employee_id", "emp_id", "staff_id"],         "agg": "count_rows","format": "integer",     "description_tpl": "Headcount from {col}"},
        {"label": "Avg Salary",          "patterns": ["salary", "wage", "pay", "compensation"],     "agg": "mean",      "format": "currency",    "description_tpl": "Average of {col}"},
        {"label": "Attrition Count",     "patterns": ["attrition", "turnover", "left", "resigned"],"agg": "sum",       "format": "integer",     "description_tpl": "Sum of {col}"},
        {"label": "Unique Departments",  "patterns": ["department", "dept", "team"],                "agg": "nunique",   "format": "integer",     "description_tpl": "Distinct values in {col}"},
    ],
    "finance": [
        {"label": "Total Revenue",       "patterns": ["revenue", "income"],                         "agg": "sum",       "format": "currency",    "description_tpl": "Sum of {col}"},
        {"label": "Total Expenses",      "patterns": ["expense", "cost", "expenditure"],            "agg": "sum",       "format": "currency",    "description_tpl": "Sum of {col}"},
        {"label": "Net Income",          "patterns": ["net_income", "net_profit", "profit"],        "agg": "sum",       "format": "currency",    "description_tpl": "Sum of {col}"},
        {"label": "Total Transactions",  "patterns": ["transaction_id", "entry_id", "id"],          "agg": "count_rows","format": "integer",     "description_tpl": "Number of records in {col}"},
    ],
    "inventory": [
        {"label": "Total SKUs",          "patterns": ["sku", "item_id", "product_id"],              "agg": "count_rows","format": "integer",     "description_tpl": "Unique items from {col}"},
        {"label": "Total Stock Units",   "patterns": ["quantity", "stock", "on_hand", "qty"],       "agg": "sum",       "format": "integer",     "description_tpl": "Sum of {col}"},
        {"label": "Avg Unit Price",      "patterns": ["price", "unit_price", "cost"],               "agg": "mean",      "format": "currency",    "description_tpl": "Average of {col}"},
        {"label": "Low Stock Items",     "patterns": ["reorder", "reorder_point"],                  "agg": "count_rows","format": "integer",     "description_tpl": "Items near reorder threshold in {col}"},
    ],
    "customer_support": [
        {"label": "Total Tickets",       "patterns": ["ticket_id", "case_id", "issue_id", "id"],   "agg": "count_rows","format": "integer",     "description_tpl": "Ticket count from {col}"},
        {"label": "Avg Response Time",   "patterns": ["response_time", "resolution_time", "handle_time"], "agg": "mean","format": "decimal",   "description_tpl": "Average of {col}"},
        {"label": "Avg CSAT Score",      "patterns": ["csat", "satisfaction", "rating", "nps"],    "agg": "mean",      "format": "decimal",     "description_tpl": "Average satisfaction from {col}"},
        {"label": "Escalated Cases",     "patterns": ["escalation", "escalated", "priority"],       "agg": "sum",       "format": "integer",     "description_tpl": "Sum of {col}"},
    ],
    "operations": [
        {"label": "Total Records",       "patterns": ["id", "record_id", "entry_id"],               "agg": "count_rows","format": "integer",     "description_tpl": "Total operational records in {col}"},
        {"label": "Avg Efficiency",      "patterns": ["efficiency", "utilization", "oee"],          "agg": "mean",      "format": "percent",     "description_tpl": "Average efficiency from {col}"},
        {"label": "Total Downtime",      "patterns": ["downtime", "idle_time", "outage"],           "agg": "sum",       "format": "decimal",     "description_tpl": "Sum of downtime in {col}"},
        {"label": "Total Throughput",    "patterns": ["throughput", "output", "volume"],            "agg": "sum",       "format": "integer",     "description_tpl": "Sum of {col}"},
    ],
    "healthcare": [
        {"label": "Total Patients",      "patterns": ["patient_id", "patient", "record_id"],        "agg": "count_rows","format": "integer",     "description_tpl": "Patient count from {col}"},
        {"label": "Avg Length of Stay",  "patterns": ["length_of_stay", "los", "days", "duration"],"agg": "mean",      "format": "decimal",     "description_tpl": "Average stay duration from {col}"},
        {"label": "Readmissions",        "patterns": ["readmission", "readmit"],                    "agg": "sum",       "format": "integer",     "description_tpl": "Sum of {col}"},
        {"label": "Unique Diagnoses",    "patterns": ["diagnosis", "condition", "icd"],             "agg": "nunique",   "format": "integer",     "description_tpl": "Distinct values in {col}"},
    ],
    "education": [
        {"label": "Total Students",      "patterns": ["student_id", "student", "enrollment_id"],    "agg": "count_rows","format": "integer",     "description_tpl": "Enrollment count from {col}"},
        {"label": "Avg Score",           "patterns": ["score", "grade", "gpa", "mark", "result"],  "agg": "mean",      "format": "decimal",     "description_tpl": "Average score from {col}"},
        {"label": "Avg Attendance",      "patterns": ["attendance", "present", "absent"],           "agg": "mean",      "format": "percent",     "description_tpl": "Average attendance from {col}"},
        {"label": "Unique Courses",      "patterns": ["course", "subject", "class"],                "agg": "nunique",   "format": "integer",     "description_tpl": "Distinct values in {col}"},
    ],
}

# Generic fallback — used when domain is "generic" or the primary domain yields < 2 KPIs
_GENERIC_KPI_CONFIGS: list[dict] = [
    {"label": "Total Rows",     "patterns": [],  "agg": "count_rows", "format": "integer", "description_tpl": "Total records in dataset"},
    {"label": "Numeric Cols",   "patterns": [],  "agg": "count_cols",  "format": "integer", "description_tpl": "Number of numeric columns"},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _col_tokens(name: str) -> set[str]:
    """Lower-case token set for a column name."""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    return {t for t in re.split(r"[\s_\-./|]+", spaced.lower()) if t}


def _match_column(patterns: list[str], df: pd.DataFrame, numeric_only: bool = True) -> str | None:
    """
    Return the first column whose token set intersects any pattern in ``patterns``.
    If ``numeric_only``, restrict to numeric dtype columns.
    """
    candidates = (
        df.select_dtypes(include="number").columns.tolist()
        if numeric_only
        else df.columns.tolist()
    )
    for col in candidates:
        tokens = _col_tokens(col)
        if any(pat in tokens or pat == col.lower() for pat in patterns):
            return col
    return None


def _aggregate(df: pd.DataFrame, col: str | None, agg: str) -> float:
    """Apply ``agg`` to ``col`` in ``df`` and return a float."""
    if agg == "count_rows":
        return float(len(df))
    if agg == "count_cols":
        return float(len(df.select_dtypes(include="number").columns))
    if col is None or col not in df.columns:
        return 0.0
    series = df[col].dropna()
    if series.empty:
        return 0.0
    ops = {
        "sum": series.sum,
        "mean": series.mean,
        "max": series.max,
        "min": series.min,
        "nunique": series.nunique,
    }
    result = ops.get(agg, series.sum)()
    val = float(result)
    return 0.0 if (math.isnan(val) or math.isinf(val)) else val


def _format_value(value: float, fmt: str) -> str:
    """Human-readable formatting for a KPI value."""
    if fmt == "currency":
        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:,.2f}M"
        if abs(value) >= 1_000:
            return f"${value:,.0f}"
        return f"${value:,.2f}"
    if fmt == "percent":
        return f"{value:.1f}%"
    if fmt == "decimal":
        return f"{value:,.2f}"
    # integer
    return f"{int(value):,}"


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------


class KPIDetector:
    """
    Detects and computes domain-appropriate KPIs from a DataFrame.

    All values are derived from actual data — nothing is hardcoded.
    """

    def detect(self, df: pd.DataFrame, domain: str) -> list[dict]:
        """
        Compute KPIs for the given domain.

        Parameters
        ----------
        df     : pd.DataFrame — the uploaded dataset.
        domain : str — detected business domain (from BusinessClassifier).

        Returns
        -------
        list of dicts: ``[{ "label", "value", "raw_value", "description" }]``
            ``value`` is a formatted string; ``raw_value`` is the float.
        """
        configs = _DOMAIN_KPI_CONFIGS.get(domain, [])
        results: list[dict] = []

        for cfg in configs:
            matched_col = _match_column(cfg["patterns"], df) if cfg["patterns"] else None
            raw = _aggregate(df, matched_col, cfg["agg"])
            fmt_val = _format_value(raw, cfg["format"])
            desc = cfg["description_tpl"].format(col=matched_col or "dataset")

            results.append({
                "label": cfg["label"],
                "value": fmt_val,
                "raw_value": raw,
                "description": desc,
            })

        # Pad to at least 4 KPIs using generic fallbacks
        if len(results) < 4:
            results += self._generic_kpis(df, needed=4 - len(results))

        return results[:4]  # frontend expects exactly 4

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    @staticmethod
    def _generic_kpis(df: pd.DataFrame, needed: int) -> list[dict]:
        """Fallback structural KPIs when domain-specific ones are scarce."""
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        fallbacks: list[dict] = []

        for col in numeric_cols[:needed]:
            series = df[col].dropna()
            if series.empty:
                continue
            raw = float(series.sum())
            fallbacks.append({
                "label": f"Total {col.replace('_', ' ').title()}",
                "value": _format_value(raw, "decimal"),
                "raw_value": raw,
                "description": f"Sum of column '{col}'",
            })

        # If still short, add row count
        if len(fallbacks) < needed:
            raw = float(len(df))
            fallbacks.append({
                "label": "Total Rows",
                "value": _format_value(raw, "integer"),
                "raw_value": raw,
                "description": "Total number of records in the dataset",
            })

        return fallbacks[:needed]
