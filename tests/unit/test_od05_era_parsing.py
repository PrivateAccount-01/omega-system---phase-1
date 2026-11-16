"""OD05 T01–T32 SYNTHETIC_TEST_ONLY. REF cases separately blocked in matrix."""

from __future__ import annotations

import hashlib
import io
import stat
import time
import zipfile
from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal, localcontext

import pytest
from od05_oracle import LEGACY, MODERN, check, expected_digest, require_corpus


@pytest.fixture()
def api():
    # Lazy import lets baseline execute every case and record feature absence.
    from omegadata.parsers.contracts import Limits, ParseRequest
    from omegadata.parsers.dispatch import parse, parse_archive

    return ParseRequest, Limits, parse, parse_archive


def request(api, raw=LEGACY, **changes):
    fields = {
        "source_key": "NSE_EQUITY_BHAVCOPY",
        "requested_business_date": date(2019, 12, 31),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "source_mode": "SYNTHETIC_TEST_ONLY",
        "format_id": "legacy-illustrative",
        "parser_version": "syn-v1",
        "reference_id": "synthetic-v1",
    }
    return api[0](**(fields | changes))


def parse(api, raw=LEGACY, **changes):
    return api[2](raw, request(api, raw, **changes))


def refused(result, reason=None):
    assert result.state == "QUARANTINED" and result.rows == ()
    assert result.reasons and (reason is None or reason in result.reasons)


def archive(raw, name="synthetic.csv", **changes):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        item = zipfile.ZipInfo(name)
        item.create_system = 3
        item.external_attr = changes.get("attrs", stat.S_IFREG << 16)
        item.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(item, raw)
        if changes.get("duplicate"):
            z.writestr(item, raw)
    return out.getvalue()


def test_t01_identity(api):
    result = parse(api)
    assert (
        result.state == "PARSED_UNVERIFIED"
        and result.raw_sha256 == hashlib.sha256(LEGACY).hexdigest()
    )
    with pytest.raises(FrozenInstanceError):
        result.rows[0].symbol = "changed"


def test_t02_determinism(api):
    assert parse(api) == parse(api)


def test_t03_revisions(api):
    one, two = parse(api), parse(api, LEGACY.replace(b"inert", b"new"))
    assert one.raw_sha256 != two.raw_sha256 and one.semantic_sha256 != two.semantic_sha256


def test_t04_legacy(api):
    check(parse(api).rows[0])


@pytest.mark.parametrize(
    "day", [date(2020, 1, 1), date(2024, 6, 24), date(2024, 7, 5), date(2024, 7, 8)]
)
def test_t05_disputed_dates_explicit_only(api, day):
    refused(parse(api, requested_business_date=day), "DATE_MISMATCH")


def test_t06_ambiguity(api):
    for kind in ("unknown", "ambiguous", "official-2024-cutover"):
        refused(parse(api, format_id=kind), "ERA_UNKNOWN")


def test_t07_modern_zip(api):
    result = parse(
        api,
        archive(MODERN),
        format_id="udiff-illustrative",
        requested_business_date=date(2026, 4, 10),
    )
    check(result.rows[0])


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"parser_version": "latest"}, "VERSION_UNSUPPORTED"),
        ({"reference_id": "official"}, "REFERENCE_PENDING"),
        ({"format_id": "BSE"}, "FORMAT_UNSUPPORTED"),
    ],
)
def test_t08_dispatch(api, changes, reason):
    refused(parse(api, **changes), reason)


def test_t09_bse(api):
    refused(parse(api, source_key="BSE_EQUITY_BHAVCOPY"), "SOURCE_SCOPE_DENIED")


def test_t10_official_flag(api):
    refused(parse(api, source_mode="OFFICIAL_REFERENCE_VERIFIED"), "SOURCE_SCOPE_DENIED")


@pytest.mark.parametrize(
    "raw",
    [
        LEGACY.replace(b"SYMBOL,", b"SYMBOL,symbol,"),
        LEGACY.replace(b"OPEN,", b"open,"),
        LEGACY.replace(b"OPEN,", b""),
        LEGACY.replace(b"NOTE", b"ISIN"),
        LEGACY.replace(b"SYMBOL", b" SYMBOL"),
    ],
)
def test_t11_headers(api, raw):
    refused(parse(api, raw))


@pytest.mark.parametrize(
    "raw",
    [
        LEGACY + b"broken,row\n",
        LEGACY.replace(b"inert", b'"unterminated'),
        LEGACY.replace(b"inert", b"inert,extra"),
        LEGACY.replace(b"inert", b"\xff"),
        LEGACY.replace(b"inert", b'x"y'),
        LEGACY.replace(b"inert", b'"x"trailing'),
    ],
)
def test_t12_csv(api, raw):
    refused(parse(api, raw), "CSV_INVALID")


@pytest.mark.parametrize(
    "name,kwargs",
    [
        ("../x.csv", {}),
        ("/x.csv", {}),
        ("C:/x.csv", {}),
        ("x\\y.csv", {}),
        ("dir/x.csv", {}),
        ("x.zip", {}),
        ("wrong.csv", {}),
        ("synthetic.csv", {"duplicate": True}),
        ("synthetic.csv", {"attrs": stat.S_IFLNK << 16}),
    ],
)
def test_t13_zip(api, name, kwargs):
    refused(parse(api, archive(LEGACY, name, **kwargs)))


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"<html>denied</html>",
        b'{"denied":true}',
        b"PK\x03\x04truncated",
        LEGACY.split(b"\n")[0] + b"\n",
    ],
)
def test_t14_denial_empty(api, raw):
    refused(parse(api, raw))


def test_t15_dates(api):
    raw = MODERN.replace(b"2026-04-10,2026-04-10", b"2026-04-10,2026-04-11")
    refused(
        parse(api, raw, format_id="udiff-illustrative", requested_business_date=date(2026, 4, 10)),
        "DATE_MISMATCH",
    )


@pytest.mark.parametrize("token", [b"-1", b"+1", b"1.5", b"", b"1,000", b"9" * 25, b"1e2"])
def test_t16_volume(api, token):
    refused(parse(api, LEGACY.replace(b",0,inert", b"," + token + b",inert")))
    assert parse(api).rows[0].volume == 0


def test_t17_exact_decimal_context(api):
    with localcontext() as ctx:
        ctx.prec = 2
        result = parse(api)
    assert result.rows[0].open == Decimal("10.10")
    assert result.semantic_sha256 == expected_digest("2019-12-31", "legacy-illustrative")
    assert result.rows[0].price_lexemes[0] == "10.10"


@pytest.mark.parametrize(
    "token",
    [
        b"NaN",
        b"Infinity",
        b"-1",
        b"1e999999",
        b"1e1",
        b"1_0",
        b"1.123456789",
        b"99999999999999999999999",
        b"+1",
        b" 10",
    ],
)
def test_t18_prices(api, token):
    refused(parse(api, LEGACY.replace(b"10.10", token)), "PRICE_INVALID")
    refused(parse(api, LEGACY.replace(b"12.20", b"1.00")), "PRICE_INVALID")


def test_t19_identity(api):
    row = LEGACY.splitlines(keepends=True)[1]
    refused(parse(api, LEGACY + row), "IDENTITY_AMBIGUOUS")
    assert len(parse(api, LEGACY + row.replace(b",EQ,", b",BE,")).rows) == 2


def test_t20_text(api):
    row = parse(api).rows[0]
    assert row.symbol == "000SYN" and row.isin == "00001234"


def test_t21_optional_identity(api):
    raw = LEGACY.replace(b",00001234,", b",,")
    assert parse(api, raw).rows[0].isin is None
    refused(parse(api, LEGACY.replace(b",EQ,", b",,")), "IDENTITY_AMBIGUOUS")


def test_t22_temporal(api):
    row = parse(api).rows[0]
    assert row.published_at is None and row.trade_date == row.business_date == date(2019, 12, 31)


def test_t23_raw_and_observation(api, tmp_path):
    refused(parse(api, raw_sha256="0" * 64), "RAW_HASH_MISMATCH")
    from omegadata.track_a.raw_archive import RawArchive
    from omegadata.track_a.source_rights import SourcePolicyError

    with pytest.raises(SourcePolicyError):
        api[3](RawArchive(tmp_path / "archive"), request(api, observation_id="a" * 32), "RESEARCH")
    with pytest.raises(ValueError, match="OBSERVATION_REQUIRED"):
        api[3](RawArchive(tmp_path / "archive"), request(api), "RESEARCH")


@pytest.mark.parametrize(
    "mode", ["SOURCE_CACHED_RAW", "SOURCE_SEED_IMPORTED", "PROVIDER_OBSERVED_UNVERIFIED"]
)
def test_t24_origin(api, mode):
    refused(parse(api, source_mode=mode), "SOURCE_SCOPE_DENIED")


def test_t25_rights(api, monkeypatch, tmp_path):
    from omegadata.track_a.raw_archive import RawArchive
    from omegadata.track_a.source_rights import SourcePolicyError

    archive_service = RawArchive(tmp_path / "archive")

    def forbidden(*args, **kwargs):
        raise AssertionError("must not open payload before rights")

    monkeypatch.setattr(archive_service, "_read", forbidden)
    with pytest.raises(SourcePolicyError):
        api[3](archive_service, request(api, observation_id="a" * 32), "RESEARCH")


@pytest.mark.parametrize("state", ["REVOKED", "WRONG_PURPOSE"])
def test_t25_revocation_scope(api, tmp_path, monkeypatch, synthetic_source_policy_provider, state):
    from datetime import UTC, datetime

    from omegadata.track_a.raw_archive import RawArchive
    from omegadata.track_a.source_rights import (
        SourcePolicy,
        SourcePolicyError,
        SourcePolicyRegister,
    )

    policies = []
    for policy in synthetic_source_policy_provider().policies:
        fields = policy.model_dump()
        if state == "REVOKED":
            fields.update(
                status="REVOKED",
                revoked_at=datetime(2026, 11, 16, tzinfo=UTC),
                revocation_reason="SYNTHETIC_TEST_ONLY",
            )
        else:
            fields["permitted_operations"] = ("READ_CACHED",)
        revised = SourcePolicy.model_validate(fields)
        policies.append(revised.model_copy(update={"revision_hash": revised.canonical_hash()}))
    register = SourcePolicyRegister(schema_version="source-policy/v1", policies=tuple(policies))
    service = RawArchive(tmp_path / "archive", policy_provider=lambda: register)
    with pytest.raises(SourcePolicyError):
        api[3](service, request(api, observation_id="a" * 32), "DERIVE")
    assert not service.root.exists()


def test_t23_verified_synthetic_archive(api, tmp_path, synthetic_source_policy_provider):
    from datetime import UTC, datetime

    from omegadata.track_a.raw_archive import ArchiveError, ObservationRequest, RawArchive

    service = RawArchive(tmp_path / "archive", policy_provider=synthetic_source_policy_provider)
    item = service.put(
        LEGACY,
        ObservationRequest(
            source_key="NSE_EQUITY_BHAVCOPY",
            business_date=date(2019, 12, 31),
            observed_at=datetime(2026, 11, 16, tzinfo=UTC),
            source_era="2010_2019",
            source_mode="SYNTHETIC_TEST_ONLY",
            parser_schema="syn-v1",
            payload_state="HTTP_RECEIVED",
            transport="HTTPX",
            original_url="https://example.invalid/file",
            final_url="https://example.invalid/file",
            origin_ref="SYNTHETIC_TEST_ONLY",
        ),
    )
    req = request(api, observation_id=item.observation_id)
    check(api[3](service, req, "RESEARCH").rows[0])
    with pytest.raises(ArchiveError):
        api[3](service, replace(req, requested_business_date=date(2020, 1, 1)), "RESEARCH")


def test_t26_no_io(api, monkeypatch):
    import builtins
    import socket

    def deny(*args, **kwargs):
        raise AssertionError("PURE_PARSER_IO")

    monkeypatch.setattr(builtins, "open", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    for raw in (LEGACY, b"", b"<html>", LEGACY + b"bad\n", archive(LEGACY, "../bad")):
        result = parse(api, raw)
        assert result.state in ("QUARANTINED", "PARSED_UNVERIFIED")


def test_t27_oracle_digest(api):
    assert parse(api).semantic_sha256 == expected_digest("2019-12-31", "legacy-illustrative")
    refused(parse(api, parser_version="syn-v2"), "VERSION_UNSUPPORTED")


def test_t28_no_production_adapter(api):
    from omegadata.track_a.source_registry import resolve_era

    before = resolve_era("NSE_EQUITY_BHAVCOPY", date(2020, 1, 2))
    parse(api)
    assert resolve_era("NSE_EQUITY_BHAVCOPY", date(2020, 1, 2)) == before
    assert api[2].__module__.startswith("omegadata.parsers")


def test_t29_newline_metadata(api):
    assert parse(api, LEGACY.replace(b"\n", b"\r\n")).semantic_sha256 == parse(api).semantic_sha256
    assert parse(api, archive(LEGACY)).semantic_sha256 == parse(api).semantic_sha256
    raw = LEGACY.replace(b"inert", b'"two\nlines"')
    assert parse(api, raw).rows[0].source_row_index == 1
    refused(parse(api, LEGACY.replace(b"\n", b"\r")), "CSV_INVALID")


def test_t30_limits(api):
    for changes in (
        {"body_bytes": 10},
        {"max_rows": 1},
        {"archive_bytes": 10},
        {"compression_ratio": 1},
    ):
        raw = (
            LEGACY + LEGACY.splitlines(keepends=True)[1].replace(b"000SYN", b"000TWO")
            if "max_rows" in changes
            else archive(LEGACY)
        )
        start = time.monotonic()
        result = api[2](raw, request(api, raw), api[1](**changes))
        refused(result, "ZIP_BUDGET" if "max_rows" not in changes else "ROW_INVALID")
        assert time.monotonic() - start < 2
    with pytest.raises(ValueError):
        api[1](body_bytes=-1)


def test_t31_independent_oracle_and_tamper(api, tmp_path):
    row = parse(api).rows[0]
    check(row)
    for changed in (
        replace(row, volume=1),
        replace(row, source_row_index=2),
        replace(row, open=Decimal("10.11")),
    ):
        with pytest.raises(AssertionError):
            check(changed)
    corpus = tmp_path / "oracle.csv"
    with pytest.raises(AssertionError):
        require_corpus(corpus)
    for data in (b"", LEGACY + b"tampered"):
        corpus.write_bytes(data)
        with pytest.raises(AssertionError):
            require_corpus(corpus)
    corpus.write_bytes(LEGACY)
    assert require_corpus(corpus) == hashlib.sha256(LEGACY).hexdigest()


def test_t32_replay_vector(api):
    # Runtime full-suite/lint/type/coverage evidence belongs to the external matrix,
    # this executable vector is compared identically on all three runtimes.
    result = parse(
        api, MODERN, format_id="udiff-illustrative", requested_business_date=date(2026, 4, 10)
    )
    assert result.semantic_sha256 == expected_digest("2026-04-10", "udiff-illustrative")


# Post-initial-implementation review additions; not part of the first frozen tranche.
def test_t23_later_in_memory_cannot_claim_archive_pin(api):
    refused(parse(api, observation_id="a" * 32), "SOURCE_SCOPE_DENIED")


def test_t25_later_archive_purpose_is_mandatory(api, tmp_path, synthetic_source_policy_provider):
    from omegadata.track_a.raw_archive import RawArchive

    service = RawArchive(tmp_path / "archive", policy_provider=synthetic_source_policy_provider)
    with pytest.raises(ValueError, match="CONSUMER_PURPOSE_REQUIRED"):
        api[3](service, request(api, observation_id="a" * 32), None)


def test_t30_later_plain_csv_expansion_budget(api):
    refused(api[2](LEGACY, request(api), api[1](archive_bytes=10)), "ZIP_BUDGET")


@pytest.mark.parametrize("kind", ["crc", "encryption", "codec", "trailer", "nested", "bomb"])
def test_t13_later_zip_variants(api, kind):
    raw = bytearray(archive(LEGACY))
    central = raw.index(b"PK\x01\x02")
    if kind == "crc":
        raw[central + 16 : central + 20] = b"\x00" * 4
    elif kind == "encryption":
        raw[central + 8 : central + 10] = (1).to_bytes(2, "little")
    elif kind == "codec":
        raw[central + 10 : central + 12] = (99).to_bytes(2, "little")
    elif kind == "trailer":
        raw += b"trailer"
    elif kind == "nested":
        raw = bytearray(archive(archive(LEGACY)))
    else:
        raw = bytearray(archive(b"x" * 200000))
    refused(parse(api, bytes(raw)))


def test_t31_later_all_fields_modern_and_date(api):
    result = parse(
        api, MODERN, format_id="udiff-illustrative", requested_business_date=date(2026, 4, 10)
    )
    row = result.rows[0]
    check(row)
    assert row.trade_date == row.business_date == date(2026, 4, 10)
    assert row.exchange == "NSE" and row.source_key == "NSE_EQUITY_BHAVCOPY"
    assert row.scrip_code is None and result.reference_classification == "SYNTHETIC_TEST_ONLY"
    changed = parse(
        api,
        MODERN,
        format_id="udiff-illustrative",
        requested_business_date=date(2026, 4, 10),
        reference_id="forged",
    )
    refused(changed, "REFERENCE_PENDING")


@pytest.mark.parametrize("count", [0, 2, True, -1])
def test_t01_later_expected_count(api, count):
    refused(parse(api, expected_record_count=count), "INTEGRITY")


def test_t16_later_volume_lexeme(api):
    result = parse(api, LEGACY.replace(b",0,inert", b",000,inert"))
    assert result.rows[0].volume == 0
    assert result.rows[0].volume_lexeme == "000"


def test_t05_later_explicit_synthetic_2020_profile(api):
    raw = LEGACY.replace(b"2019-12-31", b"2020-01-02")
    result = parse(api, raw, requested_business_date=date(2020, 1, 2))
    assert result.state == "PARSED_UNVERIFIED"
    assert result.format_id == "legacy-illustrative"
    assert result.reference_classification == "SYNTHETIC_TEST_ONLY"
