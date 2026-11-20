"""Owned disposable SQLite, existing SQLAlchemy transactions and typed payload codec.
No operational databases, automatic cleanup, original data or production migrations.
"""

from __future__ import annotations

import hashlib
from dataclasses import is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    MetaData,
    String,
    Table,
    create_engine,
    event,
    func,
    inspect,
    select,
)
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.pool import StaticPool

from omegadata.identity_authority import EvidenceAuthority
from omegadata.reconciliation import anomalies as a
from omegadata.reconciliation import contracts as c
from omegadata.reconciliation import dependencies as d
from omegadata.reconciliation import reviews as r
from omegadata.reconciliation import tolerances as t
from omegadata.reconciliation.engine import reconcile_context
from omegadata.universe import repository as upstream

M = MetaData()
schema = Table("od09_schema", M, Column("version", String, primary_key=True))


def columns() -> list[Column[Any]]:
    return [Column("payload", String, nullable=False), Column("digest", String, nullable=False)]


policies = Table("od09_tolerance", M, Column("id", String, primary_key=True), *columns())
contexts = Table(
    "od09_comparison_context",
    M,
    Column("id", String, primary_key=True),
    Column("policy", ForeignKey(policies.c.id), nullable=False),
    *columns(),
)
results = Table(
    "od09_reconciliation_result",
    M,
    Column("id", String, primary_key=True),
    Column("context", ForeignKey(contexts.c.id), nullable=False),
    *columns(),
)
anomalies = Table(
    "od09_anomaly",
    M,
    Column("id", String, primary_key=True),
    Column("context", ForeignKey(contexts.c.id), nullable=False),
    *columns(),
)
reviews = Table(
    "od09_review_revision",
    M,
    Column("id", String, primary_key=True),
    Column("result", ForeignKey(results.c.id), nullable=False),
    Column("review", String, nullable=False),
    Column("parent", ForeignKey("od09_review_revision.id"), unique=True),
    *columns(),
)
Index(
    "od09_one_review_root", reviews.c.review, unique=True, sqlite_where=reviews.c.parent.is_(None)
)
corrections = Table(
    "od09_correction_revision",
    M,
    Column("id", String, primary_key=True),
    Column("review", ForeignKey(reviews.c.id), nullable=False, unique=True),
    *columns(),
)
requests = Table(
    "od09_reprocess_request",
    M,
    Column("id", String, primary_key=True),
    Column("correction", ForeignKey(corrections.c.id), nullable=False),
    *columns(),
)
completions = Table(
    "od09_reprocess_result",
    M,
    Column("id", String, primary_key=True),
    Column("request", ForeignKey(requests.c.id), nullable=False),
    *columns(),
)
inputs = Table(
    "od09_input_index",
    M,
    Column("context", ForeignKey(contexts.c.id), primary_key=True),
    Column("observation", String, primary_key=True),
    Column("observation_digest", String, nullable=False),
)
Index("od09_input_digest", inputs.c.observation_digest, inputs.c.context)
replacements = Table(
    "od09_replacement_context",
    M,
    Column("id", String, primary_key=True),
    Column("correction", ForeignKey(corrections.c.id), nullable=False),
    Column("old_context", ForeignKey(contexts.c.id), nullable=False),
    Column("new_context", ForeignKey(contexts.c.id), nullable=False),
    *columns(),
)
Index("od09_replacement_scope", replacements.c.correction, replacements.c.old_context, unique=True)
Index("od09_result_context", results.c.context)
Index("od09_review_scope", reviews.c.review, reviews.c.result)

TYPES = {
    cls.__name__: cls
    for module in (c, r, t, a, d)
    for cls in vars(module).values()
    if isinstance(cls, type) and is_dataclass(cls) and cls.__module__ == module.__name__
}
upstream.TYPES.update(TYPES)


class ReconciliationRepository(upstream.UniverseRepository):
    transaction = upstream.UniverseRepository.transaction
    _put = upstream.UniverseRepository._put
    close = upstream.UniverseRepository.close

    def __init__(
        self, url: str, *, disposable_root: Path, authority: EvidenceAuthority | None = None
    ) -> None:
        parsed = make_url(url)
        if parsed.drivername not in {"sqlite", "sqlite+pysqlite"}:
            raise ValueError("DEVELOPMENT_SQLITE_ONLY")
        if parsed.database not in {None, "", ":memory:"}:
            path = Path(str(parsed.database))
            root = disposable_root.resolve(strict=True)
            if (
                not path.is_absolute()
                or ".." in path.parts
                or path.is_symlink()
                or not path.resolve().is_relative_to(root)
                or any(p.is_symlink() for p in path.parents)
            ):
                raise ValueError("DISPOSABLE_DATABASE_REQUIRED")
        self.authority = authority
        self.engine = create_engine(
            url,
            poolclass=StaticPool if parsed.database in {None, "", ":memory:"} else None,
            connect_args={"check_same_thread": False, "timeout": 5},
        )

        @event.listens_for(self.engine, "connect")
        def enable_fk(dbapi: Any, record: Any) -> None:
            dbapi.execute("PRAGMA foreign_keys=ON")

        existing = set(inspect(self.engine).get_table_names())
        if existing and existing != set(M.tables):
            raise ValueError("OWNED_SCHEMA_REQUIRED")
        with self.engine.begin() as con:
            M.create_all(con)
            versions = tuple(con.execute(select(schema.c.version)).scalars())
            if versions and versions != ("od09.store/v1",):
                raise ValueError("SCHEMA_VERSION_UNSUPPORTED")
            if not versions:
                con.execute(schema.insert().values(version="od09.store/v1"))
            for table in M.tables.values():
                for op in ("UPDATE", "DELETE"):
                    con.exec_driver_sql(
                        f"CREATE TRIGGER IF NOT EXISTS {table.name}_{op.lower()} BEFORE {op} ON {table.name} BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END"
                    )

    def _load(self, con: Connection, table: Table, key: str) -> Any:
        row = con.execute(select(table.c.payload, table.c.digest).where(table.c.id == key)).first()
        if row is None:
            raise ValueError("PERSISTED_INPUT_REQUIRED")
        if hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
            raise ValueError("PERSISTED_PAYLOAD_CHANGED")
        return upstream.unpack(row[0], self.authority)

    def pin_comparison(self, x: c.ComparisonContext) -> None:
        with self.transaction() as con:
            self._put(con, policies, c.fingerprint(x.policy), x.policy)
            self._put(con, contexts, x.context_id, x, policy=c.fingerprint(x.policy))
            for o in x.left + x.right:
                old = con.scalar(
                    select(inputs.c.observation_digest).where(
                        inputs.c.context == x.context_id, inputs.c.observation == o.observation_id
                    )
                )
                if old is None:
                    con.execute(
                        inputs.insert().values(
                            context=x.context_id,
                            observation=o.observation_id,
                            observation_digest=c.fingerprint(o),
                        )
                    )
                elif old != c.fingerprint(o):
                    raise ValueError("INPUT_INDEX_CHANGED")

    def admit_results(self, context_id: str, submitted: tuple[c.ReconciliationResult, ...]) -> None:
        with self.transaction() as con:
            x = self._load(con, contexts, context_id)
            if not isinstance(x, c.ComparisonContext):
                raise ValueError("COMPARISON_CONTEXT_TYPE")
            if upstream.pack(reconcile_context(x)) != upstream.pack(submitted):
                raise ValueError("INDEPENDENT_RECONCILIATION_MISMATCH")
            for value in submitted:
                if (
                    value.financial_eligibility
                    or value.publication_eligibility
                    or value.execution_eligibility
                ):
                    raise ValueError("FINANCIAL_PROMOTION_NOT_AUTHORIZED")
                self._put(con, results, value.reconciliation_id, value, context=context_id)

    def replay(self, context_id: str) -> tuple[c.ReconciliationResult, ...]:
        with self.transaction() as con:
            return reconcile_context(self._load(con, contexts, context_id))

    def append_anomaly(self, anomaly_id: str, context_id: str, value: Any) -> None:
        with self.transaction() as con:
            context = self._load(con, contexts, context_id)
            if (
                type(value) is not a.AnomalyRecord
                or value.anomaly_id != anomaly_id
                or value not in a.evaluate_anomalies(context)
            ):
                raise ValueError("ANOMALY_INDEPENDENT_RECONCILIATION_MISMATCH")
            self._put(con, anomalies, anomaly_id, value, context=context_id)

    def append_review(self, value: r.ReviewRevision) -> None:
        with self.transaction() as con:
            old = con.scalar(select(reviews.c.payload).where(reviews.c.id == value.revision_id))
            if old is not None:
                if old != upstream.pack(value):
                    raise ValueError("IMMUTABLE_RECORD_ID_REUSED")
                return
            result = self._load(con, results, value.discrepancy_id)
            x = self._load(con, contexts, result.context_id)
            ids = set(result.left_observation_ids + result.right_observation_ids)
            expected_scope = tuple(
                sorted({o.listing_id for o in x.left + x.right if o.observation_id in ids})
            )
            if value.affected_scope != expected_scope:
                raise ValueError("REVIEW_AFFECTED_SCOPE_MISMATCH")
            parent = None
            if value.previous_record_digest is None:
                if value.state != "OPEN" or value.reviewer_identity is not None:
                    raise ValueError("REVIEW_ROOT_REQUIRED")
            else:
                parent = con.scalar(
                    select(reviews.c.id).where(reviews.c.digest == value.previous_record_digest)
                )
                if parent is None:
                    raise ValueError("REVIEW_PARENT_REQUIRED")
                before = self._load(con, reviews, parent)
                if value.reviewer_identity is None or value.decision_reason is None:
                    raise ValueError("REVIEW_DECISION_FIELDS_REQUIRED")
                if value.reprocess_evidence is not None:
                    req, complete, completion_attestation = value.reprocess_evidence
                    if upstream.pack(self._load(con, requests, req.request_id)) != upstream.pack(
                        req
                    ) or upstream.pack(
                        self._load(con, completions, complete.completion_id)
                    ) != upstream.pack(complete):
                        raise ValueError("REVIEW_COMPLETION_NOT_PERSISTED")
                    correction = self._load(con, corrections, req.approved_correction_id)
                    approved = self._load(con, reviews, correction.approved_review_revision)
                    if approved.review_id != value.review_id:
                        raise ValueError("REVIEW_COMPLETION_SCOPE_MISMATCH")
                rebuilt = r.advance_review(
                    before,
                    value.state,
                    value.revision_id,
                    value.created_at,
                    value.reviewer_identity,
                    value.decision_reason,
                    tuple(
                        v for v in value.evidence_references if v not in before.evidence_references
                    ),
                    mode=x.universe.mode,
                    authority=self.authority,
                    attestation=value.reviewer_attestation,
                    proposed_revision_digest=value.proposed_revision_digest,
                    reprocess_evidence=value.reprocess_evidence,
                )
                if upstream.pack(rebuilt) != upstream.pack(value):
                    raise ValueError("REVIEW_LINEAGE_MISMATCH")
            self._put(
                con,
                reviews,
                value.revision_id,
                value,
                result=value.discrepancy_id,
                review=value.review_id,
                parent=parent,
            )

    def append_correction(self, value: r.CorrectionRevision) -> None:
        with self.transaction() as con:
            review = self._load(con, reviews, value.approved_review_revision)
            if (
                review.state != "APPROVED"
                or review.proposed_revision_digest != value.proposed_revision_digest
                or review.affected_scope != value.affected_scope
                or value.known_from < review.created_at
                or not set(value.evidence_references).issubset(review.evidence_references)
            ):
                raise ValueError("CORRECTION_NOT_APPROVED_OR_SCOPE_MISMATCH")
            self._put(
                con, corrections, value.correction_id, value, review=value.approved_review_revision
            )

    def pin_replacement_context(
        self,
        correction_id: str,
        old_context_id: str,
        new_context_id: str,
        *,
        proofs: tuple[d.UpstreamProof, ...] = (),
    ) -> None:
        with self.transaction() as con:
            correction = self._load(con, corrections, correction_id)
            old = self._load(con, contexts, old_context_id)
            new = self._load(con, contexts, new_context_id)
            oldrows = old.left + old.right
            newrows = new.left + new.right
            before = tuple(
                o for o in oldrows if c.fingerprint(o) == correction.previous_record_digest
            )
            after = tuple(
                o for o in newrows if c.fingerprint(o) == correction.proposed_revision_digest
            )
            if (
                len(before) != 1
                or len(after) != 1
                or new.known_at < correction.known_from
                or old.valid_at != new.valid_at
                or old.policy != new.policy
            ):
                raise ValueError("REPLACEMENT_CONTEXT_SCOPE_OR_KNOWLEDGE_MISMATCH")
            if (
                before[0].security_id,
                before[0].listing_id,
                before[0].exchange,
                before[0].session_date,
                before[0].field_name,
            ) != (
                after[0].security_id,
                after[0].listing_id,
                after[0].exchange,
                after[0].session_date,
                after[0].field_name,
            ):
                raise ValueError("REPLACEMENT_RECORD_SCOPE_MISMATCH")
            if sorted(c.fingerprint(o) for o in oldrows if o not in before) != sorted(
                c.fingerprint(o) for o in newrows if o not in after
            ):
                raise ValueError("REPLACEMENT_CHANGED_UNRELATED_INPUT")
            required = set()
            if before[0].availability.adjustment is not None:
                required.add(("ADJUSTMENT", before[0].availability.adjustment.output_digest))
            if before[0].universe_snapshot_id:
                required.add(("UNIVERSE", before[0].universe_snapshot_id))
            if {(p.kind, p.old_output_id) for p in proofs} != required or len(proofs) != len(
                required
            ):
                raise ValueError("REPROCESS_DOWNSTREAM_PROOF_REQUIRED")
            if any(
                p.source_revision_digest != correction.proposed_revision_digest
                or p.source_observation != after[0].availability
                or not d.verify_upstream(p, new.known_at)
                for p in proofs
            ):
                raise ValueError("REPROCESS_DOWNSTREAM_PROOF_MISMATCH")
            key = c.fingerprint((correction_id, old_context_id))
            self._put(
                con,
                replacements,
                key,
                (correction_id, old_context_id, new_context_id, proofs),
                correction=correction_id,
                old_context=old_context_id,
                new_context=new_context_id,
            )

    def _impact(self, con: Connection, request_id: str, correction_id: str) -> r.ReprocessRequest:
        correction = self._load(con, corrections, correction_id)
        affected = []
        adjusted = set()
        universes = set()
        sessions = set()
        result_ids: set[str] = set()
        expected_outputs: set[tuple[str, str]] = set()
        dependency_versions = set()
        for context_id in con.execute(
            select(inputs.c.context)
            .where(inputs.c.observation_digest == correction.previous_record_digest)
            .distinct()
            .order_by(inputs.c.context)
        ).scalars():
            x = self._load(con, contexts, context_id)
            observed = tuple(
                o for o in x.left + x.right if c.fingerprint(o) == correction.previous_record_digest
            )
            if not observed:
                continue
            affected.append(context_id)
            new_id = con.scalar(
                select(replacements.c.new_context).where(
                    replacements.c.correction == correction_id,
                    replacements.c.old_context == context_id,
                )
            )
            if new_id is None:
                raise ValueError("REPROCESS_REPLACEMENT_CONTEXT_REQUIRED")
            proofrow = self._load(con, replacements, c.fingerprint((correction_id, context_id)))
            proofset = proofrow[3]
            replacement = self._load(con, contexts, new_id)
            for proof in proofset:
                if not d.verify_upstream(proof, replacement.known_at):
                    raise ValueError("REPROCESS_DOWNSTREAM_PROOF_CHANGED")
                expected_outputs.add((proof.output_identity, proof.output_identity))
                dependency_versions.add(
                    ("downstream:" + proof.kind + ":" + proof.old_output_id, c.fingerprint(proof))
                )
            expected_outputs.update(
                (v.reconciliation_id, v.result_digest) for v in reconcile_context(replacement)
            )
            dependency_versions.add(("replacement:" + context_id, c.fingerprint(replacement)))
            dependency_versions.add(
                ("policy:" + replacement.policy.policy_id, c.fingerprint(replacement.policy))
            )
            for o in observed:
                sessions.add(o.session_date)
                if o.universe_snapshot_id:
                    universes.add(o.universe_snapshot_id)
                if o.availability.adjustment is not None:
                    adjusted.add(o.availability.adjustment.output_digest)
            result_ids.update(
                con.execute(select(results.c.id).where(results.c.context == context_id)).scalars()
            )
        if not affected:
            raise ValueError("REPROCESS_AFFECTED_SCOPE_UNKNOWN")
        return r.ReprocessRequest(
            request_id,
            correction_id,
            correction.affected_scope,
            tuple(sorted(sessions)),
            (correction.proposed_revision_digest,),
            tuple(sorted(adjusted)),
            tuple(sorted(universes)),
            tuple(sorted(result_ids)),
            tuple(
                sorted(dependency_versions | {("impact_contexts", c.fingerprint(tuple(affected)))})
            ),
            tuple(sorted(expected_outputs)),
        )

    def derive_reprocess_request(self, request_id: str, correction_id: str) -> r.ReprocessRequest:
        with self.transaction() as con:
            return self._impact(con, request_id, correction_id)

    def append_reprocess_request(self, value: r.ReprocessRequest) -> None:
        with self.transaction() as con:
            if value != self._impact(con, value.request_id, value.approved_correction_id):
                raise ValueError("REPROCESS_IMPACT_MISMATCH")
            self._put(
                con, requests, value.request_id, value, correction=value.approved_correction_id
            )

    def append_completion(
        self,
        value: r.ReprocessCompletion,
        *,
        attestation: r.ReviewerAttestation | None = None,
        at: datetime | None = None,
    ) -> str:
        with self.transaction() as con:
            request = self._load(con, requests, value.request_id)
            if (value.request_id, value.request_digest, value.adopted_correction_id) != (
                request.request_id,
                request.request_digest,
                request.approved_correction_id,
            ) or any(
                getattr(value, n) != getattr(request, n)
                for n in (
                    "source_record_revisions",
                    "affected_adjustment_outputs",
                    "affected_universe_snapshots",
                    "affected_reconciliation_results",
                    "required_dependency_versions",
                )
            ):
                raise ValueError("REPROCESS_PROGRESS_SCOPE_MISMATCH")
            if value.state in {"REQUESTED", "QUEUED", "RUNNING", "FAILED", "BLOCKED_DEPENDENCY"}:
                self._put(con, completions, value.completion_id, value, request=value.request_id)
                return value.state
            status = r.verify_completion(
                request, value, authority=self.authority, attestation=attestation, at=at
            )
            if status == "BLOCKED_DEPENDENCY" or value.state == "VERIFIED" and status != "VERIFIED":
                raise ValueError("REPROCESS_COMPLETION_MISMATCH")
            for identity, pin in request.expected_output_identities:
                if con.scalar(select(results.c.id).where(results.c.id == identity)) is not None:
                    output = self._load(con, results, identity)
                    actual_digest = c.fingerprint(output)
                else:
                    proofset = []
                    for key in con.execute(
                        select(replacements.c.id).where(
                            replacements.c.correction == request.approved_correction_id
                        )
                    ).scalars():
                        proofset.extend(self._load(con, replacements, key)[3])
                    candidates = [p for p in proofset if p.output_identity == identity]
                    if len(candidates) != 1 or not d.verify_upstream(
                        candidates[0],
                        max(
                            self._load(con, contexts, k).known_at
                            for k in con.execute(
                                select(replacements.c.new_context).where(
                                    replacements.c.correction == request.approved_correction_id
                                )
                            ).scalars()
                        ),
                    ):
                        raise ValueError("REPROCESS_DOWNSTREAM_OUTPUT_NOT_VERIFIED")
                    actual_digest = candidates[0].output_identity
                if actual_digest != pin:
                    raise ValueError("REPROCESS_EXPECTED_OUTPUT_NOT_ADMITTED")
            self._put(con, completions, value.completion_id, value, request=value.request_id)
            return status

    def get_review_history(self, review_id: str) -> tuple[r.ReviewRevision, ...]:
        with self.transaction() as con:
            ids = con.execute(select(reviews.c.id).where(reviews.c.review == review_id)).scalars()
            return tuple(
                sorted(
                    (self._load(con, reviews, k) for k in ids),
                    key=lambda v: (v.created_at, v.revision_id),
                )
            )

    def rollback_empty(self) -> None:
        with self.transaction() as con:
            if any(
                con.scalar(select(func.count()).select_from(table))
                for table in M.tables.values()
                if table is not schema
            ):
                raise ValueError("NONEMPTY_ROLLBACK_REFUSED")
            M.drop_all(con)
