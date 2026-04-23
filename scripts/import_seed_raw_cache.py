from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_REPO_ROOT = REPO_ROOT / "tmp/omega_phase2_seed_repo"
SEED_RAW_ROOT = REPO_ROOT / "data/seed_raw/omega_phase2_repo"
CANONICAL_RAW_ROOT = REPO_ROOT / "data/raw"
OUTPUT_PATH = REPO_ROOT / "artifacts/verification/seed_import_audit.json"
SOURCE_REPO_URL = "https://github.com/PrivateAccount-01/omega-system---phase-2"
PAYLOAD_CLASS = "bhavcopy"
SOURCE_KEY = "nse_equity_bhavcopy"
SEED_SOURCE_TAG = "omega_phase2_repo"
FILENAME_PATTERN = re.compile(r"cm(\d{2})([A-Z]{3})(\d{4})bhav\.csv\.zip$", re.IGNORECASE)
MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _parse_bhavcopy_date(name: str) -> date | None:
    match = FILENAME_PATTERN.match(name)
    if match is None:
        return None
    day = int(match.group(1))
    month = MONTHS[match.group(2).upper()]
    year = int(match.group(3))
    return date(year, month, day)


def _canonical_day_dir(root: Path, as_of: date) -> Path:
    return root / SOURCE_KEY / f"year={as_of.year:04d}" / f"month={as_of.month:02d}"


def _latest_pointer(root: Path, as_of: date) -> Path:
    return _canonical_day_dir(root, as_of) / f"{as_of:%Y%m%d}.latest.json"


def _canonical_exists(as_of: date) -> bool:
    return _latest_pointer(CANONICAL_RAW_ROOT, as_of).exists()


def _seed_exists(as_of: date) -> bool:
    return _latest_pointer(SEED_RAW_ROOT, as_of).exists()


def _validate_seed_archive(path: Path) -> tuple[bool, list[str], str | None]:
    try:
        with zipfile.ZipFile(path) as archive:
            members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if not members:
                return False, ["missing_csv_member"], None
            member = sorted(members)[0]
            payload = archive.read(member)
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8", errors="ignore")))
        headers = {str(value).strip() for value in (reader.fieldnames or [])}
    except Exception as exc:  # noqa: BLE001
        return False, [f"archive_parse_error:{exc}"], None

    valid_header_sets = (
        {"SYMBOL", "SERIES", "OPEN", "HIGH", "LOW", "CLOSE", "TOTTRDQTY", "ISIN"},
        {"TradDt", "BizDt", "ISIN", "TckrSymb", "SctySrs", "OpnPric", "HghPric", "LwPric", "ClsPric", "TtlTradgVol"},
    )
    anomalies: list[str] = []
    if not any(expected.issubset(headers) for expected in valid_header_sets):
        anomalies.append("unexpected_columns")
    return not anomalies, anomalies, member


def _write_seed_artifact(
    *,
    source_path: Path,
    as_of: date,
    checksum: str,
    bytes_downloaded: int,
    csv_member: str | None,
) -> dict[str, object]:
    out_dir = _canonical_day_dir(SEED_RAW_ROOT, as_of)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact_stem = f"{as_of:%Y%m%d}__{checksum[:12]}"
    output = out_dir / f"{artifact_stem}.zip"
    if not output.exists():
        try:
            output.hardlink_to(source_path)
        except OSError:
            shutil.copy2(source_path, output)
    imported_at = datetime.now(UTC).isoformat()
    manifest_payload: dict[str, object] = {
        "source_key": "NSE_EQUITY_BHAVCOPY",
        "as_of": as_of.isoformat(),
        "checksum": checksum,
        "storage_mode": "immutable_seed_cache",
        "artifact_path": _relative(output),
        "bytes_downloaded": bytes_downloaded,
        "used_url": f"seed://{SEED_SOURCE_TAG}/{source_path.relative_to(SEED_REPO_ROOT).as_posix()}",
        "attempts": 0,
        "downloaded_at": imported_at,
        "imported_at": imported_at,
        "source_repo_url": SOURCE_REPO_URL,
        "source_repo_relative_path": source_path.relative_to(SEED_REPO_ROOT).as_posix(),
        "seed_source_tag": SEED_SOURCE_TAG,
        "original_filename": source_path.name,
        "payload_class": PAYLOAD_CLASS,
        "csv_member": csv_member,
    }
    manifest_path = out_dir / f"{artifact_stem}.manifest.json"
    manifest_payload["manifest_path"] = _relative(manifest_path)
    if not manifest_path.exists():
        manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")
    latest_pointer = out_dir / f"{as_of:%Y%m%d}.latest.json"
    latest_pointer.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")
    return manifest_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Import safe raw payloads from the Phase 2 seed repo into a separated seed cache.")
    parser.add_argument("--seed-repo-root", default=str(SEED_REPO_ROOT))
    parser.add_argument("--output-path", default=str(OUTPUT_PATH))
    args = parser.parse_args()

    seed_repo_root = Path(args.seed_repo_root)
    raw_root = seed_repo_root / "data/raw"
    bhavcopy_root = raw_root / "bhavcopy"

    accepted: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    duplicates: list[dict[str, object]] = []

    safe_directories = []
    if bhavcopy_root.exists():
        safe_directories.append("data/raw/bhavcopy")

    ambiguous_directories = []
    for candidate in ("data/raw/fii_dii", "data/raw/india_vix", "data/raw/fo_bhavcopy"):
        if (seed_repo_root / candidate).exists():
            ambiguous_directories.append(candidate)

    for path in sorted(bhavcopy_root.glob("*")):
        if not path.is_file():
            continue
        as_of = _parse_bhavcopy_date(path.name)
        if as_of is None:
            rejected.append(
                {
                    "path": path.relative_to(seed_repo_root).as_posix(),
                    "reason": "unexpected_filename_pattern",
                }
            )
            continue
        valid, anomalies, csv_member = _validate_seed_archive(path)
        if not valid:
            rejected.append(
                {
                    "path": path.relative_to(seed_repo_root).as_posix(),
                    "date": as_of.isoformat(),
                    "reason": "archive_validation_failed",
                    "anomalies": anomalies,
                }
            )
            continue
        payload = path.read_bytes()
        checksum = _sha256_bytes(payload)
        if _canonical_exists(as_of):
            duplicates.append(
                {
                    "path": path.relative_to(seed_repo_root).as_posix(),
                    "date": as_of.isoformat(),
                    "reason": "canonical_raw_already_present",
                    "checksum": checksum,
                }
            )
            continue
        if _seed_exists(as_of):
            duplicates.append(
                {
                    "path": path.relative_to(seed_repo_root).as_posix(),
                    "date": as_of.isoformat(),
                    "reason": "seed_cache_already_present",
                    "checksum": checksum,
                }
            )
            continue
        manifest_payload = _write_seed_artifact(
            source_path=path,
            as_of=as_of,
            checksum=checksum,
            bytes_downloaded=len(payload),
            csv_member=csv_member,
        )
        accepted.append(
            {
                "date": as_of.isoformat(),
                "seed_repo_relative_path": path.relative_to(seed_repo_root).as_posix(),
                "imported_artifact_path": manifest_payload["artifact_path"],
                "checksum": checksum,
                "payload_class": PAYLOAD_CLASS,
            }
        )

    artifact = {
        "generated_at": datetime.now(UTC).isoformat(),
        "seed_repo_url": SOURCE_REPO_URL,
        "seed_repo_root": _relative(seed_repo_root),
        "seed_source_tag": SEED_SOURCE_TAG,
        "safe_raw_directories": safe_directories,
        "ambiguous_or_absent_raw_directories_not_imported": ambiguous_directories or [
            "data/raw/fii_dii",
            "data/raw/india_vix",
            "data/raw/fo_bhavcopy",
        ],
        "forbidden_directories_observed": [
            "data/processed",
            "data/outputs",
        ],
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "duplicate_count": len(duplicates),
        "accepted_files": accepted,
        "rejected_files": rejected,
        "duplicate_files": duplicates,
        "note": (
            "Only raw archived NSE equity bhavcopy payloads were imported from the seed repo. "
            "Processed outputs, research artifacts, summaries, and ambiguous non-bhavcopy raw trees were excluded."
        ),
    }
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
