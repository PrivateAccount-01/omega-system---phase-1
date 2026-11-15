"""Read-only, rights-aware raw commit verification. Never acquire or repair data."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

from omegadata.track_a.raw_archive import RawArchive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("observation_id")
    parser.add_argument("source_key")
    parser.add_argument("business_date", type=date.fromisoformat)
    parser.add_argument("--expected-count", type=int, help="Separately pinned number of committed observations; ALL only")
    args = parser.parse_args()
    if args.observation_id == "ALL":
        print(json.dumps(RawArchive(args.root).scan_verified(
            args.source_key, args.business_date, expected_count=args.expected_count), sort_keys=True))
        return
    if args.expected_count is not None:
        parser.error("--expected-count requires ALL")
    data, observation = RawArchive(args.root).read_verified(
        args.observation_id, args.source_key, args.business_date
    )
    print(json.dumps({"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                      "observation": observation.model_dump(mode="json")}, sort_keys=True))


if __name__ == "__main__":
    main()
