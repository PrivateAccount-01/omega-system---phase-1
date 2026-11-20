"""OD10 anonymous bookkeeping / literal scalar tests. No financial source observations."""

import hashlib
import threading
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

D = date(2020, 1, 2)
K = datetime(2020, 1, 3, tzinfo=UTC)


def record(**kw):
    from omegadata.canonical_storage.contracts import Observation

    return replace(
        Observation(
            observation_id="control-0001",
            observation_revision_id="revision-1",
            source_id="control-source",
            source_artifact_identity="control-artifact",
            source_record_identity="control-row",
            trade_date=D,
            session_date=D,
            known_from=K,
            field_semantics="CONTROL_SCALAR",
            value=Decimal("1.2500"),
            security_id="control-security",
            listing_id="00001",
            exchange="CANARY-X",
            symbol_as_reported="CONTROL",
            series_as_reported="CONTROL",
            publisher_identity="control-publisher",
            source_row_ordinal=1,
            parser_version="control-parser/v1",
            schema_version="control/v1",
            source_evidence_id="NON_MARKET_CONTROL",
            source_rights_state="NON_MARKET_CONTROL",
            source_authority_digest="a" * 64,
            observation_classification="NON_MARKET_STRUCTURAL_CONTROL",
            quality_state="UNVERIFIED",
            price_basis="RAW_UNADJUSTED",
            volume_basis="RAW",
            currency="CONTROL",
            price_unit="CONTROL",
            volume_unit="CONTROL",
            consumer_profile="AUDIT",
            economic_valid_from=D,
        ),
        **kw,
    )


def database(tmp_path):
    from omegadata.canonical_storage.store import CanonicalStore

    return CanonicalStore(tmp_path / "store", disposable_root=tmp_path)


def commit(db, rows=None, op="operation-1", parent=None, **kw):
    from omegadata.canonical_storage.contracts import DatasetDefinition

    definition = DatasetDefinition(
        "control-dataset",
        "source_observations",
        "RAW",
        "canonical/v1",
        "RAW_UNADJUSTED",
        "AUDIT",
        ("control-source",),
        "COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE",
    )
    definition = replace(definition, **kw.pop("definition", {}))
    return db.commit(
        definition,
        (record(),) if rows is None else rows,
        operation_id=op,
        parent_version=parent,
        expected_partitions=("CANARY-X/2020-01",),
        **kw,
    )


def query(db, version, **kw):
    from omegadata.canonical_storage.contracts import Query

    return db.query(
        replace(
            Query(
                version, "control-dataset", D, D + timedelta(days=1), K, "RAW_UNADJUSTED", "AUDIT"
            ),
            **kw,
        )
    )


GROUPS = [
    f"{p}{i:02}"
    for p, n in [
        ("S", 6),
        ("L", 7),
        ("V", 5),
        ("M", 6),
        ("T", 6),
        ("C", 4),
        ("E", 4),
        ("Q", 7),
        ("R", 3),
        ("G", 4),
    ]
    for i in range(1, n + 1)
]


@pytest.mark.parametrize("group", GROUPS)
def test_od10_acceptance(group, tmp_path):
    from omegadata.canonical_storage import schema
    from omegadata.canonical_storage.contracts import StorageError

    if group.startswith("S"):
        row = record()
        if group == "S01":
            assert schema.from_table(schema.to_table((row,), "canonical/v1")) == (row,)
        elif group == "S02":
            value = Decimal("0." + "1" * 90)
            coded = schema.encode_decimal(value, "CALCULATION")
            assert (
                schema.decode_decimal(coded).as_tuple() == value.as_tuple()
                and coded["fixed"] is None
            )
        elif group == "S03":
            with pytest.raises(StorageError, match="PRECISION"):
                schema.encode_decimal(Decimal("1e-90"), "RAW")
        elif group == "S04":
            rows = (
                replace(row, value=None, value_state="MISSING"),
                replace(row, observation_revision_id="zero", value=Decimal(0)),
            )
            assert [r.value for r in schema.from_table(schema.to_table(rows, "canonical/v1"))] == [
                None,
                Decimal(0),
            ]
        elif group == "S05":
            r = replace(row, known_from=K.astimezone(timezone(timedelta(hours=5, minutes=30))))
            assert schema.from_table(schema.to_table((r,), "canonical/v1"))[0].known_from == K
            with pytest.raises(StorageError):
                replace(row, known_from=K.replace(tzinfo=None))
        elif group == "S06":
            assert (
                schema.from_table(schema.to_table((row,), "canonical/v1"))[0].listing_id == "00001"
            )
        return
    db = database(tmp_path)
    if group.startswith("L"):
        from test_od09_reconciliation import controls

        from omegadata.canonical_storage.admission import (
            ProvenanceLedger,
            SourceBinding,
            admit_comparison,
        )
        from omegadata.reconciliation.engine import reconcile_context

        _, x, left, right = controls()
        ledger = ProvenanceLedger()
        if group == "L01":
            from omegadata.parsers.contracts import ParseResult

            v = ParseResult("PARSED_UNVERIFIED", "a" * 64)
            ref = ledger.pin("source_observations", "parser-control", v, K)
            assert ledger.get(ref) == v and not ledger.financial_eligible(ref)
        elif group == "L02":
            a = ledger.pin("instrument_identity_revisions", "identity", x.universe.identity, K)
            b = ledger.pin("session_calendar", "calendar", x.universe.calendar, K)
            assert ledger.get(a) == x.universe.identity and ledger.get(b) == x.universe.calendar
        elif group == "L03":
            from omegadata.canonical_storage.admission import verify_proof
            from omegadata.reconciliation.dependencies import UpstreamProof

            with pytest.raises(StorageError):
                verify_proof(None, K)
            assert UpstreamProof is not None
        elif group == "L04":
            from omegadata.universe.contracts import EligibilityPolicy
            from omegadata.universe.snapshots import get_universe_as_of

            p = EligibilityPolicy("control-membership", view="MEMBERSHIP")
            s = get_universe_as_of(x.universe, D, K, p, x.universe.source_snapshot_id)
            ref = ledger.pin("universe_snapshots", "snapshot", s, K, context=(x.universe, p))
            assert len(ledger.get(ref).decisions) == len(s.decisions)
        else:
            ledger.pin_observations((left, right))
            binding = SourceBinding.from_observation(left)
            if group == "L05":
                assert (
                    admit_comparison(
                        x,
                        reconcile_context(x),
                        ledger,
                        (left.observation_id, right.observation_id),
                        False,
                    ).financial_eligible
                    is False
                )
            elif group == "L06":
                with pytest.raises(StorageError, match="SCOPE"):
                    admit_comparison(
                        replace(x, right=()),
                        reconcile_context(replace(x, right=())),
                        ledger,
                        (left.observation_id, right.observation_id),
                        True,
                    )
            elif group == "L07":
                with pytest.raises(StorageError, match="SEMANTIC"):
                    ledger.verify_source(replace(left, field_name="open"), binding)
        return
    if group.startswith("V"):
        v1 = commit(db)
        before = db.manifest(v1)
        row2 = record(
            observation_revision_id="revision-2",
            supersedes_revision_id="revision-1",
            value=Decimal("2.5"),
            known_from=K + timedelta(days=1),
        )
        if group == "V03":
            assert commit(db) == v1
            return
        if group == "V04":
            with pytest.raises(StorageError):
                commit(db, (row2,))
            return
        v2 = commit(db, (row2,), "operation-2", v1)
        if group == "V01":
            assert query(db, v1).rows[0]["value"] == Decimal("1.2500") and query(
                db, v2, known_at=K + timedelta(days=1)
            ).rows[0]["value"] == Decimal("2.5")
        elif group == "V02":
            assert db.manifest(v1) == before and db.verify(v1)["verified"]
        elif group == "V05":
            db.select_version("control-dataset", v2, "control-new", K + timedelta(days=1))
            db.select_version("control-dataset", v1, "control-rollback", K + timedelta(days=2))
            assert db.selected_version("control-dataset") == v1 and query(db, v1).rows[0][
                "value"
            ] == Decimal("1.2500")
        return
    if group.startswith("M"):
        v = commit(db)
        m = db.manifest(v)
        file = tmp_path / "store" / m["file_entries"][0]["relative_path"]
        if group == "M01":
            file.rename(file.with_suffix(".missing"))
        elif group == "M02":
            file.write_bytes(b"NON_MARKET_CORRUPT")
        elif group in {"M03", "M04", "M05"}:
            entry = dict(m["file_entries"][0])
            entry[
                {"M03": "row_count", "M04": "schema_fingerprint", "M05": "relative_path"}[group]
            ] = {"M03": 999, "M04": "0" * 64, "M05": "../outside.parquet"}[group]
            with pytest.raises(StorageError):
                db.verify_file(entry)
            return
        elif group == "M06":
            (tmp_path / "store/objects/unreferenced.parquet").write_bytes(b"NOT_A_MEMBER")
            assert len(query(db, v).rows) == 1
            return
        with pytest.raises(StorageError):
            query(db, v)
        return
    if group.startswith("T"):
        v1 = commit(db)
        phases = {
            "T01": "during_file_write",
            "T02": "after_install_before_catalog_commit",
            "T03": "after_catalog_commit_before_acknowledgement",
            "T04": "after_file_write_before_validation",
            "T05": "during_catalog_transaction",
            "T06": "after_validation_before_install",
        }
        phase = phases[group]

        def fault(at):
            if at == phase:
                if group == "T04":
                    assert len(query(db, v1).rows) == 1
                raise RuntimeError("CONTROLLED_FAULT")

        with pytest.raises(RuntimeError):
            commit(db, op="interrupted", parent=v1, hook=fault)
        db.close()
        db = database(tmp_path)
        assert len(query(db, v1).rows) == 1
        if group == "T03":
            assert commit(db, op="interrupted", parent=v1) == db.operation_version("interrupted")
        else:
            assert db.operation_version("interrupted") is None
        assert isinstance(db.orphans(), dict)
        return
    if group.startswith("C"):
        v = commit(db)
        results = []
        barrier = threading.Barrier(2)

        def writer(i):
            local = database(tmp_path)
            try:
                barrier.wait(timeout=10)
                results.append(
                    commit(
                        local,
                        op="shared" if group == "C01" else "race-" + str(i),
                        parent=v,
                        rows=(record(value=Decimal(i + 1)),) if group == "C02" else None,
                    )
                )
            except StorageError:
                results.append("REFUSED")
            finally:
                local.close()

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        if group == "C04":
            assert query(db, v).rows[0]["value"] == Decimal("1.2500")
        for t in threads:
            t.join(15)
            assert not t.is_alive()
        assert len(results) == 2
        if group == "C01":
            assert results[0] == results[1] and results[0] != "REFUSED"
        else:
            assert results.count("REFUSED") == 1
        assert db.verify(v)["verified"]
        return
    if group.startswith("E"):
        v = commit(db)
        if group == "E01":
            assert (
                schema.classify_change("canonical/v1", "canonical/v2")
                == "BACKWARD_COMPATIBLE_ADDITION"
            )
        elif group == "E02":
            with pytest.raises(StorageError):
                schema.get_schema("unknown")
        elif group == "E03":
            with pytest.raises(StorageError):
                schema.encode_decimal(Decimal("1e40"), "RAW")
        elif group == "E04":
            new = db.convert_version(v, "canonical/v2", "convert-control")
            assert (
                db.manifest(new)["parent_dataset_version_id"] == v
                and query(db, new).rows[0]["value"] == Decimal("1.2500")
                and db.verify(v)["verified"]
            )
        return
    if group.startswith("Q"):
        v = commit(db)
        if group == "Q01":
            with pytest.raises(StorageError, match="UNKNOWN_DATASET_VERSION"):
                query(db, "unknown")
        elif group == "Q02":
            q = query(db, v, known_at=K - timedelta(seconds=1))
            assert q.rows == () and q.excluded[0]["reason"] == "FUTURE_INFORMATION"
        elif group == "Q03":
            with pytest.raises(StorageError, match="PRICE_BASIS"):
                query(db, v, price_basis="BACKWARD_ADJUSTED")
        elif group == "Q04":
            assert query(db, v, listing_ids=("other",)).rows == ()
        elif group == "Q05":
            assert query(db, v).files_scanned == 1 and query(db, v).files_verified == 1
        elif group == "Q06":
            with pytest.raises(StorageError):
                query(db, v, maximum_rows=0)
        elif group == "Q07":
            assert [
                (r["observation_revision_id"], r["listing_id"], r["value"])
                for r in query(db, v).rows
            ] == [("revision-1", "00001", Decimal("1.2500"))]
        return
    if group.startswith("R"):
        refs = (("source_observation_revision", "external-control", "a" * 64),)
        v1 = commit(db, rows=(record(lineage=refs),))
        v2 = commit(
            db,
            op="next",
            parent=v1,
            rows=(
                record(
                    observation_revision_id="second",
                    supersedes_revision_id="revision-1",
                    lineage=refs,
                    known_from=K + timedelta(days=1),
                ),
            ),
        )
        out = db.impact("source_observation_revision", "external-control", K + timedelta(days=2))
        assert set(out["dataset_versions"]) == {v1, v2}
        if group == "R02":
            assert out["coverage_state"] != "AUTHENTIC_COMPLETE"
        elif group == "R03":
            assert query(db, v1).rows[0]["observation_revision_id"] == "revision-1"
        return
    if group.startswith("G"):
        row = record()
        if group == "G01":
            with pytest.raises(ValueError, match="init=False"):
                replace(row, financial_eligibility=True)
        elif group == "G02":
            assert query(db, commit(db)).financial_eligible is False
        elif group == "G03":
            with pytest.raises(OSError):
                Path("/unmounted-original/CONTROL_ONLY").read_bytes()
        elif group == "G04":
            assert db.domain_registry()["review_revisions"] == "TRANSACTIONAL_METADATA"


def test_legacy_partition_overwrite_reproduction(tmp_path, monkeypatch):
    import pandas as pd

    from omegadata.config import settings
    from omegadata.track_a.storage import ParquetStorage

    monkeypatch.setattr(settings, "parquet_root", str(tmp_path / "legacy"))
    store = ParquetStorage()
    a = store.store_daily("NON_MARKET_BOOKKEEPING", D, pd.DataFrame({"anonymous_sequence": [1]}))
    before = hashlib.sha256(a.path.read_bytes()).hexdigest()
    b = store.store_daily("NON_MARKET_BOOKKEEPING", D, pd.DataFrame({"anonymous_sequence": [2]}))
    assert a.path == b.path and before != hashlib.sha256(b.path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "phase",
    [
        "before_write",
        "during_file_write",
        "after_file_write_before_validation",
        "after_validation_before_install",
        "after_install_before_catalog_commit",
        "during_catalog_transaction",
        "after_catalog_commit_before_acknowledgement",
    ],
)
def test_fault_retry_is_recoverable_without_orphan_promotion(phase, tmp_path):
    db = database(tmp_path)
    v = commit(db)

    def fault(at):
        if at == phase:
            raise RuntimeError("CONTROLLED_FAULT")

    with pytest.raises(RuntimeError):
        commit(db, op="retry-control", parent=v, hook=fault)
    orphans = db.orphans()
    new = commit(db, op="retry-control", parent=v)
    assert (
        db.operation_version("retry-control") == new
        and db.verify(v)["verified"]
        and db.verify(new)["verified"]
    )
    assert orphans["cleanup_performed"] is False


@pytest.mark.parametrize(
    "case", ["fixed-mismatch", "overflow", "zero-scale", "fraction", "negative", "maximum"]
)
def test_scalar_physical_and_logical_reconciliation(case):
    import pyarrow as pa

    from omegadata.canonical_storage import schema
    from omegadata.canonical_storage.contracts import StorageError

    if case == "fixed-mismatch":
        t = schema.to_table((record(),), "canonical/v1")
        i = t.schema.get_field_index("value_fixed")
        t = t.set_column(
            i, t.schema.field(i), pa.array([Decimal("2.5")], type=pa.decimal128(38, 12))
        )
        with pytest.raises(StorageError, match="SCALAR"):
            schema.from_table(t)
    elif case == "overflow":
        with pytest.raises(StorageError):
            schema.encode_decimal(Decimal("9e10000"), "CALCULATION")
    elif case == "zero-scale":
        assert (
            schema.decode_decimal(schema.encode_decimal(Decimal("0E-90"), "RAW")).as_tuple()
            == Decimal("0E-90").as_tuple()
        )
    elif case == "fraction":
        r = record(
            value=Decimal("0.125"),
            rational_numerator="1",
            rational_denominator="8",
            lineage=(("control", "00001", "a" * 64),),
        )
        assert schema.from_table(schema.to_table((r,), "canonical/v1")) == (r,)
    elif case == "negative":
        assert schema.decode_decimal(schema.encode_decimal(Decimal("-1.25"))) == Decimal("-1.25")
    else:
        assert schema.decode_decimal(
            schema.encode_decimal(Decimal("9" * 26 + "." + "9" * 12))
        ) == Decimal("9" * 26 + "." + "9" * 12)


@pytest.mark.parametrize(
    "case",
    [
        "durable",
        "changed-id",
        "future",
        "join",
        "rollback",
        "foreign-key",
        "immutable",
        "unknown-root",
    ],
)
def test_durable_typed_metadata_admission(case, tmp_path):
    from sqlalchemy import text

    from omegadata.canonical_storage.contracts import StorageError
    from omegadata.parsers.contracts import ParseResult

    db = database(tmp_path)
    payload = ParseResult("PARSED_UNVERIFIED", "a" * 64)
    if case == "unknown-root":
        from omegadata.canonical_storage.store import CanonicalStore

        unknown = tmp_path / "unknown"
        unknown.mkdir()
        (unknown / "retained").write_text("NON_MARKET_METADATA")
        with pytest.raises(StorageError):
            CanonicalStore(unknown, disposable_root=tmp_path)
        return
    if case == "rollback":
        db.rollback_empty()
        db.close()
        db = database(tmp_path)
        assert db.operation_version("none") is None
        commit(db)
        with pytest.raises(StorageError):
            db.rollback_empty()
        return
    if case == "foreign-key":
        with pytest.raises(Exception, match="FOREIGN KEY"), db.transaction() as con:
            con.execute(text("INSERT INTO commit_operation VALUES ('orphan','x','absent')"))
        return
    ref = db.pin_domain("source_observations", "parser-identity", payload, K)
    if case == "changed-id":
        with pytest.raises(StorageError):
            db.pin_domain(
                "source_observations", "parser-identity", replace(payload, raw_sha256="b" * 64), K
            )
    elif case == "future":
        with pytest.raises(StorageError, match="FUTURE"):
            db.read_domain(ref, K - timedelta(seconds=1))
    elif case == "join":
        v = commit(db)
        joined = db.query_join(
            query=__import__("omegadata.canonical_storage.contracts", fromlist=["Query"]).Query(
                v, "control-dataset", D, D + timedelta(days=1), K, "RAW_UNADJUSTED", "AUDIT"
            ),
            references=(ref,),
        )
        assert joined["metadata"][0] == payload and len(joined["rows"]) == 1
    elif case == "immutable":
        with pytest.raises(Exception, match="IMMUTABLE"), db.transaction() as con:
            con.execute(text("UPDATE typed_reference SET payload='changed'"))
    else:
        db.close()
        db = database(tmp_path)
        assert db.read_domain(ref, K) == payload


@pytest.mark.parametrize(
    "case",
    [
        "denied",
        "metadata-only",
        "forged-authority",
        "derived-unbound",
        "wrong-domain",
        "raw-price-field-mismatch",
    ],
)
def test_admission_refuses_unbound_or_unauthorized_payload(case, tmp_path):
    from omegadata.canonical_storage.contracts import StorageError

    db = database(tmp_path)
    kw = {
        "denied": {"source_rights_state": "DENIED"},
        "metadata-only": {"source_rights_state": "METADATA_ONLY"},
        "forged-authority": {
            "observation_classification": "APPROVED_AUTHENTIC_SOURCE",
            "source_rights_state": "PERMITTED",
        },
        "derived-unbound": {"price_basis": "BACKWARD_ADJUSTED", "numeric_kind": "CALCULATION"},
        "wrong-domain": {},
        "raw-price-field-mismatch": {"field_semantics": "OPEN", "observation_type": "RAW_CLOSE"},
    }[case]
    definition = (
        {"layer": "DERIVED", "domain": "adjustment_results", "price_basis": "BACKWARD_ADJUSTED"}
        if case == "derived-unbound"
        else {"domain": "adjustment_results"}
        if case == "wrong-domain"
        else {}
    )
    with pytest.raises(StorageError):
        commit(db, rows=(record(**kw),), definition=definition)


def test_query_projection_aggregate_and_partition_pruning(tmp_path):
    from omegadata.canonical_storage.contracts import DatasetDefinition, StorageError
    from omegadata.canonical_storage.query import aggregate_scalar

    db = database(tmp_path)
    rows = (
        record(),
        record(
            observation_id="other",
            observation_revision_id="other",
            listing_id="00002",
            trade_date=date(2020, 2, 3),
            session_date=date(2020, 2, 3),
            value=Decimal("0.75"),
        ),
    )
    definition = DatasetDefinition(
        "control-dataset",
        "source_observations",
        "RAW",
        "canonical/v1",
        "RAW_UNADJUSTED",
        "AUDIT",
        ("control-source",),
    )
    v = db.commit(
        definition,
        rows,
        operation_id="two-months",
        expected_partitions=("CANARY-X/2020-01", "CANARY-X/2020-02"),
    )
    q = query(db, v, columns=("listing_id", "value"))
    assert (
        q.rows == ({"listing_id": "00001", "value": Decimal("1.2500")},)
        and q.files_scanned == 1
        and q.files_verified == 2
    )
    assert aggregate_scalar(q.rows)["sum_exact"] == (5, 4)
    with pytest.raises(StorageError):
        query(db, v, columns=("arbitrary_sql()",))


def test_independently_declared_comparison_scope_rejects_metadata_relabel():
    from test_od09_reconciliation import controls

    from omegadata.canonical_storage.admission import (
        ProvenanceLedger,
        SourceBinding,
        admit_comparison,
    )
    from omegadata.canonical_storage.contracts import StorageError
    from omegadata.reconciliation.engine import reconcile_context

    _, x, a, b = controls()
    ledger = ProvenanceLedger()
    ledger.pin_observations((a, b))
    for changed in (
        replace(a, publisher_identity="forged"),
        replace(a, symbol_as_reported="NEW"),
        replace(a, source_lineage_root="fake"),
    ):
        with pytest.raises(StorageError):
            ledger.verify_source(changed, SourceBinding.from_observation(a))
    future = replace(b, availability=replace(b.availability, known_from=K + timedelta(days=1)))
    ledger = ProvenanceLedger()
    ledger.pin_observations((a, future))
    assert (
        admit_comparison(
            replace(x, right=()),
            reconcile_context(replace(x, right=())),
            ledger,
            (a.observation_id, b.observation_id),
            True,
        ).coverage_state
        == "COMPLETE_DECLARED_SCOPE"
    )


def test_bound_derived_volume_admission_replays_exact_upstream(tmp_path):
    from test_od07_final import D as BD
    from test_od07_final import setup_bound

    from omegadata.adjustments import bound_contracts as bc
    from omegadata.adjustments.bound_chain import calculate_bound_chain
    from omegadata.adjustments.contracts import digest
    from omegadata.canonical_storage.admission import derived_lineage
    from omegadata.canonical_storage.contracts import DatasetDefinition, StorageError
    from omegadata.reconciliation.dependencies import UpstreamProof
    from omegadata.universe.contracts import AvailabilityObservation
    from omegadata.universe.observation_binding import AdjustmentBinding

    parts = setup_bound(basis=bc.BasisPolicy("VOLUME", "BACKWARD_ADJUSTED", BD + timedelta(days=5)))
    pin = parts[8]
    bound = calculate_bound_chain(pin)
    raw = pin.raw.raw
    o = AvailabilityObservation(
        "bound-volume",
        "CONTROL_ONLY",
        raw.listing_id,
        raw.trade_date,
        None,
        raw.known_from,
        None,
        raw.known_from,
        None,
        None,
        pin.raw.source_id,
        raw.artifact_id,
        raw.evidence,
        interval_completed_at=raw.known_from,
        record_identity=pin.raw.source_record_identity,
        volume=bound.calculation.adjusted_volume,
        currency=raw.currency,
        price_unit=pin.raw.price_unit,
        price_basis="RAW_UNADJUSTED",
        volume_basis="BACKWARD_ADJUSTED",
        adjustment=bound,
        adjustment_pin=pin,
    )
    binding = AdjustmentBinding(
        o.observation_id,
        pin.raw.source_record_identity,
        raw.artifact_id,
        raw.security_id,
        raw.listing_id,
        raw.exchange,
        raw.trade_date,
        pin.raw.observation_id,
        digest(pin.raw),
        pin.snapshot_id,
        bound.output_digest,
        pin.policy.profile,
        bound.adjustment_basis,
        bound.basis_date,
        raw.currency,
        pin.raw.price_unit,
        "SHARES",
        "volume",
        o.volume,
        pin.context.known_at,
    )
    o = replace(o, adjustment_binding=binding)
    proof = UpstreamProof("ADJUSTMENT", "prior-output", "a" * 64, o, bound, pin)
    row = record(
        observation_id=o.observation_id,
        source_id=o.source_id,
        source_artifact_identity=o.artifact_identity,
        source_record_identity=o.record_identity,
        security_id=raw.security_id,
        listing_id=raw.listing_id,
        exchange=raw.exchange,
        trade_date=raw.trade_date,
        session_date=raw.trade_date,
        currency=raw.currency,
        price_unit=pin.raw.price_unit,
        volume_unit="SHARES",
        price_basis="RAW_UNADJUSTED",
        volume_basis="BACKWARD_ADJUSTED",
        field_semantics="VOLUME",
        numeric_kind="CALCULATION",
        value=o.volume,
        known_from=pin.context.known_at,
        lineage=derived_lineage(proof),
    )
    definition = DatasetDefinition(
        "derived-volume",
        "adjustment_results",
        "DERIVED",
        "canonical/v1",
        "RAW_UNADJUSTED",
        "AUDIT",
        (o.source_id,),
        volume_basis="BACKWARD_ADJUSTED",
    )
    db = database(tmp_path)
    v = db.commit(
        definition,
        (row,),
        operation_id="bound-control",
        expected_partitions=(raw.exchange + "/" + raw.trade_date.strftime("%Y-%m"),),
        proofs=(proof,),
    )
    assert db.verify(v)["verified"] and db.manifest(v)["layer"] == "DERIVED"
    with pytest.raises(StorageError):
        db.commit(
            definition,
            (replace(row, value=row.value + Decimal(1)),),
            operation_id="wrong-consumed-field",
            parent_version=v,
            expected_partitions=(raw.exchange + "/" + raw.trade_date.strftime("%Y-%m"),),
            proofs=(proof,),
        )


@pytest.mark.parametrize(
    "case", ["omitted", "future", "unrelated", "conflict", "unknown-time", "restart"]
)
def test_persisted_comparison_scope_independent_selection(case, tmp_path):
    from test_od09_reconciliation import controls

    from omegadata.canonical_storage.admission import ComparisonScope
    from omegadata.canonical_storage.contracts import StorageError
    from omegadata.reconciliation.engine import reconcile_context

    _, x, a, b = controls()
    db = database(tmp_path)
    scope = ComparisonScope(
        "scope",
        ("control-source",),
        (a.listing_id,),
        ("close",),
        a.session_date,
        a.session_date + timedelta(days=1),
        x.known_at,
    )
    if case == "future":
        b = replace(b, availability=replace(b.availability, known_from=K + timedelta(days=1)))
    if case == "unknown-time":
        b = replace(b, availability=replace(b.availability, known_from=None))
    db.pin_source_observations((a, b))
    db.pin_comparison_scope(scope)
    selected = replace(x, right=()) if case in {"omitted", "future", "unknown-time"} else x
    if case == "unrelated":
        db.pin_source_observations(
            (
                replace(
                    b,
                    field_name="open",
                    availability=replace(b.availability, observation_id="unrelated"),
                ),
            )
        )
    if case == "conflict":
        db.pin_source_observations(
            (replace(b, availability=replace(b.availability, observation_id="conflict")),)
        )
    if case == "restart":
        db.close()
        db = database(tmp_path)
    if case in {"omitted", "conflict", "unknown-time"}:
        with pytest.raises(StorageError):
            db.admit_comparison_scope("scope", selected, reconcile_context(selected), complete=True)
    else:
        result = db.admit_comparison_scope(
            "scope", selected, reconcile_context(selected), complete=True
        )
        assert (
            result.coverage_state == "COMPLETE_REQUIRED_LEDGER_SET"
            and not result.financial_eligible
        )


def test_transitive_dependency_index_uses_pinned_metadata(tmp_path):
    from omegadata.parsers.contracts import ParseResult

    db = database(tmp_path)
    a = db.pin_domain("source_observations", "a", ParseResult("PARSED_UNVERIFIED", "a" * 64), K)
    b = db.pin_domain(
        "source_observations", "b", ParseResult("PARSED_UNVERIFIED", "b" * 64), K, dependencies=(a,)
    )
    v = commit(db, rows=(record(lineage=(b,)),))
    out = db.impact(a[0], a[1], K)
    assert out["dataset_versions"] == [v] and out["coverage_state"] == "DEPENDENCY_UNKNOWN"
    assert db.impact(a[0], a[1], K - timedelta(seconds=1))["dataset_versions"] == []


@pytest.mark.parametrize("kind", ["symlink", "hardlink"])
def test_file_link_escape_refused(kind, tmp_path):
    import os

    from omegadata.canonical_storage.contracts import StorageError

    db = database(tmp_path)
    v = commit(db)
    p = tmp_path / "store" / db.manifest(v)["file_entries"][0]["relative_path"]
    target = tmp_path / "CONTROL_ONLY.parquet"
    target.write_bytes(p.read_bytes())
    if kind == "symlink":
        p.rename(p.with_suffix(".retained"))
        p.symlink_to(target)
    else:
        os.link(p, tmp_path / "CONTROL_ONLY.hardlink")
    with pytest.raises(StorageError):
        db.verify(v)


def test_canonical_UTC_retry_and_derived_hard_blocks(tmp_path):
    db = database(tmp_path)
    v = commit(db)
    shifted = record(known_from=K.astimezone(timezone(timedelta(hours=5, minutes=30))))
    assert commit(db, rows=(shifted,)) == v
    empty = record(security_id=None, listing_id=None, known_from=None, hard_block_reasons=())
    assert {"IDENTITY_UNRESOLVED", "AVAILABILITY_UNKNOWN", "NON_MARKET_CONTROL"} <= set(
        empty.hard_block_reasons
    )


def test_generic_pin_cannot_bypass_required_observation_index(tmp_path):
    from test_od09_reconciliation import controls

    from omegadata.canonical_storage.admission import ComparisonScope
    from omegadata.canonical_storage.contracts import StorageError
    from omegadata.reconciliation.engine import reconcile_context

    _, x, a, b = controls()
    db = database(tmp_path)
    db.pin_source_observations((a,))
    db.pin_domain("source_observations", b.observation_id, b, b.availability.known_from)
    db.pin_comparison_scope(
        ComparisonScope(
            "scope",
            ("control-source",),
            (a.listing_id,),
            ("close",),
            a.session_date,
            a.session_date + timedelta(days=1),
            x.known_at,
        )
    )
    omitted = replace(x, right=())
    with pytest.raises(StorageError):
        db.admit_comparison_scope("scope", omitted, reconcile_context(omitted), complete=True)


def test_dependency_set_cannot_mutate_existing_pin(tmp_path):
    from omegadata.canonical_storage.contracts import StorageError
    from omegadata.parsers.contracts import ParseResult

    db = database(tmp_path)
    p = ParseResult("PARSED_UNVERIFIED", "a" * 64)
    db.pin_domain("source_observations", "immutable-pin", p, K)
    with pytest.raises(StorageError):
        db.pin_domain(
            "source_observations",
            "immutable-pin",
            p,
            K,
            dependencies=(("external", "new", "a" * 64),),
        )


@pytest.mark.parametrize('field',['partition_identity','minimum_trade_date','maximum_known_from','compression','row_count','relative_path'])
def test_file_manifest_semantics_independently_reconciled(field,tmp_path):
 from omegadata.canonical_storage.contracts import StorageError
 db=database(tmp_path);v=commit(db);entry=dict(db.manifest(v)['file_entries'][0])
 entry[field]={'partition_identity':'CANARY-X/1999-01','minimum_trade_date':'1999-01-01','maximum_known_from':(K+timedelta(days=1)).isoformat(),'compression':'snappy','row_count':True,'relative_path':'objects/not-an-identity.parquet'}[field]
 with pytest.raises(StorageError):db.verify_file(entry)

def test_version_identity_cannot_alias_different_manifests_across_catalogs(tmp_path):
 first=tmp_path/'first';second=tmp_path/'second';first.mkdir();second.mkdir()
 a=database(first);b=database(second)
 av=commit(a);bv=commit(b)
 assert av!=bv or a.manifest(av)==b.manifest(bv)

def test_strict_metadata_domain_and_reconciliation_admission(tmp_path):
 from omegadata.canonical_storage.admission import ComparisonScope
 from omegadata.canonical_storage.contracts import StorageError
 from omegadata.parsers.contracts import ParseResult
 from test_od09_reconciliation import controls
 from omegadata.reconciliation.engine import reconcile_context
 db=database(tmp_path)
 with pytest.raises(StorageError):db.pin_domain('review_revisions','wrong-kind',ParseResult('PARSED_UNVERIFIED','a'*64),K)
 _,x,a,b=controls();db.pin_source_observations((a,b))
 db.pin_comparison_scope(ComparisonScope('scope',('control-source',),(a.listing_id,),('close',),a.session_date,a.session_date+timedelta(days=1),x.known_at))
 result=reconcile_context(x)[0]
 ref=db.pin_domain('reconciliation_results','result',result,x.known_at,context=('scope',x))
 assert db.read_domain(ref,x.known_at)==result
 with pytest.raises(StorageError):db.pin_domain('reconciliation_results','wrong-result',replace(result,outcome='FAIL'),x.known_at,context=('scope',x))

def test_actual_stable_identity_metadata_join(tmp_path):
 from omegadata.identity import Listing
 from omegadata.canonical_storage.contracts import Query
 db=database(tmp_path);v=commit(db)
 listing=Listing('00001','control-security','CANARY-X')
 ref=db.pin_domain('instrument_identity_revisions','listing-reference',listing,K)
 out=db.query_join(query=Query(v,'control-dataset',D,D+timedelta(days=1),K,'RAW_UNADJUSTED','AUDIT'),references=(ref,),join_key='listing_id')
 assert out['joined'][0]['status']=='MATCHED_UNVERIFIED' and out['joined'][0]['metadata']==listing and not out['financial_eligible']