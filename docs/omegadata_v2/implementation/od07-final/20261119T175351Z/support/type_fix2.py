from pathlib import Path
p=Path('/home/parilrupani/omega-od07-final-20261119T175351Z/staged2/repo/src/omegadata/adjustments/bound_contracts.py')
s=p.read_text().replace('            evidence: Evidence,','            evidence,').replace('        evidence,\n        source_version: str,','        evidence: Evidence,\n        source_version: str,');p.write_text(s)
