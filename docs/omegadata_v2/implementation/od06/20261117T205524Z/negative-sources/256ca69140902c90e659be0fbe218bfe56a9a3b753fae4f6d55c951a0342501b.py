"""OD06 invariant tests: all identifiers/dates are NON_MARKET_CANARY bookkeeping.
No real issuer, security, session, mapping or financial correctness is asserted.
"""
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

D = date(2001, 1, 1)
K = datetime(2001, 1, 1, tzinfo=UTC)


def system():
    from omegadata import identity as m
    e = m.Evidence('canary-e', 'NON_MARKET_CANARY', 'UNVERIFIED', 'PERMITTED', 'canary-review')
    issuer = m.Issuer('issuer-a')
    security = m.Security('security-a', issuer.issuer_id)
    listing = m.Listing('listing-a', security.security_id, 'CANARY-X')
    c = m.IdentifierClaim('claim-a', listing.listing_id, 'CANARY-X', 'TOKEN', 'SERIES',
                          D, None, K, None, e)
    repo = m.MemoryIdentityRepository((issuer,), (security,), (listing,), (c,))
    return m, e, repo, c


def resolve(repo, **kw):
    args = dict(exchange='CANARY-X', symbol='TOKEN', series='SERIES', valid_at=D,
                known_at=K, evidence_policy='CANARY_ONLY')
    args.update(kw)
    return repo.resolve_listing(**args)


@pytest.mark.parametrize('group', [f'I{i:02}' for i in range(1, 21)])
def test_identity_groups(group):
    m, e, repo, c = system()
    if group == 'I01':
        assert repo.listings[0].security_id == repo.securities[0].security_id
        assert len({repo.issuers[0].issuer_id, repo.securities[0].security_id,
                    repo.listings[0].listing_id}) == 3
        with pytest.raises(ValueError):
            m.MemoryIdentityRepository(repo.issuers, (), repo.listings, (c,))
    elif group == 'I02':
        assert m.record_id('issuer', 'ledger-key') == m.record_id('issuer', 'ledger-key')
        assert m.record_id('issuer', 'ledger-key') != m.record_id('security', 'ledger-key')
    elif group == 'I03':
        old = replace(c, valid_to=D+timedelta(days=2))
        other = replace(repo.listings[0], listing_id='listing-b')
        new = replace(c, claim_id='claim-b', listing_id='listing-b', valid_from=old.valid_to)
        r = m.MemoryIdentityRepository(repo.issuers, repo.securities, (*repo.listings, other), (new, old))
        assert resolve(r).listing_id == 'listing-a'
        assert resolve(r, valid_at=new.valid_from).listing_id == 'listing-b'
    elif group == 'I04':
        assert resolve(repo, exchange='CANARY-Y').state == 'UNKNOWN'
    elif group == 'I05':
        assert resolve(repo, series='OTHER').state == 'UNKNOWN'
    elif group == 'I06':
        r = replace(repo, claims=(replace(c, valid_to=D+timedelta(days=1)),))
        assert resolve(r, valid_at=D+timedelta(days=1)).state == 'UNKNOWN'
        assert resolve(r, valid_at=D-timedelta(days=1)).state == 'UNKNOWN'
        with pytest.raises(ValueError):
            replace(c, valid_to=D)
    elif group == 'I07':
        r = replace(repo, claims=(replace(c, known_to=K+timedelta(days=1)),))
        assert resolve(r, known_at=K+timedelta(days=1)).state == 'UNKNOWN'
        with pytest.raises(ValueError):
            resolve(repo, known_at=K.replace(tzinfo=None))
    elif group == 'I08':
        assert resolve(repo, known_at=K-timedelta(seconds=1)).state == 'UNKNOWN'
        assert resolve(replace(repo, claims=(replace(c, known_from=None),))).state == 'QUARANTINED'
    elif group == 'I09':
        corrected = replace(c, claim_id='correction', symbol='CORRECTED',
                            known_from=K+timedelta(days=1), supersedes_claim_id=c.claim_id)
        r = repo.append_correction(corrected)
        assert resolve(r).state == 'RESOLVED'
        assert resolve(r, known_at=corrected.known_from).state == 'UNKNOWN'
        assert resolve(r, symbol='CORRECTED', known_at=corrected.known_from).state == 'RESOLVED'
        assert repo.claims == (c,)
    elif group == 'I10':
        other = replace(repo.listings[0], listing_id='listing-b')
        r = m.MemoryIdentityRepository(repo.issuers, repo.securities, (*repo.listings, other),
                                      (c, replace(c, claim_id='claim-b', listing_id='listing-b')))
        assert resolve(r).state == 'CONFLICTING'
        assert resolve(r).listing_id is None
    elif group == 'I11':
        r = replace(repo, claims=(c, replace(c, claim_id='duplicate-evidence')))
        assert resolve(r).state == 'AMBIGUOUS'
        with pytest.raises(ValueError):
            replace(repo, claims=(c, c))
    elif group == 'I12':
        assert resolve(repo).state == 'RESOLVED'
        assert c.isin is None
    elif group == 'I13':
        from omegadata.track_b.isin_master import ISINMasterService
        assert not ISINMasterService.validate_isin('NON_MARKET_CANARY')
        assert resolve(repo, evidence_policy='STRICT').state == 'QUARANTINED'
        blocked = replace(c, evidence=replace(e, permission='PENDING'))
        assert resolve(replace(repo, claims=(blocked,))).state == 'SOURCE_BLOCKED'
    elif group == 'I14':
        assert resolve(replace(repo, claims=(replace(c, lifecycle='DELISTED'),))).state == 'RESOLVED'
        assert resolve(repo).financial_eligible is False
    elif group == 'I15':
        ev = m.LifecycleEvent('event-a', 'SUSPENSION', ('listing-a',), e, effective_at=None)
        assert ev.event_type != 'DELISTING'
        assert m.validate_events((ev,)) == (ev,)
        r = replace(repo, claims=(replace(c, lifecycle='SUSPENDED'),))
        assert resolve(r).lifecycle == 'SUSPENDED'
    elif group == 'I16':
        for kind in ('MERGER_IDENTITY_TRANSITION', 'DEMERGER_IDENTITY_TRANSITION'):
            ev = m.LifecycleEvent('event-a', kind, ('security-a',), e)
            with pytest.raises(ValueError, match='CONTINUITY'):
                m.validate_events((ev,))
    elif group == 'I17':
        with pytest.raises(ValueError):
            repo.append_correction(replace(c, claim_id='bad', supersedes_claim_id='missing'))
        correction = replace(c, claim_id='c2', known_from=K+timedelta(days=1), supersedes_claim_id='claim-a')
        revised = repo.append_correction(correction)
        with pytest.raises(ValueError):
            revised.append_correction(replace(correction, claim_id='c3'))
    elif group == 'I18':
        from omegadata.identity_adapters import MembershipClaim, strict_universe
        membership = MembershipClaim('membership-a', 'INDEX_CANARY', 'MISSING', 'SERIES',
                                     'CANARY-X', D, None, K, None, e)
        result = strict_universe((membership,), repo, 'INDEX_CANARY', D, K, 'CANARY_ONLY')
        assert len(result.unresolved_memberships) == 1
        assert result.selected_count == result.accounted_count == 1
    elif group == 'I19':
        from omegadata.identity_adapters import MembershipClaim, strict_universe
        item = MembershipClaim('member-a', 'INDEX_CANARY', 'TOKEN', 'SERIES', 'CANARY-X',
                               D, None, K, None, e, status='RECONSTRUCTED_PROVISIONAL')
        result = strict_universe((item,), repo, 'INDEX_CANARY', D, K, 'CANARY_ONLY')
        assert not result.resolved_entries
        assert result.unresolved_memberships[0].status == 'RECONSTRUCTED_PROVISIONAL'
    elif group == 'I20':
        from omegadata.identity_adapters import source_backfill
        with pytest.raises(PermissionError, match='SOURCE_DEPENDENT_BACKFILL_BLOCKED'):
            source_backfill(Path('/unmounted-original'))


def calendar_system():
    from omegadata import session_calendar as m
    _, evidence, _, _ = system()
    claim = m.SessionClaim('session-a', 'CANARY-X', D, 'REGULAR', 'Asia/Kolkata',
                           'canary-v1', evidence, K, None)
    return m, claim, m.VerifiedCalendar((claim,))


@pytest.mark.parametrize('group', [f'C{i:02}' for i in range(1, 9)])
def test_calendar_groups(group):
    m, c, cal = calendar_system()
    if group == 'C01':
        assert cal.query('CANARY-X', D, K, 'CANARY_ONLY').status == 'AUTHORITATIVE_SESSION'
        assert cal.query('CANARY-X', D, K).status == 'PROVISIONAL'
    elif group == 'C02':
        assert m.VerifiedCalendar((replace(c, session_type='CLOSED'),)).query(
            'CANARY-X', D, K, 'CANARY_ONLY').status == 'KNOWN_CLOSURE'
    elif group == 'C03':
        # Anonymous date on a weekend: positive control for explicit special claim,
        # NOT an asserted exchange session.
        special = replace(c, session_date=date(2001, 1, 6), session_type='SPECIAL')
        result = m.VerifiedCalendar((special,)).query('CANARY-X', special.session_date, K, 'CANARY_ONLY')
        assert result.status == 'VERIFIED_SPECIAL_SESSION'
        assert not result.financial_eligible
    elif group == 'C04':
        assert cal.query('CANARY-X', date(2100, 1, 1), K).status == 'COVERAGE_UNKNOWN'
        assert cal.query('OTHER', D, K).status == 'COVERAGE_UNKNOWN'
        from omegadata.track_a.trading_calendar import TradingCalendar
        legacy = TradingCalendar({}, {'CANARY-X': {2001}})
        assert m.legacy_session(legacy, 'CANARY-X', D).status == 'PROVISIONAL'
    elif group == 'C05':
        cal = m.VerifiedCalendar((c, replace(c, claim_id='other', session_type='CLOSED')))
        assert cal.query('CANARY-X', D, K, 'CANARY_ONLY').status == 'CONFLICTING_CALENDAR'
    elif group == 'C06':
        correction = replace(c, claim_id='correction', session_type='CLOSED',
                             known_from=K+timedelta(days=1), supersedes_claim_id=c.claim_id)
        revised = cal.append_correction(correction)
        assert revised.query('CANARY-X', D, K, 'CANARY_ONLY').status == 'AUTHORITATIVE_SESSION'
        assert revised.query('CANARY-X', D, correction.known_from, 'CANARY_ONLY').status == 'KNOWN_CLOSURE'
    elif group == 'C07':
        with pytest.raises(ValueError, match='COVERAGE'):
            cal.add_business_days('CANARY-X', D, 1, K, 'CANARY_ONLY')
        assert cal.add_business_days('CANARY-X', D, 0, K, 'CANARY_ONLY') == D
        with pytest.raises(ValueError):
            cal.add_business_days('CANARY-X', D, -1, K)
    elif group == 'C08':
        with pytest.raises(ValueError):
            replace(c, timezone='America/New_York')
        with pytest.raises(ValueError):
            replace(c, calendar_version='')
        assert c.opens_at is None and c.closes_at is None


@pytest.mark.parametrize('group', [f'G{i:02}' for i in range(1, 6)])
def test_governance_groups(group):
    from omegadata.identity_adapters import FinancialField, intake, engineering_gate
    if group == 'G01':
        from omegadata.parsers.schema_catalog import supported_formats
        assert supported_formats()
    elif group == 'G02':
        from omegadata.parsers.contracts import ParseRequest, ParsedBar, ParseResult, Limits, ParserError
        assert all((ParseRequest, ParsedBar, ParseResult, Limits, ParserError))
    elif group == 'G03':
        from od05x_isolated_runner import assert_boundary, native_probe
        assert assert_boundary()['verified']
        assert native_probe('read')['denied']
        assert not Path('/mnt/e').exists()
    elif group == 'G04':
        from omegadata.parsers.contracts import ParseResult
        result = intake(ParseResult('PARSED_UNVERIFIED', 'a'*64), None)
        assert result.known_from.state == 'ABSENT'
        assert result.financial_eligible is False
        with pytest.raises(ValueError):
            FinancialField('PRESENT', None)
    elif group == 'G05':
        assert engineering_gate({'focused': 1, 'mypy': 0}) == 'FAIL'
        assert engineering_gate({}) == 'BLOCKED'