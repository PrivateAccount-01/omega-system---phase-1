from pathlib import Path
B=Path('/home/parilrupani/omega-od07-20261119T171019Z');p=B/'staged2/repo/src/omegadata/adjustments/chains.py'
v=p.read_text().replace('eligibility, raw_eligibility, select_revisions','eligibility, raw_eligibility, select_revisions, references').replace('from decimal import','from omegadata.identity import query_time\nfrom decimal import')
v=v.replace('    try:inputs=canonical(','''    for action in actions:
        for reference in references(action):
            if reference.known_from is not None:query_time(reference.known_from)
    try:inputs=canonical(''');p.write_text(v)
