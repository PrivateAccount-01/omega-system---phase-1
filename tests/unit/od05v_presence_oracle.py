"""Separate stdlib stat oracle; reads pinned manifest JSON, never market bytes."""

import json
import os
import stat
from pathlib import Path


def observe(repo, groups):
    output = {}
    for label, group in groups.items():
        root = repo / group["repository_root"]
        names = []
        stack = [root]
        while stack:
            directory = stack.pop()
            with os.scandir(directory) as entries:
                for entry in entries:
                    info = entry.stat(follow_symlinks=False)
                    assert not stat.S_ISLNK(info.st_mode)
                    if stat.S_ISDIR(info.st_mode):
                        stack.append(Path(entry.path))
                    elif entry.name.endswith(".manifest.json"):
                        names.append(Path(entry.path).relative_to(root).as_posix())
        assert sorted(names) == sorted(row[0] for row in group["entries"])
        rows = []
        for name in sorted(names):
            meta = json.loads((root / name).read_text(encoding="utf-8"))
            path = repo / meta["artifact_path"].replace("\\", "/")
            try:
                info = path.lstat()
                present = stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                length = info.st_size if present else None
            except FileNotFoundError:
                present, length = False, None
            rows.append(
                {
                    "manifest": name,
                    "date": meta["as_of"],
                    "present": present,
                    "length": length,
                    "size_match": length == meta["bytes_downloaded"],
                }
            )
        output[label] = rows
    return output
