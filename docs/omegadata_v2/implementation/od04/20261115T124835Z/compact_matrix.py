"""Compact only derived matrix; authoritative command/raw logs stay unchanged."""
import json
from pathlib import Path

path=Path(__file__).resolve().parent/'logs/acceptance-matrix.json'
data=json.loads(path.read_text())
keys={'command','cwd','baseline','platform','python','start_utc','end_utc','elapsed_seconds','exit_code','output'}
for row in data:
    row['commands']=[{k:v for k,v in command.items() if k in keys} for command in row['commands']]
path.write_text(json.dumps(data,indent=2),encoding='utf-8')
print('Derived A01-A28 matrix compacted; raw command evidence preserved.')
