"""Fresh permitted manifest read + original payload lstat, never payload open."""
import hashlib
import json
import stat
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
OLD = ROOT/'docs/omegadata_v2/implementation/od05x/20261116T203751Z'
groups = json.loads((OLD/'inputs/groups.json').read_bytes())
previous = json.loads((OLD/'inputs/original-independent-stat.json').read_bytes())['rows']
rows, counts, changes = {}, Counter(), []
for label, group in groups.items():
    for name, digest, length in group['entries']:
        p = ROOT/group['repository_root']/name
        info = p.lstat()
        assert stat.S_ISREG(info.st_mode) and info.st_nlink == 1
        assert not getattr(info,'st_file_attributes',0)&0x400
        raw = p.read_bytes()
        assert len(raw)==length and hashlib.sha256(raw).hexdigest()==digest
        meta = json.loads(raw)
        relative = meta['artifact_path'].replace('\\','/')
        assert relative.startswith(group['repository_root']+'/') and '..' not in Path(relative).parts
        target = ROOT/relative
        for ancestor in target.parents:
            if ancestor == ROOT.parent:
                break
            st = ancestor.lstat()
            assert stat.S_ISDIR(st.st_mode) and not getattr(st,'st_file_attributes',0)&0x400
        st = target.lstat()  # NEVER open/hash payload
        row = {'size':st.st_size,'mtime_ns':st.st_mtime_ns,'ino':st.st_ino,'nlink':st.st_nlink,
               'matched':st.st_size==meta['bytes_downloaded'],
               'regular':stat.S_ISREG(st.st_mode) and not getattr(st,'st_file_attributes',0)&0x400,
               'group':label}
        assert relative not in rows
        rows[relative]=row
        if row != previous[relative]:
            changes.append(relative)
        counts[label]+=1
        counts['present']+=int(row['regular'])
        counts['size_matched']+=int(row['matched'])
        counts['hardlinked' if st.st_nlink>1 else 'single_link']+=1
assert set(rows)==set(previous)
name='original-stat-before.json' if not (HERE/'logs/original-stat-before.json').exists() else 'original-stat-after.json'
report={'utc':datetime.now(UTC).isoformat(),'class':'LOCAL_META_LSTAT_ONLY','rows':rows,
        'counts':dict(counts),'comparison':'ARCH_TO_RUN' if name.endswith('before.json') else 'RUN_TO_RUN',
        'historical_stat_changes':changes,'payload_bytes_opened_hashed_copied':0,
        'verified_market_rows':0,'content_inspection_eligibility':False}
if name.endswith('after.json'):
    before=json.loads((HERE/'logs/original-stat-before.json').read_bytes())
    report['run_stat_changes']=[n for n in rows if rows[n]!=before['rows'][n]]
with (HERE/'logs'/name).open('x') as f:
    json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
