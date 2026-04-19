from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from omegadata.config import settings


@dataclass(frozen=True)
class WarehouseSyncResult:
    status: str
    details: str


class ClickHouseWarehouseSync:
    def sync_release_manifest(
        self,
        *,
        release_id: str,
        release_profile: str,
        as_of_date: date,
        dataset_entries: list[dict[str, Any]],
    ) -> WarehouseSyncResult:
        try:
            import clickhouse_connect  # type: ignore[import-untyped]
        except Exception as exc:  # noqa: BLE001
            return WarehouseSyncResult(status="FAILED", details=f"clickhouse-connect unavailable: {exc}")

        try:
            client = clickhouse_connect.get_client(
                host=settings.clickhouse_host,
                port=settings.clickhouse_port,
                username=settings.clickhouse_user,
                password=settings.clickhouse_password,
                database=settings.clickhouse_database,
                secure=settings.clickhouse_secure,
            )
            client.command(
                """
                CREATE TABLE IF NOT EXISTS omegadata_release_manifest
                (
                    release_id String,
                    release_profile String,
                    as_of_date Date,
                    dataset_name String,
                    row_count UInt64,
                    checksum String,
                    storage_path String,
                    generated_at DateTime DEFAULT now()
                )
                ENGINE = MergeTree
                ORDER BY (release_id, dataset_name)
                """
            )
            rows = [
                [
                    release_id,
                    release_profile,
                    as_of_date,
                    str(entry.get("dataset_name", "")),
                    int(entry.get("row_count", 0)),
                    str(entry.get("checksum", "")),
                    str(entry.get("storage_path", "")),
                ]
                for entry in dataset_entries
            ]
            if rows:
                client.insert(
                    "omegadata_release_manifest",
                    rows,
                    column_names=[
                        "release_id",
                        "release_profile",
                        "as_of_date",
                        "dataset_name",
                        "row_count",
                        "checksum",
                        "storage_path",
                    ],
                )
            return WarehouseSyncResult(status="SYNCED", details=f"rows_inserted={len(rows)}")
        except Exception as exc:  # noqa: BLE001
            return WarehouseSyncResult(status="FAILED", details=str(exc))
