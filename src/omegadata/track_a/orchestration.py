from __future__ import annotations

from datetime import date

import pandas as pd

from omegadata.track_a.download_manager import DownloadManager
from omegadata.track_a.storage import ParquetStorage


class IngestionOrchestrator:
    def __init__(self) -> None:
        self.download_manager = DownloadManager()
        self.storage = ParquetStorage()

    def ingest_raw_source(self, source_key: str, as_of: date) -> str:
        artifact = self.download_manager.download(source_key=source_key, as_of=as_of)
        return str(artifact.path)

    def ingest_tabular_frame(self, dataset_name: str, as_of: date, frame: pd.DataFrame) -> str:
        stored = self.storage.store_daily(dataset_name=dataset_name, as_of=as_of, frame=frame)
        return str(stored.path)
