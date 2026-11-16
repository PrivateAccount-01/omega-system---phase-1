"""Explicit metadata-only CLI; no source-data acquisition or financial acceptance."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from omegadata.parsers.archive_candidate_inventory import (
    SOURCE_KEY,
    InventoryError,
    ledger,
    read_expected,
    scan_metadata,
    validate_root,
)


def main(argv: list[str] | None = None, *, allowed_roots: tuple[Path, ...] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-root", required=True, type=Path)
    parser.add_argument("--expected-pins", required=True, type=Path)
    parser.add_argument("--source-key", default=SOURCE_KEY)
    parser.add_argument("--business-date-start")
    parser.add_argument("--business-date-end")
    parser.add_argument("--metadata-only", action="store_true", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--require-real-data", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    repo = Path(__file__).resolve().parents[1]
    roots = (
        allowed_roots
        if allowed_roots is not None
        else (
            repo / "data/raw/nse_equity_bhavcopy",
            repo / "data/seed_raw/omega_phase2_repo/nse_equity_bhavcopy",
        )
    )
    try:
        root = args.manifest_root
        matching = [p for p in roots if root.is_absolute() and root.is_relative_to(p)]
        if not matching:
            raise InventoryError("PATH_UNSAFE")
        validate_root(root, matching[0])
        if args.expected_pins.is_relative_to(root):
            raise InventoryError("EXTERNAL_PINS_REQUIRED")
        if not args.dry_run:
            dest = args.output_dir
            if dest is None or not dest.is_absolute() or dest.exists() or dest.is_relative_to(repo):
                raise InventoryError("OUTPUT_UNSAFE")
            validate_root(dest.parent, dest.parent)
            if any(dest.is_relative_to(p) or p.is_relative_to(dest) for p in roots):
                raise InventoryError("OUTPUT_UNSAFE")
        expected = read_expected(args.expected_pins)
        result = scan_metadata(
            root,
            approved_root=matching[0],
            expected=expected,
            source_key=args.source_key,
            business_date_start=args.business_date_start,
            business_date_end=args.business_date_end,
        )
        report = ledger(result)
        text = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        if not args.dry_run:
            args.output_dir.mkdir(exist_ok=False)
            with (args.output_dir / "inventory.json").open("x", encoding="utf-8") as stream:
                stream.write(text + "\n")
        print(text)
        return 3 if args.require_real_data else (2 if result.errors or not result.rows else 0)
    except InventoryError as error:
        print(
            json.dumps(
                {
                    "state": "REFUSED",
                    "reason_code": error.reason_code,
                    "payload_bytes_read": 0,
                    "market_rows_parsed": 0,
                    "market_rows_independently_verified": 0,
                    "official_reference_verified": 0,
                }
            )
        )
        return 2
    except OSError:
        print('{"state":"REFUSED","reason_code":"METADATA_IO_REFUSED"}')
        return 2


if __name__ == "__main__":
    sys.exit(main())
