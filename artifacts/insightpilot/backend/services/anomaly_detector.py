"""
InsightPilot AI — Anomaly Detector.

Detects data quality issues and statistical anomalies in a DataFrame using
IQR and Z-score methods. All findings are returned as plain Python dicts —
no external dependencies beyond Pandas and NumPy.
"""

import math
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

IQR_MULTIPLIER = 1.5       # standard outlier fence
ZSCORE_THRESHOLD = 3.0     # values with |z| > 3 are flagged
SKEWNESS_THRESHOLD = 2.0   # absolute skewness above this is "suspicious"
MAX_OUTLIERS_SHOWN = 5     # cap examples per column to keep response concise


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------


class AnomalyDetector:
    """
    Performs lightweight, statistical anomaly detection on a DataFrame.

    Methods are pure functions — the same DataFrame always produces the same result.
    """

    def detect(self, df: pd.DataFrame) -> dict:
        """
        Run all anomaly checks and return a structured findings dict.

        Returns
        -------
        dict with keys:
            unusual_values          — list of per-column outlier findings
            missing_data_warnings   — list of columns with notable missing rates
            duplicate_warning       — dict (or None) describing duplicate rows
            suspicious_distributions— list of per-column distribution findings
        """
        return {
            "unusual_values": self._detect_outliers(df),
            "missing_data_warnings": self._detect_missing(df),
            "duplicate_warning": self._detect_duplicates(df),
            "suspicious_distributions": self._detect_distributions(df),
        }

    # ------------------------------------------------------------------
    # Outlier detection (IQR + Z-score)
    # ------------------------------------------------------------------

    def _detect_outliers(self, df: pd.DataFrame) -> list[dict]:
        """
        Flag outliers in every numeric column using both IQR fences and Z-scores.
        Only columns with at least one outlier by either method are reported.
        """
        findings: list[dict] = []
        numeric_cols = df.select_dtypes(include="number").columns.tolist()

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 4:
                # Too few values for meaningful statistics
                continue

            # --- IQR method ---
            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1
            lower_fence = q1 - IQR_MULTIPLIER * iqr
            upper_fence = q3 + IQR_MULTIPLIER * iqr
            iqr_mask = (series < lower_fence) | (series > upper_fence)
            iqr_outlier_count = int(iqr_mask.sum())

            # --- Z-score method ---
            mean = float(series.mean())
            std = float(series.std(ddof=1))
            if std > 0:
                z_scores = ((series - mean) / std).abs()
                zscore_mask = z_scores > ZSCORE_THRESHOLD
                zscore_outlier_count = int(zscore_mask.sum())
            else:
                zscore_outlier_count = 0

            if iqr_outlier_count == 0 and zscore_outlier_count == 0:
                continue

            # Sample a few example outlier values for the report
            example_values = (
                [self._safe_float(v) for v in series[iqr_mask].head(MAX_OUTLIERS_SHOWN).tolist()]
                if iqr_outlier_count > 0
                else []
            )

            findings.append({
                "column": col,
                "iqr_outliers": iqr_outlier_count,
                "zscore_outliers": zscore_outlier_count,
                "lower_fence": self._safe_float(lower_fence),
                "upper_fence": self._safe_float(upper_fence),
                "example_values": example_values,
                "severity": self._outlier_severity(iqr_outlier_count, len(series)),
                "message": (
                    f"'{col}' has {iqr_outlier_count} outlier(s) outside the IQR fence "
                    f"[{self._safe_float(lower_fence):.2g}, {self._safe_float(upper_fence):.2g}]."
                ),
            })

        return findings

    # ------------------------------------------------------------------
    # Missing data
    # ------------------------------------------------------------------

    def _detect_missing(self, df: pd.DataFrame) -> list[dict]:
        """
        Report columns where the missing-value rate exceeds 1%.
        """
        warnings: list[dict] = []
        total_rows = len(df)
        if total_rows == 0:
            return warnings

        for col in df.columns:
            missing_count = int(df[col].isnull().sum())
            if missing_count == 0:
                continue
            rate = missing_count / total_rows
            warnings.append({
                "column": col,
                "missing_count": missing_count,
                "missing_rate": round(rate * 100, 2),
                "severity": "high" if rate > 0.20 else ("medium" if rate > 0.05 else "low"),
                "message": (
                    f"'{col}' is missing {missing_count:,} value(s) "
                    f"({rate * 100:.1f}% of rows)."
                ),
            })

        return sorted(warnings, key=lambda w: -w["missing_count"])

    # ------------------------------------------------------------------
    # Duplicate rows
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_duplicates(df: pd.DataFrame) -> dict | None:
        """
        Return a summary if duplicate rows are present, otherwise None.
        """
        dupe_count = int(df.duplicated().sum())
        if dupe_count == 0:
            return None

        rate = dupe_count / len(df) if len(df) > 0 else 0
        return {
            "duplicate_rows": dupe_count,
            "duplicate_rate": round(rate * 100, 2),
            "severity": "high" if rate > 0.10 else ("medium" if rate > 0.02 else "low"),
            "message": (
                f"{dupe_count:,} duplicate row(s) detected "
                f"({rate * 100:.1f}% of dataset). "
                "Consider deduplication before analysis."
            ),
        }

    # ------------------------------------------------------------------
    # Suspicious distributions
    # ------------------------------------------------------------------

    def _detect_distributions(self, df: pd.DataFrame) -> list[dict]:
        """
        Flag numeric columns with high skewness or zero variance,
        which can indicate data quality or normality concerns.
        """
        findings: list[dict] = []
        numeric_cols = df.select_dtypes(include="number").columns.tolist()

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 4:
                continue

            std = float(series.std(ddof=1))

            # Zero-variance check
            if std == 0:
                findings.append({
                    "column": col,
                    "issue": "zero_variance",
                    "skewness": 0.0,
                    "severity": "medium",
                    "message": (
                        f"'{col}' has zero variance — all non-null values are identical. "
                        "This column carries no predictive information."
                    ),
                })
                continue

            # Skewness check
            skewness = float(series.skew())
            if math.isnan(skewness) or math.isinf(skewness):
                continue

            if abs(skewness) >= SKEWNESS_THRESHOLD:
                direction = "right" if skewness > 0 else "left"
                findings.append({
                    "column": col,
                    "issue": "high_skewness",
                    "skewness": round(skewness, 3),
                    "severity": "high" if abs(skewness) >= 5 else "medium",
                    "message": (
                        f"'{col}' is strongly {direction}-skewed (skewness={skewness:.2f}). "
                        "Log transformation or outlier review may be needed."
                    ),
                })

        return findings

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_float(value) -> float:
        """Convert to float, replacing NaN/Inf with 0.0."""
        try:
            f = float(value)
            return 0.0 if (math.isnan(f) or math.isinf(f)) else f
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _outlier_severity(count: int, total: int) -> str:
        if total == 0:
            return "low"
        rate = count / total
        return "high" if rate > 0.10 else ("medium" if rate > 0.02 else "low")
