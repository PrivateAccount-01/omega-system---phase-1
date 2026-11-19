from pathlib import Path
B=Path('/home/parilrupani/omega-od07-20261119T171019Z');S=B/'staged2/repo'
p=S/'src/omegadata/adjustments/contracts.py';v=p.read_text().replace('                number(v)\n            number(self.adjusted_volume, zero=True)', '''                if type(v) is not Decimal or not v.is_finite() or v<=0:raise ValueError("RESULT_NUMBER")
            if type(self.adjusted_volume) is not Decimal or not self.adjusted_volume.is_finite() or self.adjusted_volume<0:raise ValueError("RESULT_VOLUME")''');p.write_text(v)
p=S/'tests/unit/test_od07_adjustments.py';v=p.read_text().replace('import pytest','import pytest\nfrom sqlalchemy.exc import IntegrityError')
v=v.replace('with pytest.raises(Exception), repo.transaction() as connection:', 'with pytest.raises(IntegrityError), repo.transaction() as connection:')
v=v.replace('with pytest.raises(Exception):\n            repo.append_result','with pytest.raises(ValueError):\n            repo.append_result')
v=v.replace('        with pytest.raises(RuntimeError):\n            with repo.transaction() as connection:\n', '        with pytest.raises(RuntimeError), repo.transaction() as connection:\n')
# Dedent only the body formerly nested under the transaction context.
a=v.index('        with pytest.raises(RuntimeError), repo.transaction() as connection:');z=v.index('        assert "broken"',a)
prefix=v[a:z].splitlines(keepends=True);v=v[:a]+prefix[0]+''.join(line[4:] if line.startswith('                ') else line for line in prefix[1:])+v[z:];p.write_text(v)
