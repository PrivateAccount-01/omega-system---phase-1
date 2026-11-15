"""Disposable filesystem/locale capabilities only; no network or app execution."""
import json
import locale
import os
import platform
import tempfile
from datetime import UTC, datetime
from pathlib import Path

root=Path(tempfile.mkdtemp(prefix="omega-od02v-capabilities-",dir=str(Path.home()) if os.name!="nt" else None))
target=root/"CaseProbe.txt"
target.write_text("SYNTHETIC_TEST_ONLY\n",encoding="utf-8")
result={"utc":datetime.now(UTC).isoformat(),"platform":platform.platform(),"root":str(root),
    "locale":locale.getlocale(),"case_sensitive":not (root/"caseprobe.txt").exists(),
    "physical_newlines_hex":target.read_bytes().hex(),"iso_utc_z":datetime.fromisoformat("2026-11-15T00:00:00Z").isoformat()}
link=root/"synthetic-link.txt"
try:
    link.symlink_to(target)
    result["file_symlink"]={"created":link.is_symlink(),"same_bytes":link.read_bytes()==target.read_bytes()}
except OSError as exc:
    result["file_symlink"]={"created":False,"error":str(exc),"winerror":getattr(exc,"winerror",None)}
longpath=root
try:
    while len(str(longpath/"long-path.txt"))<300:longpath=longpath/("synthetic-segment-"+str(len(str(longpath))))
    longpath.mkdir(parents=True)
    p=longpath/"long-path.txt"
    p.write_text("SYNTHETIC_TEST_ONLY")
    result["long_path"]={"characters":len(str(p)),"read_back":p.read_text()=="SYNTHETIC_TEST_ONLY"}
except OSError as exc:
    result["long_path"]={"characters":len(str(longpath)),"error":str(exc)}
print(json.dumps(result,indent=2))
