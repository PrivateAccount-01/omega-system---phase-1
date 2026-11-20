from pathlib import Path
B=Path('/home/parilrupani/omega-od08-20261119T184624Z')
for n in ['reviewed-new-tests.json','new-test-classification-review.json']:
 p=B/n;p.rename(B/(p.stem+'-88-historical'+p.suffix))
p=B/'review_inventory.py';s=p.read_text().replace('assert len(nodes)==88','assert len(nodes)==92');p.write_text(s)
