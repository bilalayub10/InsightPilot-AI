"""
InsightPilot AI — FileLoader Service.

Single responsibility: accept raw file bytes + original filename, detect
the file type, load the data into a clean Pandas DataFrame, validate it,
and return the DataFrame alongside lightweight file metadata.

All downstream services (AnalyticsService, BusinessClassifier, KPIDetector,
ChartPlanner, etc.) receive only a DataFrame — they never know whether the
source was CSV or Excel.
"""

import io
from pathlib import Path
from typing import Optional

import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


class FileLoaderError(ValueError):
    """Raised for any problem loading or validating the file."""


class FileLoader:
    """
    Load a CSV or Excel upload into a normalised Pandas DataFrame.

    Usage
    -----
    loader = FileLoader()
    df, meta = loader.load_bytes(file_bytes, "Sales_Report.xlsx")
    # meta = {"file_type": "Excel (.xlsx)", "worksheet_name": "Sheet1"}

    df, meta = loader.load_path("/uploads/abc_dataset.csv")
    # meta = {"file_type": "CSV", "worksheet_name": None}
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_bytes(self, file_bytes: bytes, filename: str) -> tuple[pd.DataFrame, dict]:
        """
        Load raw upload bytes into a DataFrame.

        Parameters
        ----------
        file_bytes : bytes
            Raw multipart upload content.
        filename : str
            Original filename (used only for extension detection).

        Returns
        -------
        (df, metadata)
            df       — normalised DataFrame.
            metadata — dict with ``file_type`` and ``worksheet_name``.

        Raises
        ------
        FileLoaderError
            For unsupported formats, empty files, parse failures, etc.
        """
        if not file_bytes:
            raise FileLoaderError("Empty file.")

        ext = self._extension(filename)
        buf = io.BytesIO(file_bytes)

        if ext == ".csv":
            df = self._read_csv(buf, filename)
            meta = {"file_type": "CSV", "worksheet_name": None}
        else:
            df, sheet_name = self._read_excel(buf, filename, ext)
            label = "Excel (.xlsx)" if ext == ".xlsx" else "Excel (.xls)"
            meta = {"file_type": label, "worksheet_name": sheet_name}

        df = self._normalize(df)
        self._validate(df, filename)
        return df, meta

    def load_path(self, file_path: str) -> tuple[pd.DataFrame, dict]:
        """
        Load a previously saved file from disk into a DataFrame.

        Parameters
        ----------
        file_path : str
            Absolute path to the stored file.

        Returns
        -------
        (df, metadata)  — same shape as ``load_bytes``.

        Raises
        ------
        FileLoaderError
            If the file is missing, unsupported, or cannot be parsed.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileLoaderError(f"Dataset file not found: {file_path}")

        file_bytes = path.read_bytes()
        return self.load_bytes(file_bytes, path.name)

    # ------------------------------------------------------------------
    # Private — format detection
    # ------------------------------------------------------------------

    @staticmethod
    def _extension(filename: str) -> str:
        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise FileLoaderError(
                f"Unsupported file type '{ext or '(none)'}'. "
                "Please upload a .csv, .xlsx, or .xls file."
            )
        return ext

    # ------------------------------------------------------------------
    # Private — readers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_csv(buf: io.BytesIO, filename: str) -> pd.DataFrame:
        try:
            return pd.read_csv(buf, low_memory=False)
        except Exception as exc:
            raise FileLoaderError(f"Unable to parse CSV file '{filename}': {exc}") from exc

    @staticmethod
    def _read_excel(buf: io.BytesIO, filename: str, ext: str) -> tuple[pd.DataFrame, str]:
        """
        Open an Excel workbook and return the first non-empty sheet.

        Returns (DataFrame, sheet_name).  The architecture intentionally
        exposes ``sheet_name`` so future versions can add sheet selection.
        """
        # Choose the right engine: openpyxl for modern XLSX, xlrd for legacy XLS.
        engine: Optional[str] = "openpyxl" if ext == ".xlsx" else "xlrd"

        try:
            xl = pd.ExcelFile(buf, engine=engine)
        except Exception as exc:
            raise FileLoaderError(
                f"Unable to parse Excel workbook '{filename}': {exc}"
            ) from exc

        if not xl.sheet_names:
            raise FileLoaderError("Workbook contains no readable sheets.")

        for sheet_name in xl.sheet_names:
            try:
                df = xl.parse(sheet_name)
            except Exception:
                continue
            if not df.empty and len(df) > 0:
                return df, str(sheet_name)

        raise FileLoaderError("Workbook contains no readable sheets.")

    # ------------------------------------------------------------------
    # Private — normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply lightweight normalisation before handing the DataFrame
        to any downstream service.  Data *values* are never changed
        unless strictly necessary for parsing.
        """
        # 1. Trim whitespace from column names
        df.columns = [str(c).strip() for c in df.columns]

        # 2. Deduplicate column names (append _1, _2, … suffix)
        seen: dict[str, int] = {}
        new_cols: list[str] = []
        for col in df.columns:
            if col in seen:
                seen[col] += 1
                new_cols.append(f"{col}_{seen[col]}")
            else:
                seen[col] = 0
                new_cols.append(col)
        df.columns = new_cols

        # 3. Convert object columns that look like dates to datetime.
        #    Only convert when the majority of non-null values parse successfully.
        for col in df.select_dtypes(include="object").columns:
            try:
                converted = pd.to_datetime(df[col], errors="coerce")
                non_null = df[col].notna().sum()
                if non_null > 0 and converted.notna().sum() / non_null >= 0.8:
                    df[col] = converted
            except Exception:
                pass  # leave the column as-is

        # 4. Preserve numeric dtypes — no coercion needed; pandas keeps them.
        # 5. Preserve boolean values — pandas reads them natively from CSV/Excel.

        return df

    # ------------------------------------------------------------------
    # Private — validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(df: pd.DataFrame, filename: str) -> None:
        if len(df) == 0:
            raise FileLoaderError(
                f"Dataset '{filename}' is empty — no data rows found."
            )
        if len(df.columns) == 0:
            raise FileLoaderError(
                f"Dataset '{filename}' has no columns."
            )
