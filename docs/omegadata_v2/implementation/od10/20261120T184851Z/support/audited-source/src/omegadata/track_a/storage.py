from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from omegadata.config import settings


@dataclass(frozen=True)
class StoredDataset:
    dataset_name: str
    as_of: date
    path: Path
    rows: int


class ParquetStorage:
    def __init__(self) -> None:
        self.parquet_root = Path(settings.parquet_root)
        self.parquet_root.mkdir(parents=True, exist_ok=True)

    def store_daily(self, dataset_name: str, as_of: date, frame: pd.DataFrame) -> StoredDataset:
        if frame.empty:
            raise ValueError(f"Refusing to store empty dataset for {dataset_name} on {as_of}")
        out_dir = (
            self.parquet_root
            / dataset_name
            / f"year={as_of.year:04d}"
            / f"month={as_of.month:02d}"
            / f"day={as_of.day:02d}"
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "part-00000.parquet"
        frame.to_parquet(out_path, index=False)
        return StoredDataset(dataset_name=dataset_name, as_of=as_of, path=out_path, rows=len(frame))
