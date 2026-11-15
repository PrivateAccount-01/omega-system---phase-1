"""Dry-run single legacy candidate mapping; no import, mkdir or pointer update."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

from omegadata.track_a.download_manager import DownloadManager


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("legacy_root", type=Path)
    parser.add_argument("source_key")
    parser.add_argument("business_date", type=date.fromisoformat)
    args = parser.parse_args()
    manager = DownloadManager()
    manager.raw_root = args.legacy_root
    item = manager._load_cached_artifact_from_root(args.legacy_root, args.source_key, args.business_date)
    if item is None:
        raise RuntimeError("LEGACY_CACHE_MISS_OR_INVALID")
    raw = item.path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    print(json.dumps({"action": "DRY_RUN_ONLY", "origin": "LEGACY_UNVERIFIED",
                      "source_key": item.source_key, "date": item.as_of.isoformat(),
                      "relative_legacy_path": str(item.path.relative_to(args.legacy_root.resolve())),
                      "bytes": len(raw), "sha256": digest,
                      "proposed_object": f"objects/sha256/{digest[:2]}/{digest[2:4]}/{digest}",
                      "conflict_policy": "NO_IMPORT_NO_OVERWRITE_OWNER_REVIEW",
                      "reversible_mapping": "retain original pointer and sidecar; new namespace only"}, sort_keys=True))


if __name__ == "__main__":
    main()
