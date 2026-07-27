"""
InsightPilot AI — Analytics Service.

Responsible for profiling uploaded datasets using Pandas.
All analysis is pure computation against a local file path — no I/O side effects.
"""

import math
from pathlib import Path
import pandas as pd


class AnalyticsService:
    """
    Stateless analytics service.

    Each method accepts a file path and returns plain Python dicts/lists
    so callers never need to import pandas directly.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def profile_dataframe(self, df: pd.DataFrame) -> dict:
        """
        Profile an already-loaded DataFrame.

        Returns
        -------
        dict with keys:
            row_count, column_count, column_names, data_types,
            missing_values_per_column, total_missing_values,
            duplicate_rows, numeric_columns, categorical_columns,
            datetime_columns, summary_statistics
        """

        # Column type buckets
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
        datetime_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()

        # Missing values per column — convert int64 → int for JSON safety
        missing_per_col: dict[str, int] = {
            col: int(count)
            for col, count in df.isnull().sum().items()
        }

        # summary_statistics via describe() on numeric columns only
        # fillna(0) guards against NaN in min/max for empty columns
        if numeric_cols:
            raw_stats = df[numeric_cols].describe().to_dict()
            summary_stats = {
                col: {k: self._safe_float(v) for k, v in stat.items()}
                for col, stat in raw_stats.items()
            }
        else:
            summary_stats = {}

        return {
            "row_count": int(len(df)),
            "column_count": int(len(df.columns)),
            "column_names": df.columns.tolist(),
            "data_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "missing_values_per_column": missing_per_col,
            "total_missing_values": int(df.isnull().sum().sum()),
            "duplicate_rows": int(df.duplicated().sum()),
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "datetime_columns": datetime_cols,
            "summary_statistics": summary_stats,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load(file_path: str) -> pd.DataFrame:
        """
        Load a CSV file into a DataFrame.

        Raises
        ------
        FileNotFoundError  — if the file does not exist.
        ValueError         — if the file cannot be parsed as CSV.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        try:
            return pd.read_csv(path, low_memory=False)
        except Exception as exc:
            raise ValueError(f"Could not parse CSV file '{path.name}': {exc}") from exc

    @staticmethod
    def _safe_float(value) -> float:
        """Convert a value to float, replacing NaN/Inf with 0.0."""
        try:
            f = float(value)
            return 0.0 if (math.isnan(f) or math.isinf(f)) else f
        except (TypeError, ValueError):
            return 0.0
