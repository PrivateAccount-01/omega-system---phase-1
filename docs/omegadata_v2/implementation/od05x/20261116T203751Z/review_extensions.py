import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
here = Path(__file__).parent
root = Path.cwd()
review = json.loads((here / 'inputs/review.json').read_bytes())
review['new_functions'].update({'test_x05_x06_direct_native_calls': 3,
                                'test_x15_new_test_source_pin_is_enforced': 1})
review['new_paths'] = {n: 'tests/unit/test_od05x_native_extensions.py' for n in (
    'test_x05_x06_direct_native_calls', 'test_x15_new_test_source_pin_is_enforced')}
review['new_test_hashes'] = {n: hashlib.sha256((root / n).read_bytes()).hexdigest()
                           for n in ('tests/unit/test_od05x_isolation.py',
                                     'tests/unit/test_od05x_native_extensions.py')}
with (here / 'inputs/review-v2.json').open('x') as f: json.dump(review, f, indent=2)
selection = json.loads((here / 'logs/reviewed-source-selection.json').read_bytes())
for row in selection['files']:
    if row['path'] == 'od05x_inputs/review.json':
        row['source'] = (here / 'inputs/review-v2.json').relative_to(root).as_posix()
selection['files'].append({'path': 'tests/unit/test_od05x_native_extensions.py', 'class': 'CODE',
                           'source': 'tests/unit/test_od05x_native_extensions.py'})
selection['file_count'] += 1
selection['utc'] = datetime.now(UTC).isoformat()
selection['new_tests_explicit_A'] = review['new_functions']
with (here / 'logs/reviewed-source-selection-v2.json').open('x') as f: json.dump(selection, f, indent=2)
print('Explicit source review: 33 new cases; four added negative-first cases before correction.')
