"""Copy only exact locally reviewed regression fixture dependencies; never keys."""
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

import phase_control as ctl

info=json.loads((ctl.LOGS/"sanitized-copy.json").read_text())
target=Path(info["windows_copy"])
corpus=json.loads(Path("tests/fixtures/official_source/adjustment_reference_corpus.json").read_text())
pack=json.loads(Path("tests/fixtures/synthetic_seed/pit_universe_seed_pack.json").read_text())
paths=set()
for case in corpus["cases"]:
    paths.add(case["snapshot_path"])
    paths.update(case["price_paths"])
needed={str(item["symbol"]).upper() for item in pack["security_master"]}
covered=set(pack["symbol_isin_overrides"])


def symbols(p):
    with zipfile.ZipFile(p) as zf:
        names=[n for n in zf.namelist() if n.lower().endswith(".csv")]
        with zf.open(names[0]) as raw:
            return {str(row.get("SYMBOL") or row.get("TckrSymb") or "").strip().upper()
                for row in csv.DictReader(io.TextIOWrapper(raw,encoding="utf-8"))}


for name in sorted(paths):
    if name.endswith(".zip"):
        covered.update(symbols(Path(name)))
for p in sorted(Path("data/raw/nse_equity_bhavcopy").glob("year=*/month=*/*.zip")):
    if needed <= covered:break
    available=symbols(p)
    if (needed-covered)&available:
        paths.add(p.as_posix())
        covered.update(available)
assert needed <= covered, sorted(needed-covered)
records=[]
for name in sorted(paths):
    p=Path(name)
    assert not p.is_absolute() and ".." not in p.parts and p.parts[0] in {"data","tests"}
    assert p.parts[:2] != ("artifacts","gnupg")
    body=p.read_bytes()
    out=target/p
    if not out.is_file():
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_bytes(body)
    assert out.read_bytes()==body
    records.append({"path":name,"sha256":hashlib.sha256(body).hexdigest(),"bytes":len(body),
        "purpose":"existing corpus path/seed-symbol regression dependency; ARCH, not official authenticity certification"})
ctl.save("fixture-allowlist.json",{"files":records,"seed_symbols_covered":len(needed),
    "copy":str(target),"raw_approved_scope":"Local copies only, exact named test dependencies. No provider fetch, manifest/release/key/.env copy."})
print(json.dumps({"copied_or_verified_files":len(records),"bytes":sum(r["bytes"] for r in records)}))
