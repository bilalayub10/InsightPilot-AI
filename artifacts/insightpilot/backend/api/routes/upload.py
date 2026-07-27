"""
Dataset upload route.

Accepts a multipart CSV or Excel file, saves it via IngestService,
loads it with FileLoader, profiles it via AnalyticsService, and returns
real metadata extracted from the file.

Supported formats: .csv, .xlsx, .xls
"""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional

from models.schemas import UploadResult, DatasetStatus
from services.ingest import IngestService
from services.analytics import AnalyticsService
from services.file_loader import FileLoader, FileLoaderError
from services.business_classifier import BusinessClassifier

router = APIRouter()

# Stateless service singletons.
_ingest = IngestService()
_analytics = AnalyticsService()
_loader = FileLoader()
_classifier = BusinessClassifier()


@router.post("/upload", response_model=UploadResult)
async def upload_dataset(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
) -> UploadResult:
    """
    Accept a CSV or Excel dataset upload.

    1. Read the raw bytes from the multipart body.
    2. Load into a DataFrame via FileLoader (validates format + content).
    3. Persist the file and write a metadata sidecar (IngestService).
    4. Profile the DataFrame with AnalyticsService.
    5. Run a lightweight domain classification (BusinessClassifier).
    6. Return row count, column count, file type, worksheet name, and domain.

    Raises 400 for invalid/unsupported/empty files.
    """
    content = await file.read()
    original_name = file.filename or "dataset.csv"

    # --- Load and validate via FileLoader ---------------------------------
    try:
        df, file_meta = _loader.load_bytes(content, original_name)
    except FileLoaderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}")

    # --- Persist to disk --------------------------------------------------
    try:
        meta = _ingest.ingest(file_bytes=content, filename=original_name)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save uploaded file: {exc}",
        )

    # --- Profile the DataFrame --------------------------------------------
    try:
        profile = _analytics.profile_dataframe(df)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error profiling dataset: {exc}",
        )

    # --- Lightweight domain classification --------------------------------
    try:
        classification = _classifier.classify(profile["column_names"])
        domain = classification["domain"].replace("_", " ").title()
    except Exception:
        domain = None

    size_kb = round(len(content) / 1024, 2)
    display_name = name or original_name

    return UploadResult(
        datasetId=meta["dataset_id"],
        name=display_name,
        rowCount=profile["row_count"],
        columnCount=profile["column_count"],
        columns=profile["column_names"],
        fileSizeKb=size_kb,
        status=DatasetStatus.ready,
        uploadedAt=datetime.now(timezone.utc).isoformat(),
        fileType=file_meta["file_type"],
        worksheetName=file_meta["worksheet_name"],
        domain=domain,
    )
