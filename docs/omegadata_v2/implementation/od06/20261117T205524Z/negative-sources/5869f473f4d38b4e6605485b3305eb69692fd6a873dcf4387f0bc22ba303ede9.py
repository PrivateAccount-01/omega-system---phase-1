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
    args = {'exchange':'CANARY-X', 'symbol':'TOKEN', 'series':'SERIES', 'valid_at':D,
            'known_at':K, 'evidence_policy':'CANARY_ONLY'}
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
    from omegadata.identity_adapters import FinancialField, engineering_gate, intake
    if group == 'G01':
        from omegadata.parsers.schema_catalog import supported_formats
        assert supported_formats()
    elif group == 'G02':
        from omegadata.parsers.contracts import (
            Limits,
            ParsedBar,
            ParseRequest,
            ParserError,
            ParseResult,
        )
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
@pytest.mark.parametrize('case', ['empty', 'order', 'duplicate', 'unknown-link', 'invalid-isin',
    'bad-policy', 'bad-knowledge', 'event-contradiction', 'bad-event-status', 'inclusive-boundary',
    'strict-missing', 'universe-conflict', 'legacy-universe', 'legacy-symbols', 'intake-fields',
    'calendar-unknown-knowledge', 'calendar-exchange', 'calendar-arithmetic', 'calendar-budget',
    'calendar-invalid-date', 'structural-oracle'])
def test_adversarial_invariants(case):
    m, e, repo, c = system()
    if case == 'empty':
        assert resolve(m.MemoryIdentityRepository()).state == 'UNKNOWN'
    elif case == 'order':
        extra = replace(c, claim_id='other', symbol='ELSE')
        assert resolve(replace(repo, claims=(c, extra))) == resolve(replace(repo, claims=(extra, c)))
    elif case == 'duplicate':
        with pytest.raises(ValueError):
            replace(repo, issuers=(*repo.issuers, repo.issuers[0]))
    elif case == 'unknown-link':
        listing = replace(repo.listings[0], security_id=None)
        assert resolve(replace(repo, listings=(listing,))).state == 'QUARANTINED'
    elif case == 'invalid-isin':
        with pytest.raises(ValueError):
            replace(c, isin='NON_MARKET_CANARY')
    elif case == 'bad-policy':
        with pytest.raises(ValueError):
            resolve(repo, evidence_policy='ANYTHING')
    elif case == 'bad-knowledge':
        with pytest.raises(ValueError):
            resolve(repo, known_at=None)
    elif case == 'event-contradiction':
        first = m.LifecycleEvent('e1', 'SUSPENSION', ('listing-a',), e, effective_at=K)
        second = replace(first, event_id='e2', event_type='RELISTING')
        with pytest.raises(ValueError, match='CONTRADICTORY'):
            m.validate_events((first, second))
    elif case == 'bad-event-status':
        with pytest.raises(ValueError):
            m.LifecycleEvent('e1', 'LISTING', ('listing-a',), e, validation_status='IMPLICIT_PASS')
    elif case == 'inclusive-boundary':
        assert m.legacy_exclusive_end(D) == D+timedelta(days=1)
        assert m.legacy_exclusive_end(None) is None
        with pytest.raises(OverflowError):
            m.legacy_exclusive_end(date.max)
    elif case in {'strict-missing', 'universe-conflict'}:
        from omegadata.identity_adapters import MembershipClaim, strict_universe
        item = MembershipClaim('m1', 'INDEX_CANARY', 'MISSING', 'SERIES', 'CANARY-X',
                               D, None, K, None, e, status='OFFICIAL_VERIFIED')
        result = strict_universe((item,), repo, 'INDEX_CANARY', D, K, 'CANARY_ONLY')
        assert len(result.unresolved_memberships) == 1
        if case == 'universe-conflict':
            r = replace(repo, claims=(c, replace(c, claim_id='ambiguous')))
            result = strict_universe((replace(item, symbol='TOKEN'),), r,
                                     'INDEX_CANARY', D, K, 'CANARY_ONLY')
            assert len(result.ambiguous_identifiers) == 1
        assert result.accounted_count == 1 and not result.financial_eligible
    elif case == 'legacy-universe':
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from omegadata.db.base import Base
        from omegadata.db.models import UniverseMembership
        from omegadata.identity_adapters import legacy_universe_inventory
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            session.add(UniverseMembership(isin='CANARY-NONE', index_name='INDEX_CANARY',
                added_date=D, effective_date=D, source='RECONSTRUCTED', source_confidence=1))
            session.flush()
            rows = legacy_universe_inventory(session, 'INDEX_CANARY', D)
            assert len(rows) == 1 and not rows[0].master_present
            assert rows[0].known_from is None and rows[0].status == 'RECONSTRUCTED_PROVISIONAL'
        engine.dispose()
    elif case == 'legacy-symbols':
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from omegadata.db.base import Base
        from omegadata.db.models import SymbolMap
        from omegadata.domain import Exchange
        from omegadata.identity_adapters import legacy_symbol_inventory
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            session.add(SymbolMap(isin='CANARY-NONE', exchange=Exchange.NSE, symbol='CANARY',
                                  valid_from=D, valid_to=D))
            session.flush()
            rows = legacy_symbol_inventory(session, Exchange.NSE, 'CANARY', D)
            assert len(rows) == 1 and rows[0].valid_to_exclusive == D+timedelta(days=1)
            assert rows[0].known_from is None and not rows[0].authoritative
        engine.dispose()
    elif case == 'intake-fields':
        from omegadata.identity_adapters import intake
        from omegadata.parsers.contracts import ParseResult
        raw = ParseResult('PARSED_UNVERIFIED', 'a'*64)
        result = intake(raw, None)
        fields = dict(result.fields)
        assert result.parser_result is raw
        assert fields['source_artifact_identity'].state == 'PRESENT'
        assert fields['source_authentication_status'].state == 'UNVERIFIED'
        assert fields['symbol_as_reported'].state == 'ABSENT'
        assert not result.financial_eligible
        with pytest.raises(ValueError):
            intake(replace(raw, state='QUARANTINED'), None)
    elif case.startswith('calendar-'):
        cm, sc, cal = calendar_system()
        if case == 'calendar-unknown-knowledge':
            assert cm.VerifiedCalendar((replace(sc, known_from=None),)).query(
                'CANARY-X', D, K, 'CANARY_ONLY').status == 'PROVISIONAL'
            assert cal.query('CANARY-X', D, K-timedelta(seconds=1)).status == 'COVERAGE_UNKNOWN'
        elif case == 'calendar-exchange':
            assert cal.query('CANARY-Y', D, K).status == 'COVERAGE_UNKNOWN'
        elif case == 'calendar-arithmetic':
            # Nonmarket interval arithmetic includes a calendar-year transition.
            start = date(2000, 12, 31)
            claims = tuple(replace(sc, claim_id=f's{i}', session_date=start+timedelta(days=i),
                session_type='CLOSED' if i in (1, 2) else 'SPECIAL') for i in range(4))
            assert cm.VerifiedCalendar(claims).add_business_days(
                'CANARY-X', start, 1, K, 'CANARY_ONLY') == date(2001, 1, 3)
        elif case == 'calendar-budget':
            with pytest.raises(ValueError):
                cal.add_business_days('CANARY-X', D, 1, K, 'CANARY_ONLY', max_calendar_days=4000)
        elif case == 'calendar-invalid-date':
            with pytest.raises(ValueError):
                cal.query('CANARY-X', K, K, 'CANARY_ONLY')
    elif case == 'structural-oracle':
        # Independent explicit interval predicate, no resolver-generated expectation.
        claims = tuple(replace(c, claim_id=f'canary-{i}', symbol=f'TOKEN-{i}',
            valid_from=D+timedelta(days=i), valid_to=D+timedelta(days=i+2),
            known_from=K+timedelta(days=i)) for i in range(32))
        r = replace(repo, claims=claims)
        for i in range(32):
            for offset in (-1, 0, 1, 2):
                actual = resolve(r, symbol=f'TOKEN-{i}', valid_at=D+timedelta(days=i+offset),
                                 known_at=K+timedelta(days=i))
                assert (actual.state == 'RESOLVED') == (offset in (0, 1))
@pytest.mark.parametrize('case', ['immutable-ledger', 'immutable-calendar', 'conflicting-evidence',
    'bad-evidence-time', 'closed-hours', 'missing-calendar', 'calendar-chain',
    'identity-chain', 'wrong-exchange-correction', 'financial-gate'])
def test_review_refusals(case):
    m, e, repo, c = system()
    if case == 'immutable-ledger':
        with pytest.raises(ValueError):
            m.MemoryIdentityRepository(list(repo.issuers), repo.securities, repo.listings, repo.claims)
    elif case == 'immutable-calendar':
        cm, sc, _ = calendar_system()
        with pytest.raises(ValueError):
            cm.VerifiedCalendar([sc])
    elif case == 'conflicting-evidence':
        contradictory = replace(c, evidence=replace(e, authentication='CONFLICTING'))
        assert resolve(replace(repo, claims=(contradictory,))).state == 'QUARANTINED'
    elif case == 'bad-evidence-time':
        with pytest.raises(ValueError):
            replace(c, known_from='2001-01-01')
    elif case == 'closed-hours':
        _, sc, _ = calendar_system()
        with pytest.raises(ValueError):
            replace(sc, session_type='CLOSED', opens_at=K)
    elif case == 'missing-calendar':
        from omegadata.track_a.trading_calendar import TradingCalendar
        from omegadata.session_calendar import legacy_session
        for state in ('missing', 'invalid'):
            assert legacy_session(TradingCalendar({}, {}, config_state=state), 'CANARY-X', D).status == 'COVERAGE_UNKNOWN'
    elif case == 'calendar-chain':
        cm, sc, cal = calendar_system()
        corrected = replace(sc, claim_id='c2', known_from=K+timedelta(days=1), supersedes_claim_id=sc.claim_id)
        revised = cal.append_correction(corrected)
        with pytest.raises(ValueError):
            revised.append_correction(replace(corrected, claim_id='c3'))
        assert cal.claims == (sc,)
        assert cm.VerifiedCalendar((replace(sc, known_to=K+timedelta(days=1)),)).query(
            'CANARY-X', D, K+timedelta(days=1), 'CANARY_ONLY').status == 'COVERAGE_UNKNOWN'
    elif case == 'identity-chain':
        with pytest.raises(ValueError):
            repo.append_correction(replace(c, claim_id='c2', supersedes_claim_id=c.claim_id))
    elif case == 'wrong-exchange-correction':
        with pytest.raises(ValueError):
            repo.append_correction(replace(c, claim_id='c2', exchange='OTHER',
                known_from=K+timedelta(days=1), supersedes_claim_id=c.claim_id))
    elif case == 'financial-gate':
        from omegadata.identity_adapters import engineering_gate
        commands = {n:0 for n in ('focused', 'adoption', 'A', 'ruff', 'mypy', 'pip', 'compile', 'containment')}
        assert engineering_gate(commands) == 'PASS'
        assert engineering_gate({**commands, 'A':None}) == 'BLOCKED'
        assert resolve(repo).financial_eligible is False