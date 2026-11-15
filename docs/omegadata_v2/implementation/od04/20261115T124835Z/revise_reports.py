"""Refresh derived reports only; preserve every original command and gate log."""
import json
import report

note='''

## Corpus verifier correction and authoritative evidence

The first post-process Linux independent scan returned 0 observations/0 objects
after WSL removed the fresh /tmp corpus on session shutdown. This was a harness
verification defect: a missing root could pass vacuously. The retained
[old scan](logs/linux-corpus-reference.txt) and first final-preservation.json do
not prove persistent corpus completeness. The strengthened scanner requires an
existing root and exactly 18 commits/13 object files. Its
[missing-evidence negative](logs/linux-missing-corpus-negative.json) exits nonzero.
Linux process experiments were rerun in a fresh private native /home directory;
[new process commands](logs/linux-process-persistent.json) exit 0 and the
[independent persistent scan](logs/linux-corpus-persistent.txt) verifies all 18/13.
No old experiment or original data was deleted by this task. Both earlier logs
remain intact; this correction does not waive the separate Gate 2 chronology
block. Application/test source did not change for this harness correction.
'''

def write(name,text):
    assert name in report.REQUIRED and name!='02_architecture_and_contracts.md'
    text=text.replace('linux-process-accepted','linux-process-persistent').replace('linux-corpus-reference','linux-corpus-persistent').replace('final-preservation.json','final-preservation-reviewed.json')
    if name in {'05_concurrency_crash_recovery.md','08_metrics_and_reproducibility.md','09_gatekeeper_verdict.md'}:
        text+=note
    (report.HERE/name).write_text(text,encoding='utf-8',newline='\n')

old_save=report.control.save
def save(name,data):
    if name in {'acceptance-matrix.json','metrics.json'}:
        (report.LOGS/name).write_text(json.dumps(data,indent=2),encoding='utf-8')
    else:old_save(name,data)

report.write=write
report.control.save=save
report.reports()
raise SystemExit(report.final(reviewed=True))
