# OmegaData Repository Instructions for Codex

**Repository instructions (loaded by root `AGENTS.md`).** Keep this file short; the controlling project-specific technical reference is `docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md`. Read the master document when running an OmegaData architecture, audit, ingestion, data-quality, historical-correctness, publication or release phase. For trivial unrelated edits, read only the relevant sections.

## Operating rule

- Verify repository branch, HEAD, worktree and applicable nested instructions before editing.
- Follow explicit user-selected `OD-XX` phase. **Default mode is `OD-00 AUDIT_AND_PLAN_ONLY`** if no phase is approved. Never silently advance phases.
- Source-backed financial correctness beats speed, model confidence, feature count and green-looking CI.
- Do not modify existing code, tests, dependencies, data, release artifacts, configs or CI during OD-00; only create fresh documentation under `docs/omegadata_v2/audit/` and `docs/omegadata_v2/plan/`.
- No broker orders, live trading, credential handling in files, paid APIs, unauthorized scraping, anti-bot/access-control bypass or unreviewed network egress.
- Do not overwrite existing data or evidence. No `--reset-sqlite-db` or destructive commands against existing paths. Inspect script side effects first.
- Label cached vs seeded vs downloaded data accurately. Synthetic fixtures cannot prove official live-source availability. Distinguish event, effective, published, observed, ingested and decision times.
- Every phase requires a repo-first candidate audit (reuse vs wrapper vs extension), actual tests, independent financial references where relevant, risk report and executable Gatekeeper verdict.
- The AEF Maker/Reviewer/Implementer/Gatekeeper/Historian roles are review procedures. LLM-generated approval is not proof of executing tests or authorization by the user.
- Prefer small reversible changes, existing conventions and stable versioned interfaces; no library adoption by popularity alone.
- A phase is complete only when its documented acceptance tests were actually executed and pass, or when a BLOCKED/REJECT verdict honestly describes why. Never fake tests, benchmarks, license clearance, backtests or profits.
- Do not commit, push, create PRs, deploy, rotate secrets, fetch restricted sources or advance to another phase without explicit user approval.

## Phase output

Report: phase/verdict, branch+SHA, files changed, actual command/exit-code results, financial-integrity findings, reused library decisions, unresolved P0-P3 risks, evidence paths and the single next approval step. When blocked, stop with exact cause and minimal user action required.
