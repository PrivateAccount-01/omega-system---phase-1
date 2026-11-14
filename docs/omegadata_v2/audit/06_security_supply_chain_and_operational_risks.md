# 06 — Security, supply chain and operational risks

- Repository: PrivateAccount-01/omega-system---phase-1; branch main.
- HEAD: `09631ae5cdca7d35172724a68d70847183b914df`; inspected working tree includes pre-existing changes.
- Evaluated: 2026-11-14 UTC; run ID `OD-00-20261114-1107Z`.
- Owner: Security / operations reviewer; evidence classes: RUN / ARCH / CLAIM / UNK.
- Mode: OD-00 AUDIT_AND_PLAN_ONLY. No implementation approval or production certification.

## Procedure

Ran filename-only secret-candidate searches over source/scripts/config/CI/examples; inspected config defaults, GnuPG tracked paths, subprocess/URL/archive/write paths, workflow and dependency metadata. [Candidate file list](logs/security-candidate-paths.txt), [tracked signing paths](logs/tracked-gnupg-paths.txt), [exception inventory](logs/exception-and-placeholder-search.txt) and [package metadata](logs/module-and-package-inventory.json). No secret contents were copied into reports. No remote scanner or advisory service was contacted.

## Verified findings

- **P0 signing trust exposure:** git tracks two files under the GnuPG private-keys directory plus a revocation certificate; more signing files were already untracked at entry. Paths are recorded in the filename-only log. [Signing code](../../../src/omegadata/track_b/release_manager.py#L142) selects an existing secret key or generates a no-passphrase key under a repository-local home. This can undermine release authenticity if repository readers can use that key. Whether keys were exported to a public remote, used for operational releases, or otherwise compromised is UNVERIFIED. Do not rotate, delete, rewrite history or test private-key usability in OD-00. Security owner must classify exposure and approve remediation.
- [Config](../../../src/omegadata/config.py#L30) has a development default API key; production rejection is not evidenced. Do not treat placeholders as current credential leaks. Internal endpoints use API-key dependencies, but deployment authentication/rate/TLS posture is not validated.
- URL redirects/discovered links and cache manifest paths need host/path confinement; ZIP reads need decompression/entry-count/body-size bounds. No exploit was attempted. Ordinary except Exception occurrences were inventoried, not automatically labeled bugs.
- [Reset script](../../../scripts/run_full_pipeline.py#L49) can unlink its SQLite target; [readiness builder](../../../scripts/build_release_readiness_report.py#L49) additionally writes profile evidence under the canonical verification directory. Both hazards are confirmed statically and were avoided.
- Existing user warehouse patch uses escaped SQL string assembly and a plain INSERT, not a demonstrated idempotent upsert. Repeated sync may duplicate metadata under MergeTree. Real ClickHouse and retry tests were not run; do not revert user work.
- [Dependencies](../../../pyproject.toml#L14) use lower bounds with no inspected lockfile/SBOM. Installed package license metadata was inventoried, not treated as complete legal clearance. No project LICENSE was found by repository filename search excluding environments.
- [CI](../../../.github/workflows/trading-calendar-guard.yml#L1) only runs calendar coverage on Python 3.11. No full offline test, lint, type, secret or advisory gate is defined in this sole workflow. Version tags for actions are not immutable SHAs.

## Operational boundaries and mitigations

Current report ages exceed policy; live source, warehouse and scheduler health are UNVERIFIED. PostgreSQL/ClickHouse/Kafka/Redis/Airflow were not started. No Docker command ran. Do not infer service readiness from mocked offline tests or old SYNCED fields.

Immediate procedural mitigation: no release certification, no source collection and no distribution while P0/P1 trust issues remain. Preserve evidence, use public-only trust verification in an isolated keyring later, and keep all reproduction work disposable. OD-14 supply-chain work is a future phase; an earlier security phase requires an explicitly reviewed ordering decision.

## Limitations / next action

This is a scoped static scan, not an exhaustive secret-history, CVE, penetration or license audit. Advisory status is UNK, not 'no vulnerabilities'. Security owner must review tracked signing material; dependency owner must pin a compatible matrix and obtain approved advisory/license evidence. No private material was printed, transmitted, rotated or deleted.

