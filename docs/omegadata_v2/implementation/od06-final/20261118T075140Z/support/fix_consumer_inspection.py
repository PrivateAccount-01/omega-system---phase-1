from pathlib import Path
B=Path('/home/parilrupani/omega-od06-final-20261118T075140Z')
p=B/'inspect_consumers.py';v=p.read_text().replace("raw=(S/n).read_bytes();raw.decode();read.append", "raw=(Path('/mnt/e/omega system - phase 1')/n).read_bytes();raw.decode();read.append");p.write_text(v)
