OD-05T | run 20261116T100613Z | branch feature/od01-source-rights | HEAD db087fb9ee12887d3d9c787b797bb6968ad45440.

# Security and rights

Root confinement, absolute private paths, lexical traversal/UNC/device/reparse/symlink/hardlink refusal, deterministic bounds, duplicate keys, mixed-source refusal and privacy redaction have executed negative probes. Manifest artifact_path is never opened. Expected pin files must be non-hidden JSON before any open. Metadata-only declarations never grant source/payload/reviewer authority. CLI output destination is fresh, external to repository and approved source trees, with validated non-link ancestors. Caller/operator must own private local roots; no hostile concurrent directory-owner/kernel/power-loss certificate is claimed.

Each runtime executes five reviewed guard probes: DNS, TCP/UDP, subprocess, protected-copy write and fictional signing-path read denial. Full tests run under that guard with disposable DB/storage/env paths. Static compile/type commands run on disposable code copies. The original metadata scan has its own audit hook restricting reads to allowlisted manifest names and denying writes/network/process creation while scanning. Its guard-denial count is zero; no payload/key open attempted.

Eight actual trusted CLI worker processes test help, invalid args, dry run, real-acceptance refusal, fresh/existing/protected output and unexpected source; [exact argv/exits and redacted summaries](logs/cli-process-probes.json). They are offline CLI smoke processes; the in-process cross-runtime CLI tests run under the stricter inherited guard.

[Source policy identity](logs/source-policy-identity.json): 13 pending, zero approved, unchanged. Metadata read authority is not payload-research permission, publisher authentication, source acquisition approval, redistribution or legal clearance. Current advisory feeds/transitive license review were not contacted; pip check is dependency consistency only.
