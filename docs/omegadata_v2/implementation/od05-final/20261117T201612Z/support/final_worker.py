"""Final phase worker extension: no original repository access or Git use."""
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
    job = config['job']
    if job not in {'finalfocus', 'parser', 'report', 'type'}:
        import od05x_base_worker_jobs
        return od05x_base_worker_jobs.run(config)
    import od05x_isolated_runner as boundary
    boundary.assert_boundary()
    os.chdir('/work/repo')
    output = Path('/work/job')
    output.mkdir()
    if job == 'type':
        from mypy import api
        os.environ['MYPY_CACHE_DIR']='/work/job/mypy'
        stdout,stderr,code=api.run(['--follow-imports=silent','scripts/od05_final_report.py'])
        (output/'result.json').write_text(json.dumps({'job':job,'exit_code':code,'counts':{},'python':sys.version,'stdout_stderr':stdout+stderr}))
        return code
    if job == 'report':
        import od05_final_report
        spec = Path('/work/repo/final_inputs/manifest.json')
        import hashlib
        result = od05_final_report.render(spec.parent, hashlib.sha256(spec.read_bytes()).hexdigest(),
                                         Path('/work/final-report'), capability=boundary.assert_boundary())
        (output / 'result.json').write_text(json.dumps({'job':job,'exit_code':0,'counts':{},
             'python':sys.version,'stdout_stderr':json.dumps(result),'boundary':boundary.assert_boundary()}))
        return 0
    import coverage
    import pytest
    os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    records = []
    class Evidence:
        def pytest_runtest_logreport(self, report):
            if report.when == 'call' or report.failed or report.skipped:
                records.append({'nodeid':report.nodeid,'outcome':report.outcome,
                                'reason':str(report.longrepr) if report.failed or report.skipped else None})
    capture=io.StringIO()
    cov=coverage.Coverage(source=['omegadata.parsers','od05_final_report'],branch=True,
                          data_file=str(output/'focused.coverage'))
    start,tick=datetime.now(UTC).isoformat(),time.monotonic()
    cov.start()
    args=['-q','-p','no:cacheprovider','--basetemp','/work/job/tmp']
    if job=='parser':
        args += ['tests/unit/test_od05_era_parsing.py','tests/unit/test_od05r_reference_evidence.py','tests/unit/test_od05_final_contracts.py']
    else:
        args += ['--confcutdir','/work/repo/tests/unit','tests/unit/test_od05_final_contracts.py']
    with contextlib.redirect_stdout(capture),contextlib.redirect_stderr(capture):
        code=int(pytest.main(args,plugins=[Evidence()]))
    cov.stop();cov.save();cov.json_report(outfile=str(output/'coverage.json'))
    result={'job':job,'exit_code':code,'counts':dict(Counter(r['outcome'] for r in records)),
            'reports':records,'start_utc':start,'end_utc':datetime.now(UTC).isoformat(),
            'elapsed_seconds':time.monotonic()-tick,'python':sys.version,'interpreter':sys.executable,
            'stdout_stderr':capture.getvalue(),'boundary':boundary.assert_boundary()}
    (output/'result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:result[k] for k in ('job','exit_code','counts')}))
    return code
