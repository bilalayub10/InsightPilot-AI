"""
InsightPilot AI — Ingest Service.

Responsible for:
  - Saving uploaded file bytes to the local uploads/ directory.
  - Writing a JSON sidecar (``{dataset_id}.meta.json``) so the
    /analyze route can look up the file by datasetId.
  - Returning lightweight metadata so the upload route can call
    AnalyticsService without needing to know file-system details.
"""

import json
import uuid
from pathlib import Path

# Uploads directory is relative to the backend root (where start.sh runs).
UPLOADS_DIR = Path(__file__).parent.parent / "uploads"


class IngestService:
    """
    Saves an uploaded file and records its metadata sidecar.
    """

    def __init__(self):
        # Ensure the uploads directory exists on first use.
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    def ingest(self, file_bytes: bytes, filename: str) -> dict:
        """
        Persist ``file_bytes`` to disk under a new dataset ID.

        Parameters
        ----------
        file_bytes : bytes
            Raw content of the uploaded file.
        filename : str
            Original filename from the multipart upload (used for the
            stored file name so the extension is preserved).

        Returns
        -------
        dict with keys:
            dataset_id  — UUID string identifying this dataset.
            file_path   — Absolute path to the saved file.
            filename    — Original filename.
        """
        dataset_id = str(uuid.uuid4())

        # Sanitise filename: strip path separators to prevent traversal attacks.
        safe_name = Path(filename).name or "dataset.csv"
        stored_name = f"{dataset_id}_{safe_name}"
        file_path = UPLOADS_DIR / stored_name

        # Write the file bytes.
        file_path.write_bytes(file_bytes)

        # Write a sidecar so /analyze can resolve datasetId → file_path.
        meta = {
            "dataset_id": dataset_id,
            "file_path": str(file_path),
            "filename": safe_name,
        }
        meta_path = UPLOADS_DIR / f"{dataset_id}.meta.json"
        meta_path.write_text(json.dumps(meta, indent=2))

        return meta

    @staticmethod
    def resolve(dataset_id: str) -> dict:
        """
        Look up a previously ingested dataset by its ID.

        Returns the same dict that ``ingest`` returned, or raises
        FileNotFoundError if the metadata sidecar is missing.
        """
        meta_path = UPLOADS_DIR / f"{dataset_id}.meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(
                f"No metadata found for dataset '{dataset_id}'. "
                "The file may not have been uploaded yet."
            )
        return json.loads(meta_path.read_text())
