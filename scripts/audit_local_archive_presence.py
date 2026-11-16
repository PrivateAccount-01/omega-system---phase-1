"""Read-only, allowlisted, pinned-manifest to archive-presence CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from omegadata.parsers.archive_candidate_inventory import (
    SOURCE_KEY,
    InventoryError,
    read_expected,
    validate_root,
)
from omegadata.parsers.local_archive_presence import ROOTS, request_payload_integrity, scan_presence


def main(argv: list[str] | None = None, *, repo: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, choices=tuple(ROOTS))
    parser.add_argument("--expected-pins", required=True, type=Path)
    parser.add_argument("--source-key", default=SOURCE_KEY)
    parser.add_argument("--dry-run", action="store_true", help="Default; no report writes")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--payload-integrity", action="store_true")
    parser.add_argument("--report-version", type=int, choices=(1, 2), default=2)
    args = parser.parse_args(argv)
    repo = repo if repo is not None else Path(__file__).resolve().parents[1]
    try:
        if args.source_key != SOURCE_KEY:
            raise InventoryError("SOURCE_SCOPE")
        if args.payload_integrity:
            request_payload_integrity(args.root)
        dest = args.output_dir
        if args.dry_run and dest is not None:
            raise InventoryError("OUTPUT_UNSAFE")
        if dest is not None:
            if (
                not dest.is_absolute()
                or dest.exists()
                or dest.is_relative_to(repo)
                or repo.is_relative_to(dest)
            ):
                raise InventoryError("OUTPUT_UNSAFE")
            validate_root(dest.parent, dest.parent)
        if not args.expected_pins.is_absolute() or args.expected_pins.is_relative_to(repo / "data"):
            raise InventoryError("EXTERNAL_PINS_REQUIRED")
        report = scan_presence(
            repo,
            args.root,
            expected=read_expected(args.expected_pins),
            source_key=args.source_key,
            version=args.report_version,
        )
        text = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        if dest is not None:
            dest.mkdir(exist_ok=False, mode=0o700)
            with (dest / "presence.json").open("x", encoding="utf-8") as stream:
                stream.write(text + "\n")
        print(text)
        if args.report_version == 2:
            return 0 if report["counts"]["size_matches_manifest"] == report["manifest_count"] else 2
        return 0 if report["states"] == {"PRESENT_SIZE_MATCHED": report["manifest_count"]} else 2
    except InventoryError as error:
        print(
            json.dumps(
                {"state": "REFUSED", "reason_code": error.reason_code, "payload_bytes_read": 0}
            )
        )
        return 2
    except OSError:
        print('{"state":"REFUSED","reason_code":"METADATA_IO_REFUSED","payload_bytes_read":0}')
        return 2


if __name__ == "__main__":
    sys.exit(main())
