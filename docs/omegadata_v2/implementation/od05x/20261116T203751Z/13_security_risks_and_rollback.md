# Remaining risks and rollback

- P1: required Windows filesystem/egress/native-child containment and regression matrix remain blocked. AppContainer/restricted-token/job/mitigation APIs exist, but no configured boundary is demonstrated. Windows Sandbox is absent; no privileged software or host-wide policy is installed.
- P1: historical incident disposition and financial-source permissions/authenticity remain unapproved. No new approval is inferred. Existing signing/release custody risks are not waived.
- P2: historical Windows INPUT_CHANGED cause remains unknown. Linux canary diagnostics are not Windows reproduction evidence.
- P2: original mounted WSL seed enumeration still exceeds the unchanged 30-second budget. Native corpus and Windows-host metadata performance are distinct.
- P2: trusted launcher, installed runtime/public system support and trusted-owner source trees remain assumptions. Host administrator/kernel compromise, hostile host mount swaps, hardware power-loss durability and complete executable/supply-chain certification are outside these tests. New script bootstrap coverage was not measured by package coverage.

The implementation is additive. A future requested rollback can remove/revert only the four new script/test paths after review, retaining this dossier. No cleanup, data rollback, signing action, release or branch operation was performed. Old controllers stay historical and are not a fallback. Static tool PASS does not certify the blocked Windows or child-execution requirements.
