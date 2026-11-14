# Component search evidence

Evidence: RUN; current working tree, 2026-11-14 UTC.

```powershell
rg -n 'def |class |known_from|published_at|first_observed|decision_at|supersed|delete\(|row\.|price_record\.' src/omegadata/track_b/isin_master.py src/omegadata/track_b/corporate_actions.py src/omegadata/track_b/publication.py src/omegadata/track_b/cross_source_validation.py src/omegadata/track_a/orchestration.py; rg -n 'def |source|raw_artifact|parser_version|release_id|observation_known' src/omegadata/db/models.py src/omegadata/pipelines/sequential_pipeline.py; rg -n 'reset-sqlite-db|unlink|profile_path|write_text' scripts/run_full_pipeline.py scripts/build_release_readiness_report.py; rg -n 'ready: true|fresh|official|14|5' README.md; rg -n '^#|^##|^###' 'plan - track A.md' 'plan - track B.md'; rg --files -g '*LICENSE*' -g '*lock*' -g '!**/.venv*/**' -g '!**/.git/**'
```

Exit code: 0

```text
Warning: truncated output (original token count: 6969)
Total output lines: 290

src/omegadata/track_a/orchestration.py:11:class IngestionOrchestrator:
src/omegadata/track_a/orchestration.py:12:    def __init__(self) -> None:
src/omegadata/track_a/orchestration.py:16:    def ingest_raw_source(self, source_key: str, as_of: date) -> str:
src/omegadata/track_a/orchestration.py:20:    def ingest_tabular_frame(self, dataset_name: str, as_of: date, frame: pd.DataFrame) -> str:
src/omegadata/track_b/corporate_actions.py:58:class ConfirmationResult:
src/omegadata/track_b/corporate_actions.py:63:class CorporateActionService:
src/omegadata/track_b/corporate_actions.py:64:    def __init__(self) -> None:
src/omegadata/track_b/corporate_actions.py:69:    def _validate_required_fields(action_type: CorporateActionType, payload: Mapping[str, object]) -> list[str]:
src/omegadata/track_b/corporate_actions.py:84:    def _merged_payload(
src/omegadata/track_b/corporate_actions.py:103:    def _review_exists(
src/omegadata/track_b/corporate_actions.py:121:    def _queue_review(
src/omegadata/track_b/corporate_actions.py:149:    def _required_fields_complete(
src/omegadata/track_b/corporate_actions.py:155:        errors = self._validate_required_fields(row.action_type, row.payload)
src/omegadata/track_b/corporate_actions.py:161:            isin=row.isin,
src/omegadata/track_b/corporate_actions.py:162:            event_date=row.ex_date,
src/omegadata/track_b/corporate_actions.py:164:            payload={"missing_fields": ",".join(errors), "source": row.source.value},
src/omegadata/track_b/corporate_actions.py:168:    def _required_fields_complete_payload(
src/omegadata/track_b/corporate_actions.py:176:        errors = self._validate_required_fields(row.action_type, payload)
src/omegadata/track_b/corporate_actions.py:182:            isin=row.isin,
src/omegadata/track_b/corporate_actions.py:183:            event_date=row.ex_date,
src/omegadata/track_b/corporate_actions.py:189:    def add_staging_record(
src/omegadata/track_b/corporate_actions.py:212:    def run_daily_confirmation(self, session: Session, as_of: date) -> list[ConfirmationResult]:
src/omegadata/track_b/corporate_actions.py:219:            grouped.setdefault(row.isin, []).append(row)
src/omegadata/track_b/corporate_actions.py:223:            nse_rows = [row for row in rows if row.source == Exchange.NSE]
src/omegadata/track_b/corporate_actions.py:224:            bse_rows = [row for row in rows if row.source in {Exchange.BSE, Exchange.BSE_ONLY}]
src/omegadata/track_b/corporate_actions.py:258:    def _is_stale_unmatched(row: CorporateActionStaging, as_of: date) -> bool:
src/omegadata/track_b/corporate_actions.py:263:                row.ex_date,
src/omegadata/track_b/corporate_actions.py:264:                row.record_date,
src/omegadata/track_b/corporate_actions.py:265:                row.announcement_date,
src/omegadata/track_b/corporate_actions.py:266:                row.fetched_at.date(),
src/omegadata/track_b/corporate_actions.py:274:    def _confirm_pair(
src/omegadata/track_b/corporate_actions.py:321:            superseded=False,
src/omegadata/track_b/corporate_actions.py:329:    def _confirm_single(
src/omegadata/track_b/corporate_actions.py:333:            raise ValueError(f"Corporate action {row.id} cannot be auto-confirmed with missing required fields")
src/omegadata/track_b/corporate_actions.py:339:                isin=row.isin,
src/omegadata/track_b/corporate_actions.py:340:                event_date=row.ex_date,
src/omegadata/track_b/corporate_actions.py:342:                payload={"action_type": row.action_type.value},
src/omegadata/track_b/corporate_actions.py:346:            isin=row.isin,
src/omegadata/track_b/corporate_actions.py:347:            action_type=row.action_type,
src/omegadata/track_b/corporate_actions.py:349:            announcement_date=row.announcement_date,
src/omegadata/track_b/corporate_actions.py:350:            ex_date=row.ex_date,
src/omegadata/track_b/corporate_actions.py:351:            record_date=row.record_date,
src/omegadata/track_b/corporate_actions.py:352:            parameters=row.payload,
src/omegadata/track_b/corporate_actions.py:353:            source_preference=row.source,
src/omegadata/track_b/corporate_actions.py:354:            superseded=False,
src/omegadata/track_b/corporate_actions.py:356:        row.matched = True
src/omegadata/track_b/corporate_actions.py:362:    def _payload_mismatch(nse_payload: Mapping[str, object], bse_payload: Mapping[str, object]) -> list[str]:
src/omegadata/track_b/corporate_actions.py:382:    def _numerically_close(left: object, right: object, tolerance: Decimal) -> bool:
src/omegadata/track_b/corporate_actions.py:394:    def apply_correction(
src/omegadata/track_b/corporate_actions.py:404:        original.superseded = True
src/omegadata/track_b/corporate_actions.py:414:            superseded=False,
src/omegadata/track_b/corporate_actions.py:415:            supersedes_id=original.id,
src/omegadata/track_b/corporate_actions.py:420:    def get_active_actions(self, session: Session, isin: str) -> list[ConfirmedCorporateAction]:
src/omegadata/track_b/corporate_actions.py:425:            .where(ConfirmedCorporateAction.superseded.is_(False))
src/omegadata/track_b/corporate_actions.py:430:    def get_action_on_date(
src/omegadata/track_b/corporate_actions.py:441:                ConfirmedCorporateAction.superseded.is_(False),
src/omegadata/track_b/isin_master.py:21:class ISINValidationError(ValueError):
src/omegadata/track_b/isin_master.py:26:class SymbolResolution:
src/omegadata/track_b/isin_master.py:33:class ISINMasterService:
src/omegadata/track_b/isin_master.py:35:    def validate_isin(isin: str) -> bool:
src/omegadata/track_b/isin_master.py:57:    def create_instrument(
src/omegadata/track_b/isin_master.py:96:    def add_ipo_record(
src/omegadata/track_b/isin_master.py:113:    def add_cross_listing(
src/omegadata/track_b/isin_master.py:132:    def apply_symbol_change(
src/omegadata/track_b/isin_master.py:178:    def resolve_symbol(self, session: Session, isin: str, exchange: Exchange, as_of: date) -> SymbolResolution:
src/omegadata/track_b/isin_master.py:190:    def mark_delisted(
src/omegadata/track_b/publication.py:15:class PublicationBlock:
src/omegadata/track_b/publication.py:24:class PublicationStatus:
src/omegadata/track_b/publication.py:31:class PublicationService:
src/omegadata/track_b/publication.py:32:    def _policy_for_category(self, category: str) -> ReviewPolicy:
src/omegadata/track_b/publication.py:36:    def _resolution_decision(review: ManualReviewQueue) -> str | None:
src/omegadata/track_b/publication.py:44:    def _applies(self, review: ManualReviewQueue, trade_date: date) -> bool:
src/omegadata/track_b/publication.py:57:    def _is_active(self, review: ManualReviewQueue) -> bool:
src/omegadata/track_b/publication.py:67:    def active_reviews_for_isin(
src/omegadata/track_b/publication.py:85:    def blocked_dates(
src/omegadata/track_b/publication.py:93:        rows_by_date = {row.trade_date: row for row in rows}
src/omegadata/track_b/publication.py:137:    def status_for_row(self, session: Session, row: PriceRecord) -> PublicationStatus:
src/omegadata/track_b/publication.py:138:        reviews_with_policy = self.active_reviews_for_isin(session, row.isin)
src/omegadata/track_b/publication.py:140:        blocks = blocks_by_date.get(row.trade_date, [])
src/omegadata/track_b/publication.py:142:        return PublicationStatus(isin=row.isin, trade_date=row.trade_date, state=state, blocks=blocks)
src/omegadata/track_b/publication.py:144:    def evaluate_records(
src/omegadata/track_b/publication.py:153:        publishable = [row for row in records if row.trade_date not in blocked_dates]
src/omegadata/track_b/publication.py:154:        blocked_rows = [row for row in records if row.trade_date in blocked_dates]
src/omegadata/track_b/publication.py:157:    def filter_records(
src/omegadata/track_b/publication.py:165:        blocked_dates = sorted({row.trade_date for row in blocked_rows})
src/omegadata/track_b/cross_source_validation.py:24:class ValidationOutcome:
src/omegadata/track_b/cross_source_validation.py:32:class PriceToleranceContext:
src/omegadata/track_b/cross_source_validation.py:42:class CrossSourceValidator:
src/omegadata/track_b/cross_source_validation.py:43:    def __init__(self) -> None:
src/omegadata/track_b/cross_source_validation.py:51:    def _audit_key(
src/omegadata/track_b/cross_source_validation.py:65:    def _audit_exists(
src/omegadata/track_b/cross_source_validation.py:116:    def validate_nse_bse_prices(self, session: Session, isin: str) -> list[ValidationOutcome]:
src/omegadata/track_b/cross_source_validation.py:198:    def _price_tolerance_context(*, nse: PriceRecord, bse: PriceRecord, field: str) -> PriceToleranceContext:
src/omegadata/track_b/cross_source_validation.py:252:    def _price_tolerance(*, nse: PriceRecord, bse: PriceRecord, field: str) -> Decimal:
src/omegadata/track_b/cross_source_validation.py:255:    def validate_monthly_flow_consistency(
src/omegadata/track_b/cross_source_validation.py:276:    def validate_implied_volatility_spot_check(
src/omegadata/track_b/cross_source_validation.py:298:    def validate_secondary_adjusted_price(
src/omegadata/track_b/cross_source_validation.py:320:    def validate_corporate_actions(self, session: Session, isin: str) -> list[ValidationOutcome]:
src/omegadata/track_b/cross_source_validation.py:361:                and best_candidate.action_type != staged_row.action_type
src/omegadata/track_b/cross_source_validation.py:372:                            left=staged_row.action_type.value,
src/omegadata/track_b/cross_source_validation.py:397:                        "nse_action_type": staged_row.action_type.value,
src/omegadata/track_b/cross_source_validation.py:410:                        left=staged_row.action_type.value,
src/omegadata/track_b/cross_source_validation.py:453:            if staged_row.action_type != staging_pair.action_type:
src/omegadata/track_b/cross_source_validation.py:459:                        isin=staged_row.isin,
src/omegadata/track_b/cross_source_validation.py:462:                        left=staged_row.action_type.value,
src/omegadata/track_b/cross_source_validation.py:485:                    isin=staged_row.isin,
src/omegadata/track_b/cross_source_validation.py:497:            compared_keys = set(staged_row.payload) | set(staging_pair.payload)
src/omegadata/track_b/cross_source_validation.py:498:            required_keys = set(CorporateActionService._validate_required_fields(staged_row.action_type, staged_row.payload))
src/omegadata/track_b/cross_source_validation.py:502:                left_val = staged_row.payload.get(key)
src/omegadata/track_b/cross_source_validation.py:511:                            isin=staged_row.isin,
src/omegadata/track_b/cross_source_validation.py:512:                            data_date=staged_row.ex_date or nse_date,
src/omegadata/track_b/cross_source_validation.py:535:                                isin=staged_row.isin,
src/omegadata/track_b/cross_source_validation.py:536:                                data_date=staged_row.ex_date or nse_date,
src/omegadata/track_b/cross_source_validation.py:547:                data_date = staged_row.ex_date or nse_date
src/omegadata/track_b/cross_source_validation.py:553:                        isin=staged_row.isin,
src/omegadata/track_b/cross_source_validation.py:564:    def _event_date(row: CorporateActionStaging) -> date | None:
src/omegadata/track_b/cross_source_validation.py:565:        return row.ex_date or row.announcement_date or row.record_date
src/omegadata/track_b/cross_source_validation.py:568:    def _date_gap_days(left: date, right: date | None) -> int:
src/omegadata/track_b/cross_source_validation.py:573:    def _compare_numeric(
src/omegadata/track_b/cross_source_validation.py:633:    def _persist_categorical_result(
src/omegadata/track_b/cross_source_validation.py:694:    def _detect_systematic_disagreement(
src/omegadata/pipelines/sequential_pipeline.py:34:    due_corporate_action_sources,
src/omegadata/pipelines/sequential_pipeline.py:42:from omegadata.track_b.cross_source_validation import CrossSourceValidator
src/omegadata/pipelines/sequential_pipeline.py:57:    def __init__(self) -> None:
src/omegadata/pipelines/sequential_pipeline.py:67:    def _to_decimal(value: str | int | float | None) -> Decimal | None:
src/omegadata/pipelines/sequential_pipeline.py:71:    def _parse_date(value: str | None) -> date | None:
src/omegadata/pipelines/sequential_pipeline.py:97:    def _normalize_row(raw: Mapping[str, object]) -> dict[str, str]:
src/omegadata/pipelines/sequential_pipeline.py:105:    def _ensure_identity_adjusted_fields(price_record: PriceRecord) -> None:
src/omegadata/pipelines/sequential_pipeline.py:127:    def _load_fii_dii(self, session: Session, path: Path) -> int:
src/omegadata/pipelines/sequential_pipeline.py:159:                    raw_source="nse_fii_dii",
src/omegadata/pi…469 tokens truncated…ial_pipeline.py:438:    def _ensure_instrument(
src/omegadata/pipelines/sequential_pipeline.py:503:    def _load_bhavcopy_prices(self, session: Session, path: Path, trade_date: date) -> int:
src/omegadata/pipelines/sequential_pipeline.py:598:                    raw_source="nse_bhavcopy",
src/omegadata/pipelines/sequential_pipeline.py:609:                existing.raw_source = "nse_bhavcopy"
src/omegadata/pipelines/sequential_pipeline.py:615:    def _load_bse_bhavcopy_prices(self, session: Session, path: Path, trade_date: date) -> int:
src/omegadata/pipelines/sequential_pipeline.py:699:                    raw_source="bse_bhavcopy",
src/omegadata/pipelines/sequential_pipeline.py:710:                existing.raw_source = "bse_bhavcopy"
src/omegadata/pipelines/sequential_pipeline.py:717:    def _parse_bse_graph_trade_date(value: object) -> date | None:
src/omegadata/pipelines/sequential_pipeline.py:730:    def _load_bse_prices_from_stockreach(self, session: Session, as_of: date) -> int:
src/omegadata/pipelines/sequential_pipeline.py:735:    def _load_corporate_actions(self, session: Session, source: Exchange, path: Path) -> int:
src/omegadata/pipelines/sequential_pipeline.py:807:            if source == Exchange.BSE and action_type == CorporateActionType.UNCLASSIFIED:
src/omegadata/pipelines/sequential_pipeline.py:814:                .where(CorporateActionStaging.source == source)
src/omegadata/pipelines/sequential_pipeline.py:858:                source=source,
src/omegadata/pipelines/sequential_pipeline.py:870:    def run_track_a(self, as_of: date) -> dict[str, str]:
src/omegadata/pipelines/sequential_pipeline.py:871:        sources = [
src/omegadata/pipelines/sequential_pipeline.py:880:        required_sources = {"NSE_EQUITY_BHAVCOPY", "BSE_EQUITY_BHAVCOPY"}
src/omegadata/pipelines/sequential_pipeline.py:882:        for source in sources:
src/omegadata/pipelines/sequential_pipeline.py:884:                paths[source] = self.ingestor.ingest_raw_source(source, as_of)
src/omegadata/pipelines/sequential_pipeline.py:886:                if source in required_sources:
src/omegadata/pipelines/sequential_pipeline.py:888:                paths[source] = ""
src/omegadata/pipelines/sequential_pipeline.py:914:    def run_scheduled_corporate_action_collection(self, run_at: datetime) -> dict[str, str]:
src/omegadata/pipelines/sequential_pipeline.py:916:        due_sources = due_corporate_action_sources(aware_run_at)
src/omegadata/pipelines/sequential_pipeline.py:917:        if not due_sources:
src/omegadata/pipelines/sequential_pipeline.py:918:            raise ValueError(f"No corporate action source is due at {aware_run_at.isoformat()}")
src/omegadata/pipelines/sequential_pipeline.py:922:        for source_key in due_sources:
src/omegadata/pipelines/sequential_pipeline.py:923:            paths[source_key] = self.ingestor.ingest_raw_source(source_key, as_of)
src/omegadata/pipelines/sequential_pipeline.py:940:    def _resolve_market_isin(self, session: Session, market_isin: str | None) -> str | None:
src/omegadata/pipelines/sequential_pipeline.py:950:    def run_track_b(self, as_of: date, market_isin: str | None = None) -> tuple[int, int, int, int, int]:
src/omegadata/pipelines/sequential_pipeline.py:1018:                    is_secondary_source=(row.raw_source.lower() != "nse_bhavcopy"),
src/omegadata/pipelines/sequential_pipeline.py:1042:    def run_scheduled_track_b_confirmation(
src/omegadata/pipelines/sequential_pipeline.py:1051:    def run_full_day(self, as_of: date, market_isin: str | None = None) -> PipelineSummary:
src/omegadata/db/models.py:34:def _utc_now() -> datetime:
src/omegadata/db/models.py:123:        Index("ix_ca_staging_source_isin_exdate", "source", "isin", "ex_date"),
src/omegadata/db/models.py:127:    source: Mapped[Exchange] = mapped_column(Enum(Exchange), nullable=False)
src/omegadata/db/models.py:152:    source_preference: Mapped[Exchange] = mapped_column(Enum(Exchange), nullable=False)
src/omegadata/db/models.py:204:    raw_source: Mapped[str] = mapped_column(String(64), nullable=False)
src/omegadata/db/models.py:261:    source: Mapped[str] = mapped_column(String(255), nullable=False)
src/omegadata/db/models.py:262:    source_confidence: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("1.00"))
src/omegadata/db/models.py:273:    source_1: Mapped[str] = mapped_column(String(64), nullable=False)
src/omegadata/db/models.py:274:    source_2: Mapped[str] = mapped_column(String(64), nullable=False)
src/omegadata/db/models.py:278:    source_1_value: Mapped[str] = mapped_column(String(255), nullable=False)
src/omegadata/db/models.py:279:    source_2_value: Mapped[str] = mapped_column(String(255), nullable=False)
src/omegadata/db/models.py:301:    raw_source: Mapped[str] = mapped_column(String(64), nullable=False)
src/omegadata/db/models.py:302:    source_artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)
src/omegadata/db/models.py:324:    raw_source: Mapped[str] = mapped_column(String(64), nullable=False)
src/omegadata/db/models.py:325:    source_artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)
src/omegadata/db/models.py:364:    raw_source: Mapped[str] = mapped_column(String(64), nullable=False)
src/omegadata/db/models.py:365:    source_artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)
src/omegadata/db/models.py:428:    raw_source: Mapped[str] = mapped_column(String(64), nullable=False)
src/omegadata/db/models.py:429:    source_artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)
src/omegadata/db/models.py:435:        UniqueConstraint("release_id", name="uq_release_record_release_id"),
src/omegadata/db/models.py:440:    release_id: Mapped[str] = mapped_column(String(64), nullable=False)
scripts/run_full_pipeline.py:34:        "--reset-sqlite-db",
scripts/run_full_pipeline.py:52:            raise ValueError("--reset-sqlite-db is only supported for sqlite db URLs")
scripts/run_full_pipeline.py:55:            db_path.unlink()
scripts/build_release_readiness_report.py:50:    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
scripts/build_release_readiness_report.py:51:    profile_path = REPO_ROOT / "artifacts/verification" / f"release_readiness_{args.profile}.json"
scripts/build_release_readiness_report.py:52:    profile_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
20:- synthetic/manual fixtures still exist for isolated unit testing, but they are explicitly separated from official-source-backed verification assets
91:- official-source-backed fixtures:
92:  [`tests/fixtures/official_source/`](tests/fixtures/official_source/)
112:- compares official BSE OHLC against NSE OHLC when available
133:- enriches it with official BSE bhavcopy when needed
140:  - `p50`, `p95`, `p99`
171:- [`tests/fixtures/official_source/corporate_action_matching_benchmark.json`](tests/fixtures/official_source/corporate_action_matching_benchmark.json)
192:### 5. Publication Gating
285:5. completion writes structured completion payload onto the job and the review
393:- source-probe freshness
394:- tolerance-report freshness
395:- matching-benchmark freshness
401:- official-source adjustment corpus minimum case count
402:- official-source transformational evidence minimum
409:- minimum official-source adjustment cases: `10`
410:- minimum official-source transformational cases: `3`
411:- minimum hand-computed transformational cases: `14`
413:Those numbers are intentionally aligned with the bundled evidence that actually exists in the repository today. The official-source corpus now clears the governed transformational threshold with real official-source-backed cases instead of relying on README narrative.
419:- official-source-backed corpus:
420:  [`tests/fixtures/official_source/adjustment_reference_corpus.json`](tests/fixtures/official_source/adjustment_reference_corpus.json)
428:The official corpus now records:
434:The hand-computed corpus still exists because it covers math-heavy transformational cases that are not yet sufficiently represented in the bundled official source window.
438:- official corpus proves source realism
441:At the moment the bundled official-source window yields:
443:- `14` official-source-backed cases
444:- `5` official-source transformational cases
446:Current official transformational labels:
448:- `NESTLEIND_2024-01-05_SPLIT`
454:That is still not the final long-term target for official-source realism. The more awkward transformational classes such as demergers, merger targets, reverse splits, supersessions, and multi-action chains are still more deeply covered in the synthetic/manual corpus than in the official-source corpus. What changed is that the official corpus is no longer stuck at a token two-case proof point.
460:- [`artifacts/verification/pipeline_execution_result.json`](artifacts/verification/pipeline_execution_result.json) is a fresh clean-db pipeline replay over `2026-04-02`, `2026-04-06`, `2026-04-07`, `2026-04-08`, `2026-04-09`, and `2026-04-13`
461:- [`artifacts/verification/release_readiness.json`](artifacts/verification/release_readiness.json) is currently `ready: true`
462:- [`tests/fixtures/official_source/adjustment_reference_corpus.json`](tests/fixtures/official_source/adjustment_reference_corpus.json) currently reports `case_count: 14` and `transformational_case_count: 5`
467:- [`artifacts/verification/extreme_test_report.json`](artifacts/verification/extreme_test_report.json) is refreshed from current test and verification outputs rather than carrying obsolete warning text
471:- a fresh full-pipeline replay artifact is treated as heavier operational evidence than a quick unit/probe rebuild
479:- `51,494` adjusted rows recomputed
734:5. Run the API
790:python scripts/backfill_nse_equity_history.py --start-date 2019-01-01 --end-date 2025-12-31 --sample-mode first_trading_day_per_year
829:- Are tolerance thresholds calibrated and fresh?
834:- Is a fresh full-pipeline replay artifact present, or is that evidence currently missing?
853:- official-source-backed transformational adjustment evidence is materially better than before but still limited by the bundled raw-source window
plan - track A.md:5:## Do Not Vibe-Code OmegaData
plan - track A.md:21:## The Correct Approach for OmegaData
plan - track A.md:33:## What You Need to Produce Before Track B Code Is Written
plan - track A.md:41:### Section 1 — Data Source Registry
plan - track A.md:97:### Section 2 — ISIN Master and Symbol Mapping Specification
plan - track A.md:146:### Section 3 — Corporate Action Adjustment Specification
plan - track A.md:257:### Section 4 — Price Discontinuity Detection Specification
plan - track A.md:303:### Section 5 — Confidence Score Specification
plan - track A.md:355:### Section 6 — Point-in-Time Universe Specification
plan - track A.md:401:### Section 7 — 24/7 News Pipeline Specification
plan - track A.md:469:## Now You Are Ready to Vibe-Code
plan - track B.md:1:# OmegaData — Track B Complete Ideation & Planning
plan - track B.md:3:## What Track B Is and Why It Exists Separately
plan - track B.md:13:## The Dependency Order
plan - track B.md:35:## Component 1 — ISIN Master & Identifier System
plan - track B.md:37:### What It Is
plan - track B.md:41:### The Core Problem It Solves
plan - track B.md:45:### Design Decisions — Every Single One
plan - track B.md:111:## Component 2 — Corporate Action Database & Classification
plan - track B.md:113:### What It Is
plan - track B.md:117:### The Core Problem It Solves
plan - track B.md:121:### Design Decisions
plan - track B.md:217:## Component 3 — Price Adjustment Engine
plan - track B.md:219:### What It Is
plan - track B.md:223:### The Core Problem It Solves
plan - track B.md:227:### Design Decisions
plan - track B.md:297:## Component 4 — Price Discontinuity Detector
plan - track B.md:299:### What It Is
plan - track B.md:303:### Design Decisions
plan - track B.md:354:## Component 5 — Point-in-Time Universe Manager
plan - track B.md:356:### What It Is
plan - track B.md:360:### The Core Problem It Solves
plan - track B.md:364:### Design Decisions
plan - track B.md:428:## Component 6 — Confidence Scoring & Data Trust System
plan - track B.md:430:### What It Is
plan - track B.md:434:### Design Decisions
plan - track B.md:494:## Component 7 — Cross-Source Validation Framework
plan - track B.md:496:### What It Is
plan - track B.md:500:### Design Decisions
plan - track B.md:532:## The Track B Testing Specification
plan - track B.md:536:### Corporate Action Reference Cases — The Non-Negotiable Test Set
plan - track B.md:569:### Discontinuity Detector Reference Cases
plan - track B.md:583:### Universe Manager Reference Cases
plan - track B.md:597:## The Vibe-Coding Instructions for Track B
plan - track B.md:617:## What You Hand to the Vibe-Coding Session
scripts\reconcile_release_blocking_reviews.py

```
