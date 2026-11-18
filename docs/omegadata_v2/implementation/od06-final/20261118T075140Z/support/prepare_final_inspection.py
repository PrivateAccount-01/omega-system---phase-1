from pathlib import Path
B=Path('/home/parilrupani/omega-od06-final-20261118T075140Z')
v=(B/'inspect_consumers.py').read_text().replace('complete-consumer-inventory.json','complete-consumer-inventory-final.json')
(B/'inspect_consumers_final.py').write_text(v)
