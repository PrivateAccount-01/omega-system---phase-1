from pathlib import Path
p=Path('/home/parilrupani/omega-od07-final-20261119T175351Z/staged2/repo/src/omegadata/adjustments/bound_chain.py');s=p.read_text().replace('tradability = past.lifecycle if past is not None else "UNKNOWN"','tradability = (past.lifecycle or "UNKNOWN") if past is not None else "UNKNOWN"');p.write_text(s)
