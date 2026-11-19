from pathlib import Path
B=Path('/home/parilrupani/omega-od07-20261119T171019Z');P=B/'staged2/repo/src/omegadata/adjustments'
p=P/'contracts.py';v=p.read_text().replace('abs(value.as_tuple().exponent)>64','abs(int(value.as_tuple().exponent))>64')
v=v.replace('    @property\n    def canonical_json', '''    def __post_init__(self) -> None:
        allowed={"CALCULATED","NOT_APPLICABLE","BLOCKED_EVIDENCE","BLOCKED_KNOWLEDGE","BLOCKED_IDENTITY","BLOCKED_CALENDAR","INVALID_PARAMETERS","CONFLICTING_ACTIONS","UNSUPPORTED_POLICY"}
        if self.status not in allowed or type(self.adjustment_factor_chain) is not tuple:raise ValueError("RESULT_CONTRACT")
        if self.status=="CALCULATED":
            if not self.inputs or not self.original_raw_reference:raise ValueError("INCOMPLETE_RESULT")
            for v in (self.cumulative_factor,self.cumulative_volume_factor,self.adjusted_price):number(v)
            number(self.adjusted_volume,zero=True)
        elif self.adjustment_factor_chain or any(v is not None for v in (self.adjusted_price,self.adjusted_volume,self.cumulative_factor,self.cumulative_volume_factor)):raise ValueError("PARTIAL_ACCEPTED_OUTPUT_REFUSED")
    @property
    def canonical_json''');p.write_text(v)
p=P/'factors.py';v=p.read_text().replace('d=number(p.multiplier);vn=d','d=number(p.multiplier);vn=d\n                if kind=="SPLIT_REVERSE" and d>=1:raise ValueError("REVERSE_SPLIT_MULTIPLIER")');p.write_text(v)
p=P/'temporal.py';v=p.read_text().replace('from omegadata.identity import Evidence','from omegadata.identity import Evidence, Policy as EvidencePolicy, text')
v=v.replace('mode="CANARY_ONLY"','mode: EvidencePolicy="CANARY_ONLY"')
v=v.replace('    for ref in references(a):\n        if ref.currency', '''    for ref in references(a):
        try:text(ref.artifact_id)
        except ValueError:return "INVALID_PARAMETERS","REFERENCE_IDENTITY_REQUIRED",""
        if ref.currency''')
v=v.replace('        ref=a.parameters.reference\n        if ref is None or prior.claims[0].session_date!=ref.session_date','        prior_ref=a.parameters.reference\n        if prior_ref is None or prior.claims[0].session_date!=prior_ref.session_date');p.write_text(v)
p=P/'chains.py';v=p.read_text().replace('from decimal import Decimal,','from decimal import DecimalException, Decimal,')
v=v.replace('    try:inputs=canonical(', '''    try:selected=select_revisions(actions,x.known_at)
    except ValueError as error:return Result("CONFLICTING_ACTIONS",str(error),raw.artifact_id,consumer_profile=policy.profile)
    try:inputs=canonical(''').replace('tuple(sorted(actions,key=lambda a:a.action_id))','selected')
a=v.index('    with localcontext() as math:');z=v.index('    return Result("CALCULATED"',a)
v=v[:a]+'    try:\n'+''.join('    '+line if line.strip() else line for line in v[a:z].splitlines(keepends=True))+'    except DecimalException:return blocked("INVALID_PARAMETERS","OUTPUT_PRECISION_OR_RESOURCE_LIMIT")\n'+v[z:];p.write_text(v)
p=P/'repository.py';v=p.read_text().replace('path=Path(parsed.database)','assert parsed.database is not None\n            path=Path(parsed.database)')
v=v.replace("        raw=result.canonical_json\n",'''        validate_result(result)
        raw=result.canonical_json
''')
v += '''

def validate_result(result: c.Result) -> None:
    """Reconcile stored arithmetic/lineage; this is not a financial certification."""
    from decimal import ROUND_HALF_UP, localcontext
    from omegadata.adjustments.factors import factor
    body=json.loads(result.inputs) if result.inputs else {}
    if result.status!="CALCULATED" or not body:raise ValueError("RESULT_NOT_CALCULATED")
    raw=body["raw"];policy=c.Policy(body["policy"]["profile"],body["policy"]["direction"],body["policy"]["version"])
    with localcontext() as math:
        math.prec=20480
        n=d=vn=vd=Decimal(1)
        for link in result.adjustment_factor_chain:
            action=json.loads(link.input_parameters)
            if link.consumer_profile!=policy.profile or link.raw_observation_reference!=raw["artifact_id"] or link.calculation_version!=c.VERSION:raise ValueError("RESULT_LINEAGE_MISMATCH")
            # Exact typed action is bound to persistent action rows separately.
            f=link.factor
            if f.status not in {"CALCULATED","NOT_APPLICABLE"} or any(v is None for v in (f.numerator,f.denominator,f.volume_numerator,f.volume_denominator)):raise ValueError("INVALID_FACTOR")
            assert f.numerator is not None and f.denominator is not None and f.volume_numerator is not None and f.volume_denominator is not None
            n*=f.numerator;d*=f.denominator;vn*=f.volume_numerator;vd*=f.volume_denominator
        math.prec=c.PRECISION
        price=Decimal(raw["price"]);volume=Decimal(raw["volume"])
        expected_price=price if policy.profile in {"RAW","EXECUTION","VOLUME"} else (price*n/d).quantize(policy.price_quantum,rounding=ROUND_HALF_UP)
        expected_volume=volume if policy.profile in {"RAW","EXECUTION"} else (volume*vn/vd).quantize(policy.volume_quantum,rounding=ROUND_HALF_UP)
        if (result.adjusted_price,result.adjusted_volume,result.cumulative_factor,result.cumulative_volume_factor)!=(expected_price,expected_volume,n/d,vn/vd):raise ValueError("RESULT_MATH_MISMATCH")
'''
v=v.replace('or c.canonical(stored[link.action_revision_id])!=link.input_parameters:', 'or c.canonical(stored[link.action_revision_id])!=link.input_parameters:')
v=v.replace("raise ValueError('RESULT_ACTION_PAYLOAD_MISMATCH')\n            old=",'''raise ValueError('RESULT_ACTION_PAYLOAD_MISMATCH')
                from omegadata.adjustments.factors import factor
                action=stored[link.action_revision_id]
                policy_body=json.loads(result.inputs)["policy"]
                expected=factor(action.action_type,action.parameters,c.Policy(policy_body["profile"],policy_body["direction"],policy_body["version"]))
                if link.factor!=expected:raise ValueError('RESULT_ACTION_FACTOR_MISMATCH')
            old=''')
v=v.replace('    from omegadata.adjustments.factors import factor\n    body=', '    body=').replace('            action=json.loads(link.input_parameters)\n','')
p.write_text(v)
