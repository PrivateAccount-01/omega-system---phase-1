"""Fresh data-free worker extension; delegates unchanged accepted Linux jobs."""
import contextlib
import io
import json
import os
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path


def run(config):
    if config['job'] == 'r1type':
        import od05x_isolated_runner as boundary
        boundary.assert_boundary()
        os.chdir('/work/repo')
        output = Path('/work/job')
        output.mkdir()
        os.environ['MYPY_CACHE_DIR'] = str(output / 'mypy')
        from mypy import api
        start = datetime.now(UTC).isoformat()
        stdout, stderr, code = api.run(['--follow-imports=silent', 'scripts/od05xr1_windows_backend.py'])
        result = {'job': 'r1type', 'exit_code': code, 'stdout_stderr': stdout + stderr,
                  'start_utc': start, 'end_utc': datetime.now(UTC).isoformat(),
                  'python': sys.version, 'interpreter': sys.executable, 'counts': {}}
        with (output / 'result.json').open('x') as f:
            json.dump(result, f, indent=2)
        return code
    if config['job'] != 'r1':
        import od05x_base_worker_jobs
        return od05x_base_worker_jobs.run(config)
    import od05x_isolated_runner as boundary
    boundary.assert_boundary()
    import coverage
    import pytest
    root = Path('/work/repo')
    os.chdir(root)
    output = Path('/work/job')
    output.mkdir()
    os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    records = []
    class Evidence:
        def pytest_runtest_logreport(self, report):
            if report.when == 'call' or report.failed or report.skipped:
                records.append({'nodeid': report.nodeid, 'outcome': report.outcome,
                                'reason': str(report.longrepr) if report.failed or report.skipped else None})
    capture = io.StringIO()
    cov = coverage.Coverage(source=['od05xr1_windows_backend'], branch=True,
                            data_file=str(output / 'contract.coverage'))
    cov.start()
    start, tick = datetime.now(UTC).isoformat(), time.monotonic()
    with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
        code = int(pytest.main(['-q', '-p', 'no:cacheprovider', '--confcutdir', str(root / 'tests/unit'),
                               '--basetemp', '/work/job/tmp', 'tests/unit/test_od05xr1_windows_contract.py'],
                              plugins=[Evidence()]))
    cov.stop()
    cov.save()
    cov.json_report(outfile=str(output / 'coverage.json'))
    result = {'job': 'r1', 'start_utc': start, 'end_utc': datetime.now(UTC).isoformat(),
              'elapsed_seconds': time.monotonic()-tick, 'exit_code': code,
              'interpreter': sys.executable, 'python': sys.version, 'reports': records,
              'counts': dict(Counter(r['outcome'] for r in records)),
              'stdout_stderr': capture.getvalue(), 'boundary': boundary.assert_boundary()}
    with (output / 'result.json').open('x') as f:
        json.dump(result, f, indent=2)
    print(json.dumps({k: result[k] for k in ('job', 'exit_code', 'counts')}))
    return code
