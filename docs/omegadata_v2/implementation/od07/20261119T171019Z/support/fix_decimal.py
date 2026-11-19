from pathlib import Path
B=Path('/home/parilrupani/omega-od07-20261119T171019Z');P=B/'staged2/repo/src/omegadata/adjustments'
p=P/'contracts.py';v=p.read_text().replace('from decimal import Decimal','from decimal import Context as DecimalContext, Decimal, DivisionByZero, Inexact, InvalidOperation, Overflow, ROUND_HALF_EVEN')
v += '''

def arithmetic_context() -> DecimalContext:
    """Pin all ambient state; reject inexact intermediate multiplication."""
    return DecimalContext(prec=20480,rounding=ROUND_HALF_EVEN,Emin=-999999,Emax=999999,traps=[InvalidOperation,DivisionByZero,Overflow,Inexact])
''';p.write_text(v)
for name,variable in [('factors.py','context'),('chains.py','math'),('repository.py','math')]:
 p=P/name;v=p.read_text()
 if name=='repository.py':
  v=v.replace('with localcontext() as math:', 'with localcontext(c.arithmetic_context()) as math:').replace('        math.prec = c.PRECISION','        math.traps[Inexact] = False\n        math.prec = c.PRECISION')
 else:
  v=v.replace('with localcontext() as '+variable+':', 'with localcontext(arithmetic_context()) as '+variable+':')
  # Add the helper to an existing explicit imports tuple.
  marker='    canonical,' if name=='chains.py' else '    number,'
  assert marker in v
  v=v.replace(marker,marker+'\n    arithmetic_context,')
  indent='            ' if name=='factors.py' else '            '
  v=v.replace(indent+variable+'.prec = PRECISION',indent+variable+'.traps[Inexact] = False\n'+indent+variable+'.prec = PRECISION')
 v=v.replace('from decimal import ', 'from decimal import Inexact, ',1)
 p.write_text(v)
p=B/'run.py';v=p.read_text().replace('len(newnodes)==99','len(newnodes)==100');p.write_text(v)
(B/'reviewed-new-tests.json').rename(B/'reviewed-new-tests-99-historical.json')
(B/'new-test-classification-review.json').rename(B/'new-test-classification-99-historical.json')
